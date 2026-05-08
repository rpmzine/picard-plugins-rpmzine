# -*- coding: utf-8 -*-
PLUGIN_NAME = "Audio File Info"
PLUGIN_AUTHOR = "rpmzine"
PLUGIN_DESCRIPTION = "Adds bits-per-sample, sample rate, channels and codec (if available) to metadata and offers to append [BPS-SR] to album titles."
PLUGIN_VERSION = "4.2"
PLUGIN_API_VERSIONS = ["2.10", "2.11", "2.12", "2.13"]

import os
import shutil
import subprocess
from picard import log
from picard.metadata import register_track_metadata_processor, register_album_metadata_processor
from picard.file import register_file_post_load_processor
from mutagen import File as MutagenFile
from picard.ui.itemviews import (
    BaseAction,
    register_album_action,
    register_cluster_action,
    register_file_action,
    register_track_action,
)
from PyQt5 import QtWidgets
from contextlib import suppress


# --- Technical tag propagation logic ---
TECHNICAL_TAGS = [
    ("bits_per_sample", "_bits_per_sample"),
    ("sample_rate", "_sample_rate"),
    ("codec", "_codec"),
    ("channels", "_channels"),
    ("bitstream_codec", "_bitstream_codec"),
]

# ---------------------------------------------------------------------------
# Bitstream codec detection
# ---------------------------------------------------------------------------

# Lossless container extensions where a hidden bitstream could exist
_LOSSLESS_EXTS = {'.flac', '.wav', '.wave', '.aiff', '.aif', '.w64', '.caf'}

# DSD native formats — always DSD, no sync-word scanning required
_DSD_EXTS = {'.dsf', '.dff'}

# Additional paths to search for ffmpeg — macOS app bundles run with a
# minimal PATH that excludes Homebrew/MacPorts/manual install locations.
_FFMPEG_EXTRA_PATHS = os.pathsep.join([
    '/opt/homebrew/bin',   # Homebrew on Apple Silicon
    '/usr/local/bin',      # Homebrew on Intel / manual install
    '/opt/local/bin',      # MacPorts
    '/usr/bin',
    '/bin',
])

# Cached ffmpeg binary path (None = not found, False = not yet searched)
_ffmpeg_bin = False


def _get_ffmpeg():
    """Return the absolute path to ffmpeg, or None if not found anywhere."""
    global _ffmpeg_bin
    if _ffmpeg_bin is not False:
        return _ffmpeg_bin
    # Try the system PATH first (works when Picard is launched from terminal)
    found = shutil.which('ffmpeg')
    if not found:
        # Probe common install locations (Homebrew, MacPorts, manual)
        found = shutil.which('ffmpeg', path=_FFMPEG_EXTRA_PATHS)
    if found:
        log.info("Audio File Info: ffmpeg found at %r", found)
    else:
        log.warning(
            "Audio File Info: ffmpeg not found; bitstream detection "
            "unavailable. Install via: brew install ffmpeg"
        )
    _ffmpeg_bin = found  # str or None
    return _ffmpeg_bin


# DTS Coherent Acoustics sync words (16-bit and 14-bit, both endiannesses)
_DTS_SYNCS = [
    b'\x7f\xfe\x80\x01',  # 16-bit big-endian
    b'\xfe\x7f\x01\x80',  # 16-bit little-endian
    b'\x1f\xff\xe8\x00',  # 14-bit big-endian
    b'\xff\x1f\x00\xe8',  # 14-bit little-endian
]

# DTS-HD MA / DTS-HD High Resolution substream extension
_DTS_HD_SYNC = b'\x64\x58\x20\x25'

# Dolby TrueHD / MLP
_TRUEHD_SYNC = b'\xf8\x72\x6f\xba'

# DTS frame size bounds (bytes). FSIZE field is 14-bit: range 95–16383,
# so actual frame byte length = FSIZE + 1, giving 96–16384.
_DTS_FRAME_MIN = 96
_DTS_FRAME_MAX = 16384

# Number of consecutively-spaced sync words required to confirm a codec.
# Frame-chaining eliminates false positives far more reliably than a raw
# count: three random occurrences at the same spacing is essentially
# impossible for audio data.
_MIN_CHAIN_LEN = 4

# AC-3 / Dolby Digital sync word
_AC3_SYNC = b'\x0b\x77'

# AC-3 frame sizes in bytes for 48 kHz (indexed by frmsizecod 0-37)
# Source: ATSC A/52 Table 4.13
_AC3_FRAME_SIZES_48 = [
    128, 128, 160, 160, 192, 192, 224, 224, 256, 256,
    320, 320, 384, 384, 448, 448, 512, 512, 640, 640,
    768, 768, 896, 896, 1024, 1024, 1280, 1280, 1536, 1536,
    1792, 1792, 2048, 2048, 2560, 2560, 3072, 3072,
]


def _decode_chunk(filename, seconds=10):
    """Decode first N seconds of audio to raw s16le PCM via ffmpeg.

    Returns raw bytes on success, None if ffmpeg is unavailable or fails.
    The s16le output preserves sample integer values, allowing sync word
    scanning on DTS/AC-3/TrueHD bitstreams packed as PCM in lossless files.
    """
    ffmpeg = _get_ffmpeg()
    if not ffmpeg:
        return None
    try:
        result = subprocess.run(
            [ffmpeg, '-v', 'quiet', '-i', filename,
             '-t', str(seconds), '-f', 's16le', 'pipe:1'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        )
        return result.stdout or None
    except subprocess.TimeoutExpired:
        log.warning("Audio File Info: ffmpeg timed out decoding %r", filename)
        return None
    except Exception as exc:
        log.error("Audio File Info: ffmpeg error for %r: %s", filename, exc)
        return None


def _check_frame_chain(data, sync, frame_min, frame_max, chain_len):
    """Confirm a bitstream by finding sync words at consistent spacing.

    Locates the first two occurrences of `sync` separated by a valid frame
    size, infers the frame spacing, then verifies the chain continues for
    `chain_len` total frames.  A ±2-byte tolerance accommodates alignment
    padding between frames.

    Returns True only if `chain_len` consecutive, evenly-spaced sync words
    are found.  Accidental sync-word matches in PCM audio data occur at
    random positions and will not repeat at a consistent interval.
    """
    sw_len = len(sync)
    data_len = len(data)
    pos = 0
    while pos < data_len - sw_len:
        p1 = data.find(sync, pos)
        if p1 == -1 or p1 + frame_min >= data_len:
            break
        p2 = data.find(sync, p1 + frame_min)
        if p2 == -1:
            break
        spacing = p2 - p1
        if spacing > frame_max:
            pos = p1 + sw_len
            continue
        # Walk forward confirming the chain at this spacing
        confirmed = 2
        cp = p2
        while confirmed < chain_len:
            expected = cp + spacing
            if expected + sw_len > data_len:
                break
            # Allow ±2 bytes for inter-frame padding/alignment
            found = False
            for off in (0, 1, -1, 2, -2):
                ep = expected + off
                if 0 <= ep and ep + sw_len <= data_len:
                    if data[ep:ep + sw_len] == sync:
                        cp = ep
                        found = True
                        break
            if not found:
                break
            confirmed += 1
        if confirmed >= chain_len:
            return True
        pos = p1 + sw_len
    return False


def _check_ac3(data):
    """Validate AC-3 (48 kHz) by confirming consecutive frame syncs.

    Uses frame chaining: find sync word, compute frame size from frmsizecod,
    confirm the next sync word appears exactly frame_bytes later.
    Only validates fscod=0 (48 kHz); returns False for other rates to avoid
    false positives from random 2-byte collisions.
    """
    pos = 0
    while pos < len(data) - 5:
        idx = data.find(_AC3_SYNC, pos)
        if idx == -1 or idx + 5 > len(data):
            break
        fscod = (data[idx + 4] >> 6) & 0x03
        frmsizecod = data[idx + 4] & 0x3F
        if fscod == 0 and frmsizecod < len(_AC3_FRAME_SIZES_48):
            frame_bytes = _AC3_FRAME_SIZES_48[frmsizecod]
            next_idx = idx + frame_bytes
            if (next_idx + 1 < len(data)
                    and data[next_idx:next_idx + 2] == _AC3_SYNC):
                return True
        pos = idx + 1
    return False


def detect_bitstream_codec(filename):
    """Detect the bitstream codec for a lossless or DSD audio file.

    For DSD files (.dsf, .dff) returns 'DSD' immediately without invoking
    ffmpeg.  For PCM lossless containers (.flac, .wav, .aiff, etc.) decodes
    the first 10 seconds via ffmpeg and scans for known sync words.
    Detection priority: DTS-HD > DTS > Dolby TrueHD > Dolby Digital > PCM.

    Returns one of: 'DSD', 'DTS-HD', 'DTS', 'Dolby TrueHD',
    'Dolby Digital', 'PCM'.
    Returns None for lossy container formats or when ffmpeg is unavailable.

    Note: detects bitstream-in-PCM codecs (DTS, AC-3). Cannot detect
    transcoded files (e.g. MP3 decoded to FLAC) — those leave no sync words.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext in _DSD_EXTS:
        return 'DSD'
    if ext not in _LOSSLESS_EXTS:
        return None

    data = _decode_chunk(filename)
    if not data:
        return None

    # DTS-HD MA / DTS-HD HR (check before core DTS — may co-occur)
    if _check_frame_chain(
            data, _DTS_HD_SYNC, _DTS_FRAME_MIN, _DTS_FRAME_MAX,
            _MIN_CHAIN_LEN):
        return 'DTS-HD'

    # DTS Coherent Acoustics core (all four sync word variants).
    # Frame-chaining is used instead of a raw count: accidental matches
    # from extreme PCM sample values appear at random positions and will
    # not repeat at a consistent frame interval.
    for sync in _DTS_SYNCS:
        if _check_frame_chain(
                data, sync, _DTS_FRAME_MIN, _DTS_FRAME_MAX,
                _MIN_CHAIN_LEN):
            return 'DTS'

    # Dolby TrueHD / MLP — frames are 40 ms (~80 bytes min at 48 kHz)
    if _check_frame_chain(
            data, _TRUEHD_SYNC, 80, 65536, _MIN_CHAIN_LEN):
        return 'Dolby TrueHD'

    # AC-3 / Dolby Digital (frame-chaining validation, 48 kHz only)
    if _check_ac3(data):
        return 'Dolby Digital'

    return 'PCM'


def _add_audio_info(tagger, metadata, track, release):
    # Prefer Picard-populated metadata (underscore/script variables) when
    # available on the linked file(s). Fall back to Mutagen probing only if
    # no such metadata exists.
    try:
        fn = track and getattr(track, 'filename', None)
        log.debug("Audio File Info: _add_audio_info called for track=%r, filename=%r", track, fn)

        # Try to read existing file-level metadata from the first linked file
        file_md = {}
        file_obj = None
        if hasattr(track, "linked_files") and track.linked_files:
            file_obj = track.linked_files[0]
            file_md = getattr(file_obj, "metadata", {}) or {}

        # helper to pick preferred keys (prefer underscore-preserved/script vars)
        def pick_key(md, *names):
            for n in names:
                v = md.get(n)
                if v is not None and v != "":
                    return v, n
            return None, None

        # prefer underscore keys first, then plain, then tilde/script vars
        bps, bps_key = pick_key(file_md, "_bits_per_sample", "bits_per_sample", "~_bits_per_sample", "~bits_per_sample")
        sr, sr_key = pick_key(file_md, "_sample_rate", "sample_rate", "~_sample_rate", "~sample_rate")
        ch, ch_key = pick_key(file_md, "_channels", "channels", "~_channels", "~channels")
        codec, codec_key = pick_key(file_md, "_codec", "codec", "~_codec", "~codec")
        bc, bc_key = pick_key(file_md, "_bitstream_codec", "bitstream_codec")

        album_id = None
        try:
            if file_obj and getattr(file_obj, "parent", None) and getattr(file_obj.parent, "album", None):
                album_id = str(file_obj.parent.album.id)
        except Exception:
            album_id = None

            # Load PersistentVariables (optional) so we can read/write album-scoped values
            PersistentVariables = None
            try:
                from picard.plugins.persistent_variables import PersistentVariables as _PV
                PersistentVariables = _PV
            except Exception:
                PersistentVariables = None

            # If any preferred metadata present, normalize and persist
            if bps is not None:
                try:
                    bps_i = int(bps)
                except Exception:
                    bps_i = None
                if bps_i is not None:
                    metadata["bits_per_sample"] = bps_i
                    log.debug("Audio File Info: used existing metadata %r (key=%r)", bps_i, bps_key)
                    if sr is not None:
                        try:
                            sr_i = int(sr)
                            metadata["sample_rate"] = sr_i
                        except Exception:
                            pass
                    if ch is not None:
                        try:
                            ch_i = int(ch)
                            metadata["channels"] = ch_i
                        except Exception:
                            pass
                    if codec is not None:
                        metadata["codec"] = str(codec)
                    if bc is not None:
                        metadata["bitstream_codec"] = str(bc)

                    # persist to PersistentVariables if available
                    try:
                        if PersistentVariables and album_id:
                            PersistentVariables.set_album_var(album_id, "bits_per_sample", str(bps_i))
                            if sr is not None:
                                PersistentVariables.set_album_var(album_id, "sample_rate", str(sr))
                            if ch is not None:
                                PersistentVariables.set_album_var(album_id, "channels", str(ch))
                            if codec is not None:
                                PersistentVariables.set_album_var(album_id, "codec", str(codec))
                    except Exception:
                        # persistent_variables not present or failed; ignore
                        pass
                    return

            # No file-level Picard metadata; try to read album-level persistent variables
            try:
                if PersistentVariables and album_id:
                    pv_bps = PersistentVariables.get_album_var(album_id, "bits_per_sample")
                    pv_sr = PersistentVariables.get_album_var(album_id, "sample_rate")
                    pv_ch = PersistentVariables.get_album_var(album_id, "channels")
                    pv_codec = PersistentVariables.get_album_var(album_id, "codec")
                    if pv_bps:
                        try:
                            bps_i = int(pv_bps)
                            metadata["bits_per_sample"] = bps_i
                        except Exception:
                            pass
                    if pv_sr:
                        try:
                            sr_i = int(pv_sr)
                            metadata["sample_rate"] = sr_i
                        except Exception:
                            pass
                    if pv_ch:
                        try:
                            ch_i = int(pv_ch)
                            metadata["channels"] = ch_i
                        except Exception:
                            pass
                    if pv_codec:
                        metadata["codec"] = str(pv_codec)
                    # if we got anything from persistent vars, we're done
                    if pv_bps or pv_sr or pv_ch or pv_codec:
                        log.debug("Audio File Info: used album persistent vars for album_id=%r", album_id)
                        return
            except Exception:
                # ignore persistent variable read errors
                pass

        # No Picard-provided metadata available; fall back to probing file
        if not fn:
            log.debug("Audio File Info: No filename for track %r", track)
            return
        if not os.path.isfile(fn):
            log.debug("Audio File Info: File does not exist: %r", fn)
            return
        audio = MutagenFile(fn)
        if not audio or not getattr(audio, "info", None):
            log.debug("Audio File Info: No audio info for file %r", fn)
            return

        info = audio.info

        # bits_per_sample
        br = getattr(info, "bits_per_sample", None)
        log.debug("Audio File Info: bits_per_sample for %r: %r", fn, br)
        if br:
            metadata["bits_per_sample"] = int(br)
        # sample rate (Hz)
        sr = getattr(info, "sample_rate", None) or getattr(info, "samplerate", None)
        log.debug("Audio File Info: sample_rate for %r: %r", fn, sr)
        if sr:
            metadata["sample_rate"] = int(sr)
        # channels
        ch = getattr(info, "channels", None)
        log.debug("Audio File Info: channels for %r: %r", fn, ch)
        if ch:
            metadata["channels"] = int(ch)
        # codec (best effort)
        codec = getattr(info, "codec", None) or audio.__class__.__name__
        log.debug("Audio File Info: codec for %r: %r", fn, codec)
        if codec:
            metadata["codec"] = str(codec)
        # bitstream codec (DTS / AC-3 / TrueHD embedded in lossless PCM)
        bc = detect_bitstream_codec(fn)
        if bc is not None:
            metadata["bitstream_codec"] = bc
            log.debug(
                "Audio File Info: bitstream_codec for %r: %r", fn, bc
            )

        log.debug(
            "Audio File Info: %r bps=%r sr=%r ch=%r"
            " codec=%r bitstream_codec=%r",
            fn,
            metadata.get("bits_per_sample"),
            metadata.get("sample_rate"),
            metadata.get("channels"),
            metadata.get("codec"),
            metadata.get("bitstream_codec"),
        )

        # persist probed values to PersistentVariables
        try:
            from picard.plugins.persistent_variables import PersistentVariables
            if album_id:
                if metadata.get("bits_per_sample") is not None:
                    PersistentVariables.set_album_var(album_id, "bits_per_sample", str(metadata.get("bits_per_sample")))
                if metadata.get("sample_rate") is not None:
                    PersistentVariables.set_album_var(album_id, "sample_rate", str(metadata.get("sample_rate")))
                if metadata.get("channels") is not None:
                    PersistentVariables.set_album_var(album_id, "channels", str(metadata.get("channels")))
                if metadata.get("codec") is not None:
                    PersistentVariables.set_album_var(album_id, "codec", str(metadata.get("codec")))
        except Exception:
            pass

    except Exception as e:
        log.error("Audio File Info: failed for %r: %s", track and getattr(track, 'filename', None), e)

def propagate_technical_tags_to_metadata(metadata, file_metadata):
    """
    Copy technical tags from file_metadata to metadata (track/album), if present.
    """
    for plain, underscore in TECHNICAL_TAGS:
        value = file_metadata.get(plain)
        if value is not None:
            metadata[plain] = value
        value_ = file_metadata.get(underscore)
        if value_ is not None:
            metadata[underscore] = value_

def propagate_file_tags_to_track(tagger, metadata, track, release):
    """
    Copy technical tags from the first file in the track to the track metadata.
    """
    if hasattr(track, "linked_files") and track.linked_files:
        propagate_technical_tags_to_metadata(metadata, track.linked_files[0].metadata)


# --- Bits-per-sample promotion and UI actions (from bits_per_sample_only) ---
_registered = False


def add_bits_per_sample(file_obj):
    """Promote Picard-populated technical metatags from a file's metadata and
    persist them to album-scoped PersistentVariables when possible.
    """
    try:
        fn = getattr(file_obj, "filename", None)
        log.debug("Audio File Info: add_bits_per_sample called for %r", fn)

        try:
            from picard.plugins.persistent_variables import (
                PersistentVariables,
            )
        except Exception:
            PersistentVariables = None

        album_id = None
        try:
            if getattr(file_obj, "parent", None) and getattr(file_obj.parent, "album", None):
                album_id = str(file_obj.parent.album.id)
        except Exception:
            album_id = None

        md = getattr(file_obj, "metadata", {}) or {}

        # Bitstream detection — runs independently of bits_per_sample
        if fn and os.path.isfile(fn) and not md.get('bitstream_codec'):
            bc = detect_bitstream_codec(fn)
            if bc is not None:
                file_obj.metadata['bitstream_codec'] = bc
                log.debug(
                    "Audio File Info: bitstream_codec=%r for %r", bc, fn
                )

        def pick_key(*names):
            for n in names:
                v = md.get(n)
                if v is not None and v != "":
                    return v, n
            return None, None

        bps, bps_key = pick_key("_bits_per_sample", "bits_per_sample", "~_bits_per_sample", "~bits_per_sample")
        sr, sr_key = pick_key("_sample_rate", "sample_rate", "~_sample_rate", "~sample_rate")
        ch, ch_key = pick_key("_channels", "channels", "~_channels", "~channels")
        codec, codec_key = pick_key("_codec", "codec", "~_codec", "~codec")

        br = None
        if bps is not None:
            try:
                br = int(bps)
            except Exception:
                br = None

        if br is not None:
            file_obj.metadata["bits_per_sample"] = br
            if bps_key:
                if bps_key.startswith("~"):
                    log.debug("Audio File Info: used script variable %r for %r", bps_key, fn)
                elif bps_key.startswith("_"):
                    log.debug("Audio File Info: used underscore-tag %r for %r", bps_key, fn)
            if sr is not None:
                try:
                    file_obj.metadata["sample_rate"] = int(sr)
                except Exception:
                    pass
            if ch is not None:
                try:
                    file_obj.metadata["channels"] = int(ch)
                except Exception:
                    pass
            if codec is not None:
                file_obj.metadata["codec"] = str(codec)
            log.debug("Audio File Info: promoted %r -> %r", fn, br)

            try:
                if PersistentVariables and album_id:
                    PersistentVariables.set_album_var(album_id, "bits_per_sample", str(br))
                    if sr is not None:
                        PersistentVariables.set_album_var(album_id, "sample_rate", str(sr))
                    if ch is not None:
                        PersistentVariables.set_album_var(album_id, "channels", str(ch))
                    if codec is not None:
                        PersistentVariables.set_album_var(album_id, "codec", str(codec))
            except Exception:
                pass
            return

        # attempt to resolve from album persistent vars
        try:
            if PersistentVariables and album_id:
                pv_bps = PersistentVariables.get_album_var(album_id, "bits_per_sample")
                if pv_bps:
                    try:
                        br = int(pv_bps)
                        file_obj.metadata["bits_per_sample"] = br
                        pv_sr = PersistentVariables.get_album_var(album_id, "sample_rate")
                        if pv_sr:
                            try:
                                file_obj.metadata["sample_rate"] = int(pv_sr)
                            except Exception:
                                pass
                        pv_ch = PersistentVariables.get_album_var(album_id, "channels")
                        if pv_ch:
                            try:
                                file_obj.metadata["channels"] = int(pv_ch)
                            except Exception:
                                pass
                        pv_codec = PersistentVariables.get_album_var(album_id, "codec")
                        if pv_codec:
                            file_obj.metadata["codec"] = str(pv_codec)
                        log.debug("Audio File Info: resolved %r from album persistent var %r", fn, album_id)
                        return
                    except Exception:
                        pass
        except Exception:
            pass

        log.debug("Audio File Info: no metadata/persistent bits available for %r", fn)
    except Exception:
        pass


def _process_track_promo(album, metadata, track, release):
    for f in getattr(track, "linked_files", []):
        with suppress(Exception):
            add_bits_per_sample(f)
        if f.metadata.get("bits_per_sample") is not None:
            metadata["bits_per_sample"] = f.metadata.get("bits_per_sample")
            break


class ProcessSelection(BaseAction):
    NAME = "Process technical tags"

    def callback(self, objs):
        files = self.tagger.get_files_from_objects(objs)
        if not files:
            return
        processed = 0
        for f in files:
            with suppress(Exception):
                add_bits_per_sample(f)
                processed += 1
        log.debug("Audio File Info: ProcessSelection processed %d files", processed)
        QtWidgets.QMessageBox.information(None, "Process technical tags", f"Processed {processed} files")


# Register promo processor/actions at import time and from plugin_loaded
try:
    if not _registered:
        register_track_metadata_processor(_process_track_promo, priority=40)
        _act = ProcessSelection()
        register_file_action(_act)
        register_track_action(_act)
        register_cluster_action(_act)
        # ensure automatic processing on file load
        try:
            register_file_post_load_processor(add_bits_per_sample)
        except Exception:
            # older Picard may not provide this API; ignore
            pass
        log.debug("Audio File Info: registered promo processor and ProcessSelection action at import time")
        _registered = True
except Exception:
    log.debug("Audio File Info: promo import-time registration failed; plugin_loaded will try")

def aggregate_technical_tags_to_album(tagger, metadata, release):
    log.debug("Audio File Info: aggregate_technical_tags_to_album called for album '%s'", metadata.get("album"))
    agg = {plain: set() for plain, _ in TECHNICAL_TAGS}
    for track in getattr(release, "tracks", []):
        for file in getattr(track, "linked_files", []):
            for plain, underscore in TECHNICAL_TAGS:
                v = file.metadata.get(plain)
                if v is not None:
                    agg[plain].add(str(v))
    for plain, _ in TECHNICAL_TAGS:
        if agg[plain]:
            metadata[plain] = "/".join(sorted(agg[plain]))
    # aggregation only; album title append removed (handled by another plugin)

# Define a BaseAction subclass for the context menu
# album append action removed; aggregation only

# Attempt to register processors at import time as a fallback so they are
# available even if plugin_loaded timing differs in some environments.
try:
    register_track_metadata_processor(_add_audio_info, priority=40)
    register_track_metadata_processor(propagate_file_tags_to_track, priority=60)
    register_album_metadata_processor(aggregate_technical_tags_to_album)
    log.debug("Audio File Info: registered processors at import time")
except Exception:
    log.debug("Audio File Info: import-time processor registration failed or deferred")


def plugin_loaded(picard):
    log.info("Audio File Info: plugin_loaded")
    # Extract technical info from file
    register_track_metadata_processor(_add_audio_info, priority=40)
    # Propagate file tags to track metadata
    register_track_metadata_processor(propagate_file_tags_to_track, priority=60)
    # Aggregate to album
    register_album_metadata_processor(aggregate_technical_tags_to_album)
    # register file post-load processor as fallback
    try:
        register_file_post_load_processor(add_bits_per_sample)
    except Exception:
        pass

def plugin_unloaded(_picard):
    pass