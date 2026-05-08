# Audio File Info Plugin — Development Notes

## Overview

Reads and exposes technical audio metadata — bits per sample, sample rate, channels, codec — into Picard's tag namespace. Also detects bitstream codecs (DTS, DTS-HD, Dolby TrueHD, Dolby Digital) hidden inside lossless PCM containers via ffmpeg decoding + frame-chaining sync word scanning.

Evolved from the standalone scripts in `old_tools/`: `bits_per_sample_only.py` → `force_extract_bits.py` → this plugin.

---

## Architecture

### Tags set
| Tag name | Description |
|---|---|
| `bits_per_sample` | Bit depth (16, 24, 32…) |
| `sample_rate` | Sample rate in Hz |
| `channels` | Channel count |
| `codec` | Container/codec name from Mutagen |
| `bitstream_codec` | PCM-embedded bitstream: DSD / DTS-HD / DTS / Dolby TrueHD / Dolby Digital / PCM |

### Hooks registered
- `register_track_metadata_processor(_add_audio_info, priority=40)` — probes file and populates tags
- `register_track_metadata_processor(propagate_file_tags_to_track, priority=60)` — copies underscore tags to plain tags
- `register_album_metadata_processor(aggregate_technical_tags_to_album)` — aggregates across tracks
- `register_file_post_load_processor(add_bits_per_sample)` — promotes tags on file load

All processors are registered both at import time and in `plugin_loaded()` for compatibility with different Picard startup orders.

### Bitstream detection
1. DSD (.dsf / .dff) — returns `'DSD'` immediately, no ffmpeg needed
2. Lossless containers (.flac, .wav, .aiff, .w64, .caf…) — decodes first 10 seconds via ffmpeg to raw `s16le` PCM
3. Scans decoded bytes for sync words using frame-chaining: finds two consecutive sync words at consistent spacing, then confirms the chain continues for ≥ 4 frames — eliminates false positives from random PCM data
4. Detection priority: DTS-HD > DTS > Dolby TrueHD > Dolby Digital (AC-3) > PCM

ffmpeg is searched in PATH first, then in `/opt/homebrew/bin`, `/usr/local/bin`, `/opt/local/bin` (macOS app bundles run with a stripped PATH).

### PersistentVariables
Optionally persists probed values to album-scoped `PersistentVariables` (a separate optional plugin) to survive metadata refreshes without re-probing. Gracefully absent if not installed.

---

## Version History

- **Early** — Standalone `bits_per_sample_only.py`, `force_extract_bits.py` in old_tools
- **4.x** — Unified plugin: Mutagen probing + ffmpeg bitstream detection + PersistentVariables support
- **4.2** — Current stable

---

## When Resuming Development

1. Check `PLUGIN_VERSION` in `__init__.py`
2. Key complexity: the dual-registration pattern (import-time + `plugin_loaded`) exists because Picard's plugin loading order varies — don't remove either
3. `_registered` guard prevents double-registration of the `ProcessSelection` action
4. Bitstream detection requires ffmpeg; if unavailable, `bitstream_codec` is silently skipped
5. Testing: load a DTS FLAC and confirm `bitstream_codec = DTS` appears in Picard's tag view

Current stable version: **4.2**
Last updated: 2026-04-25
