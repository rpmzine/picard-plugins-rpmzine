# Audio File Info Plugin

**Version:** 4.2
**Author:** rpmzine
**API Versions:** 2.10, 2.11, 2.12, 2.13

## Description

Extracts technical audio metadata from your files and writes it as tags in MusicBrainz Picard. Includes bitstream codec detection for lossless containers (FLAC, WAV, AIFF, etc.) and DSD format recognition.

## Generated Tags

| Tag | Description | Example values |
| --- | ----------- | -------------- |
| `bits_per_sample` | Bit depth | `16`, `24`, `32` |
| `sample_rate` | Sample rate in Hz | `44100`, `96000`, `192000` |
| `channels` | Number of audio channels | `1`, `2`, `6` |
| `codec` | Container/codec | `FLAC`, `MP3`, `AAC` |
| `bitstream_codec` | Bitstream encoded inside lossless container | `DTS`, `Dolby Digital`, `Dolby TrueHD`, `DTS-HD`, `PCM`, `DSD` |

For albums with mixed specs, values are aggregated with `/` separation (e.g. `16/24` for mixed bit depths).

## Bitstream Codec Detection

Many audio discs encode a lossy or object-based audio bitstream inside a lossless PCM container. Common cases:

- **DTS CD** — DTS Coherent Acoustics audio packed as PCM on a standard CD, ripped to FLAC
- **DTS-HD MA** — DTS-HD Master Audio on Blu-ray, stored as PCM in FLAC/WAV
- **Dolby Digital (AC-3)** — Dolby Digital bitstream packed as PCM
- **Dolby TrueHD** — Dolby TrueHD / MLP bitstream packed as PCM
- **DSD** — Native DSD audio (DSF or DFF files) — detected without ffmpeg
- **PCM** — Standard unencoded PCM (written for all other lossless files)

Detection requires **ffmpeg** to be installed. On macOS, the plugin searches:

- System `PATH`
- `/opt/homebrew/bin` (Homebrew on Apple Silicon)
- `/usr/local/bin` (Homebrew on Intel)
- `/opt/local/bin` (MacPorts)

Install ffmpeg via: `brew install ffmpeg`

Detection uses sync word scanning with a minimum occurrence threshold (`_MIN_SYNC_COUNT = 8`) to eliminate false positives from coincidental PCM sample values that match a sync pattern.

## Dependencies

- **Mutagen** — audio file analysis (included with Picard)
- **ffmpeg** — required for bitstream codec detection (optional, external)
- **Persistent Variables plugin** — optional, for storing tags across sessions

## Installation

1. Place the `audio_file_info` folder in your Picard plugins directory
2. Enable the plugin in Picard's Options > Plugins
3. Restart Picard

## Changelog

### Version 4.2

- Replaced count-based DTS/TrueHD detection with frame-chaining validation. Finds two consecutive sync words, infers frame spacing, and verifies the pattern continues for 4 frames with ±2-byte tolerance. Accidental sync-word collisions from PCM audio data appear at random positions and will not repeat at a consistent interval, making this approach robust against all false positive cases.

### Version 4.1

- Fixed DTS false positives caused by extreme PCM sample values matching the DTS sync word byte pattern (e.g. stereo peak at +32766 / -32767 produces `FE 7F 01 80` in the s16le stream). Applied minimum sync count threshold (8) for DTS, DTS-HD, and TrueHD detection.
- Added DSD format detection: `.dsf` and `.dff` files now return `bitstream_codec = DSD` immediately without invoking ffmpeg.

### Version 4.0

- Added `bitstream_codec` tag: detects DTS, DTS-HD, Dolby Digital (AC-3), Dolby TrueHD, and PCM bitstreams inside lossless containers.
- Uses ffmpeg `s16le` decode + sync word scanning. AC-3 uses ATSC A/52 frame-chaining validation to suppress false positives.
- ffmpeg path search covers Homebrew (Apple Silicon + Intel), MacPorts, and system PATH — handles macOS app bundle PATH limitations.
- Bumped API versions to 2.10–2.13.

### Version 3.5

- Fixed function signatures for Picard API compatibility
- Improved error handling for track filename access
- Enhanced album metadata aggregation
