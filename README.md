# rpmzine Picard Plugins

A collection of MusicBrainz Picard plugins for music collectors and archivists.

**Compatibility:** Picard 3.0 (primary) · Picard 2.10–2.13 (supported)  
**Platform:** macOS (tested); Linux/Windows should work with minor path differences

---

## Plugins

| Plugin | Version | Type | Description |
|--------|---------|------|-------------|
| [Album Subfolder](#album-subfolder) | 2.3.0 | Auto | Moves saved files into `Albumartist - Album` subfolders; sweeps companion files |
| [Artwork Searcher](#artwork-searcher) | 1.0.0 | Right-click | Opens Google/Bing image search for album artwork from context menu |
| [Audio File Info](#audio-file-info) | 4.2 | Auto | Writes technical tags (codec, bitrate, sample rate, bit depth, bitstream codec) |
| [Cluster Refresh](#cluster-refresh) | 1.0.0 | Right-click | Re-reads files from disk without re-dragging; useful after external tagging |
| [Grouping Tagger](#grouping-tagger) | 3.1.2 | Right-click + Auto | Tags the GROUPING field with source, format, and quality tier |
| [Multidisc Tagger](#multidisc-tagger) | 2.6.0 | Auto + Right-click | Sets Work/Movement tags for multidisc releases; manual subtitles via context menu |
| [Suffix Appender](#suffix-appender) | 2.4.0 | Right-click | Appends formula-based suffixes to album/track titles from context menu |
| [Tag Filter & Joiner](#tag-filter--joiner) | 0.9.5 | Options | Removes unwanted tags and/or joins multi-value tags with custom separators |

---

## Installation

### From Picard (recommended)

1. In Picard: **Options → Plugins → Install Plugin**
2. Enter the URL of any plugin's `__init__.py` from this repository, **or** install individual plugin ZIP files from the `dist/` directory

### Manual installation (Picard 2.x)

Copy a plugin folder (e.g. `album_subfolder/`) to your Picard plugins directory:

| Platform | Path |
|----------|------|
| macOS | `~/.config/MusicBrainz/Picard/plugins/` |
| Linux | `~/.config/MusicBrainz/Picard/plugins/` |
| Windows | `%APPDATA%\MusicBrainz\Picard\plugins\` |

### Picard 3.0

Picard 3.0 uses a new plugins directory:

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/MusicBrainz/Picard/plugins3/` |

Each plugin folder must contain `__init__.py`, `_compat.py`, and `MANIFEST.toml`.

---

## Plugin Details

### Album Subfolder

After saving, moves each file into a subfolder named `Albumartist - Album` inside the destination directory. Also sweeps companion files (artwork, cue sheets, logs, checksums, playlists) and subdirectories from the source folder into the new subfolder.

**Requirement:** Picard's *Move additional files* option must be **disabled** — the plugin handles companion file relocation itself.

A dialog appears once per save batch asking whether to move files. The dialog offers three choices: move to subfolder, skip once, or disable permanently.

→ [Full documentation](album_subfolder/README.md)

---

### Artwork Searcher

Adds **Search Artwork → Google Images** and **Search Artwork → Bing Images** actions to the right-click menu on files, tracks, clusters, and albums. Opens a large-image-filtered browser search for `<Albumartist> <Album> album cover`.

Deduplicates queries when multiple items share the same artist+album — one tab per unique search.

→ [Full documentation](artwork_searcher/README.md)

---

### Audio File Info

A metadata processor that runs automatically on every loaded file and writes technical tags:

| Tag | Example |
|-----|---------|
| `codec` | `FLAC`, `MP3`, `AAC` |
| `bits_per_sample` | `16`, `24` |
| `sample_rate` | `44100`, `96000` |
| `channels` | `2`, `6` |
| `bitstream_codec` | `DTS`, `Dolby TrueHD`, `DSD`, `PCM` |

Bitstream codec detection (for DTS CDs, Blu-ray rips, etc.) requires **ffmpeg** to be installed. On macOS, the plugin searches Homebrew, MacPorts, and system PATH automatically.

→ [Full documentation](audio_file_info/README.md)

---

### Cluster Refresh

Adds a **Refresh from Disk** action to the right-click menu on clusters and individual cluster files. Re-reads files from disk without requiring you to drag them back from Finder — useful when editing metadata in an external tagger (e.g. Yate) while Picard is open.

→ [Full documentation](cluster_refresh/README.md)

---

### Grouping Tagger

Tags the `GROUPING` field with source, format, and quality information. Works as both an automatic metadata processor and via right-click actions.

**Detection rules:** Vinyl · CD · Cassette · Digital · Bootleg · Remaster · Quality tier (Lossy / Lossless / Hi-Def)

**Template system:** Create custom templates using variables (`{SOURCE}`, `{FORMAT}`, `{QUALITY}`, etc.) with a live preview editor. Templates appear in the right-click context menu.

**Fixed tags:** Predefined tags (Vinyl, CD, FLAC, Bootleg, etc.) for quick application via right-click.

Configuration (templates + fixed tags) is stored in a JSON file outside the plugin folder and survives plugin updates:  
`~/Library/Preferences/MusicBrainz/Picard/json/grouping_tagger_config.json`

→ [Full documentation](grouping_tagger/README.md)

---

### Multidisc Tagger

Sets `work`, `movement`, and `showmovement` tags for multidisc releases, enabling classical-style hierarchical organization in music players (Apple Music, Roon, etc.).

**Automatic mode:** Activates when MusicBrainz provides `discsubtitle` metadata — no user action required.

**Manual mode:** Right-click an album or cluster → *Make it a Multidisc* → enter disc subtitles in a dialog. Quick presets for "CD 1, CD 2…" and "Disc 1, Disc 2…" numbering.

→ [Full documentation](multidisc_tagger/README.md)

---

### Suffix Appender

Appends formula-based suffixes to album or track titles via the right-click context menu. Uses a simple variable language with smart detection and conditional rendering.

**Example formulas:**

| Formula | Result |
|---------|--------|
| `[<releasecountry> <format>] [<bits_per_sample>-<sample_rate\|khz>]` | `[US FLAC] [24-96]` |
| `[<releasecountry> <catalognumber> <format>]` | `[Japan TOCP-12345 FLAC]` |
| `[<releasecountry> <formatsize> <recordtype>]` | `[US 12" LP]` |

12 built-in templates; unlimited custom templates via the Template Manager dialog.

→ [Full documentation](suffix_appender/README.md)

---

### Tag Filter & Joiner

Removes unwanted tags and/or joins multi-value tags with custom separators. Configured via **Options → Plugins → Tag Filter and Joiner**.

For each of 69 standard MusicBrainz tags, you can:
- **Ignore** — remove the tag entirely before saving
- **Join Multi-values** — combine multiple values into one using a configurable separator (default: ` / `)

→ [Full documentation](tag_filter_joiner/README.md)

---

## Repository Structure

```
PicardPlugin/
├── _compat.py              # Master compatibility shim (Picard 2.x / 3.0, PyQt5 / PyQt6)
├── MANIFEST.toml           # Collection manifest
├── README.md               # This file
├── DEVELOPMENT.md          # Developer notes: _compat architecture, V3 API patterns
├── install_plugins.sh      # Helper script for local installation
├── dist/                   # Built plugin ZIPs
│
├── album_subfolder/
│   ├── __init__.py
│   ├── _compat.py          # Copy of root _compat.py
│   ├── MANIFEST.toml
│   ├── README.md
│   └── DEVELOPMENT_NOTES.md
│
├── artwork_searcher/       # same structure
├── audio_file_info/        # same structure
├── cluster_refresh/        # same structure
├── grouping_tagger/        # same structure
├── multidisc_tagger/       # same structure
├── suffix_appender/        # same structure
└── tag_filter_joiner/      # same structure
```

The `_compat.py` shim in each plugin directory is identical to the root `_compat.py`. When updating `_compat.py`, copy it to all plugin directories.

---

## License

Each plugin specifies its own license (MIT or GPL-2.0). See the `PLUGIN_LICENSE` field in each plugin's `__init__.py` or its `README.md`.

---

## Author

[rpmzine](https://github.com/rpmzine)
