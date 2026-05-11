# Album Subfolder

**Version:** 2.3.0
**Author:** rpmzine
**API Versions:** 2.10, 2.11, 2.12, 2.13, 3.0
**License:** GPL-2.0

## Description

After saving files in Picard, this plugin automatically moves them into a subfolder named `Albumartist - Album` inside the destination folder. It also moves companion files — artwork, cue sheets, logs, and subdirectories (e.g. `ARTWORK/`) — from the source folder into the new subfolder.

> **Requirement:** "Move additional files" must be **DISABLED** in Picard's Options → File Naming. The plugin handles companion file relocation itself.

## Installation

1. Copy the `album_subfolder` folder to your Picard plugins directory:
   - macOS: `~/.config/MusicBrainz/Picard/plugins`
2. Restart MusicBrainz Picard
3. Enable the plugin in Options → Plugins

## Usage

1. Tag your files normally and save via Picard
2. The plugin runs automatically after each save — no manual action needed
3. Each saved file is moved into `<destination>/<Albumartist - Album>/<filename>`
4. Companion files (artwork, cue, log, etc.) and subdirectories are swept into the same subfolder once all tracks from the source folder have been saved

### Companion file extensions swept automatically

Images: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tif`, `.tiff`, `.webp`  
Audio extras: `.cue`, `.log`, `.txt`, `.nfo`, `.pdf`  
Checksums: `.md5`, `.ffp`, `.sha`, `.sha256`  
Playlists: `.m3u`, `.m3u8`  
Subdirectories: all (e.g. `ARTWORK/`, `Scans/`)

### Notes

- If the file is already inside a correctly named subfolder, it is left in place
- Re-saving an already-organised file (source dir == destination dir) skips the companion sweep to avoid side effects
- Thread-safe: works correctly when Picard saves multiple files in parallel

## Changelog

### Version 2.3.0

- Added Picard 3.0 (`enable(api)` V3 API) compatibility
- Per-save confirmation dialog: move to subfolder, skip once, or disable permanently
- Options page with enable/disable checkbox (`Options → Plugins → Album Subfolder`)

### Version 2.2.0
- Thread-safe source-directory tracking via lock-protected `_source_map`
- Companion sweep deferred until the last file from a source folder is saved
- Subdirectories moved in addition to flat companion files

### Version 2.1.x
- Added snapshot of extra files at load time to avoid race conditions

### Version 2.0.0
- Initial public release with post-save subfolder organisation
