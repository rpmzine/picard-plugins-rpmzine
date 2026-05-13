# -*- coding: utf-8 -*-
PLUGIN_NAME = "Audio File Info"
PLUGIN_AUTHOR = "rpmzine"
PLUGIN_DESCRIPTION = "Adds bits-per-sample, sample rate, channels and codec (if available) to metadata and offers to append [BPS-SR] to album titles."
PLUGIN_VERSION = "5.0"
PLUGIN_API_VERSIONS = ["2.10", "2.11", "2.12", "2.13", "3.0"]

import os
import shutil
import subprocess
from picard import log
from mutagen import File as MutagenFile
from ._compat import (
    QtWidgets,
    BaseAction,
    register_album_action,
    register_cluster_action,
    register_file_action,
    register_file_post_load_processor,
    register_track_action,
    register_track_metadata_processor,
)
from contextlib import suppress

# Tags this plugin writes — all plain names, no prefix.
TAGS = ("bits_per_sample", "sample_rate", "channels", "codec", "bitstream_codec")

# ---------------------------------------------------------------------------
# ffmpeg helpers
# ---------------------------------------------------------------------------

_FFMPEG_EXTRA_PATHS = os.pathsep.join([
    '/opt/homebrew/bin',
    '/usr/local/bin',
    '/opt/local/bin',
    '/usr/bin',
    '/bin',
])

_ffmpeg_bin = False


def _get_ffmpeg():
    global _ffmpeg_bin
    if _ffmpeg_bin is not False:
        return _ffmpeg_bin
    found = shutil.which('ffmpeg') or shutil.which('ffmpeg', path=_FFMPEG_EXTRA_PATHS)
    if found:
        log.info("Audio File Info: ffmpeg found at %r", found)
    else:
        log.warning("Audio File Info: ffmpeg not found; bitstream detection unavailable.")
    _ffmpeg_bin = found
    return _ffmpeg_bin


# ---------------------------------------------------------------------------
# Bitstream codec detection (DTS / TrueHD / Dolby Digital inside lossless PCM)
# ---------------------------------------------------------------------------

_LOSSLESS_EXTS = {'.flac', '.wav', '.wave', '.aiff', '.aif', '.w64', '.caf'}
_DSD_EXTS = {'.dsf', '.dff'}

_DTS_SYNCS = [
    b'\x7f\xfe\x80\x01',
    b'\xfe\x7f\x01\x80',
    b'\x1f\xff\xe8\x00',
    b'\xff\x1f\x00\xe8',
]
_DTS_HD_SYNC = b'\x64\x58\x20\x25'
_TRUEHD_SYNC = b'\xf8\x72\x6f\xba'
_DTS_FRAME_MIN = 96
_DTS_FRAME_MAX = 16384
_MIN_CHAIN_LEN = 4
_AC3_SYNC = b'\x0b\x77'
_AC3_FRAME_SIZES_48 = [
    128, 128, 160, 160, 192, 192, 224, 224, 256, 256,
    320, 320, 384, 384, 448, 448, 512, 512, 640, 640,
    768, 768, 896, 896, 1024, 1024, 1280, 1280, 1536, 1536,
    1792, 1792, 2048, 2048, 2560, 2560, 3072, 3072,
]


def _decode_chunk(filename, seconds=10):
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
        confirmed = 2
        cp = p2
        while confirmed < chain_len:
            expected = cp + spacing
            if expected + sw_len > data_len:
                break
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
    ext = os.path.splitext(filename)[1].lower()
    if ext in _DSD_EXTS:
        return 'DSD'
    if ext not in _LOSSLESS_EXTS:
        return None
    data = _decode_chunk(filename)
    if not data:
        return None
    if _check_frame_chain(data, _DTS_HD_SYNC, _DTS_FRAME_MIN, _DTS_FRAME_MAX, _MIN_CHAIN_LEN):
        return 'DTS-HD'
    for sync in _DTS_SYNCS:
        if _check_frame_chain(data, sync, _DTS_FRAME_MIN, _DTS_FRAME_MAX, _MIN_CHAIN_LEN):
            return 'DTS'
    if _check_frame_chain(data, _TRUEHD_SYNC, 80, 65536, _MIN_CHAIN_LEN):
        return 'Dolby TrueHD'
    if _check_ac3(data):
        return 'Dolby Digital'
    return 'PCM'


# ---------------------------------------------------------------------------
# Core probe: read audio properties from a file and write plain tags
# ---------------------------------------------------------------------------

def _probe_and_write(file_obj):
    """Read audio technical properties and write as plain tags to file metadata.

    Priority:
      1. Picard's own ~bits_per_sample / ~sample_rate / ~channels (already computed)
      2. Mutagen direct probe (fallback when Picard's values aren't populated yet)
    """
    fn = getattr(file_obj, "filename", None)
    if not fn or not os.path.isfile(fn):
        return

    md = getattr(file_obj, "metadata", {}) or {}

    # 1. Prefer Picard's built-in tilde-prefixed audio properties
    bps = md.get("~bits_per_sample")
    sr  = md.get("~sample_rate")
    ch  = md.get("~channels")
    codec = None  # Picard doesn't expose codec as a tilde tag

    # 2. Mutagen fallback (also gives us codec)
    if not bps or not sr:
        try:
            audio = MutagenFile(fn)
            if audio and getattr(audio, "info", None):
                info = audio.info
                if not bps:
                    bps = getattr(info, "bits_per_sample", None)
                if not sr:
                    sr = getattr(info, "sample_rate", None) or getattr(info, "samplerate", None)
                if not ch:
                    ch = getattr(info, "channels", None)
                codec = getattr(info, "codec", None) or audio.__class__.__name__
        except Exception as exc:
            log.error("Audio File Info: Mutagen failed for %r: %s", fn, exc)

    if bps:
        file_obj.metadata["bits_per_sample"] = str(int(bps))
    if sr:
        file_obj.metadata["sample_rate"] = str(int(sr))
    if ch:
        file_obj.metadata["channels"] = str(int(ch))
    if codec:
        file_obj.metadata["codec"] = str(codec)

    # Bitstream detection (DTS / TrueHD etc. inside lossless PCM)
    if not md.get("bitstream_codec"):
        bc = detect_bitstream_codec(fn)
        if bc is not None:
            file_obj.metadata["bitstream_codec"] = bc

    log.debug(
        "Audio File Info: %r → bps=%r sr=%r ch=%r codec=%r bitstream=%r",
        fn,
        file_obj.metadata.get("bits_per_sample"),
        file_obj.metadata.get("sample_rate"),
        file_obj.metadata.get("channels"),
        file_obj.metadata.get("codec"),
        file_obj.metadata.get("bitstream_codec"),
    )


# ---------------------------------------------------------------------------
# Track metadata processor: copy file tags up to track metadata
# ---------------------------------------------------------------------------

def _copy_file_tags_to_track(tagger, metadata, track, release):
    """Propagate technical tags from the first matched file to track metadata."""
    # V3: track.files  /  V2: track.linked_files
    files = getattr(track, "files", None) or getattr(track, "linked_files", [])
    for f in files:
        for tag in TAGS:
            v = f.metadata.get(tag)
            if v is not None:
                metadata[tag] = v
        break  # use first matched file only


# ---------------------------------------------------------------------------
# Right-click action: manually re-process selected files
# ---------------------------------------------------------------------------

class ProcessSelection(BaseAction):
    NAME = "Process technical tags"
    TITLE = "Process technical tags"
    MENU = ("Audio File Info",)

    def callback(self, objs):
        tagger = getattr(getattr(self, 'api', None), 'tagger', None) or getattr(self, 'tagger', None)
        files = []
        for obj in objs:
            if hasattr(obj, 'files'):
                files.extend(obj.files)
            elif hasattr(obj, 'filename'):
                files.append(obj)
        if not files and tagger and hasattr(tagger, 'get_files_from_objects'):
            files = list(tagger.get_files_from_objects(objs))

        processed = 0
        for f in files:
            with suppress(Exception):
                _probe_and_write(f)
                processed += 1
        log.info("Audio File Info: ProcessSelection processed %d files", processed)
        QtWidgets.QMessageBox.information(
            None, "Audio File Info", f"Processed {processed} files."
        )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def enable(api):
    register_file_post_load_processor(_probe_and_write)
    register_track_metadata_processor(_copy_file_tags_to_track, priority=60)

    if hasattr(api, 'register_cluster_action'):
        api.register_file_action(ProcessSelection)
        api.register_track_action(ProcessSelection)
        api.register_cluster_action(ProcessSelection)
        api.register_album_action(ProcessSelection)
    else:
        _action = ProcessSelection()
        register_file_action(_action)
        register_track_action(_action)
        register_cluster_action(_action)
        register_album_action(_action)

    log.info("Audio File Info: Plugin loaded (v%s)", PLUGIN_VERSION)
