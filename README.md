# rpmzine · MusicBrainz Picard Plugins

A collection of plugins for [MusicBrainz Picard](https://picard.musicbrainz.org) focused on music collectors and archivists working with vinyl, CD, and high-resolution audio.

**Picard 3.0** (primary) · **Picard 2.10–2.13** (supported) · macOS tested

---

## Plugins

### [Album Subfolder](https://github.com/rpmzine/picard-plugin-album-subfolder)
After saving, automatically moves files into a subfolder named `Albumartist - Album` inside the destination directory. Also sweeps companion files — artwork, cue sheets, logs, checksums — from the source folder into the same subfolder.

> Requires *Move additional files* to be **disabled** in Picard options.

---

### [Artwork Searcher](https://github.com/rpmzine/picard-plugin-artwork-searcher)
Adds **Search Artwork → Google Images** and **Search Artwork → Bing Images** to the right-click menu on any file, track, cluster, or album. Opens a large-image-filtered browser search for the release's cover art. Deduplicates tabs across multi-selection.

---

### [Audio File Info](https://github.com/rpmzine/picard-plugin-audio-file-info)
Writes technical audio properties as tags: `codec`, `bits_per_sample`, `sample_rate`, `channels`, and `bitstream_codec`. Detects DTS CDs, Dolby TrueHD, DTS-HD, Dolby Digital, and DSD bitstreams inside lossless containers using frame-chain validation via ffmpeg.

---

### [Cluster Refresh](https://github.com/rpmzine/picard-plugin-cluster-refresh)
Adds **Refresh from Disk** to the right-click menu on clusters and cluster files. Re-reads updated metadata from disk without re-dragging files from Finder — useful when editing in an external tagger (e.g. Yate) while Picard is open.

---

### [Grouping Tagger](https://github.com/rpmzine/picard-plugin-grouping-tagger)
Tags the `GROUPING` field with source, format, and quality information. Detects Vinyl · CD · Cassette · Digital · Bootleg · Remaster · Quality tier (Lossy / Lossless / Hi-Def). Supports custom templates with variables (`{SOURCE}`, `{FORMAT}`, `{QUALITY}`, …) and fixed tags, all configurable via an Options page. Templates and fixed tags are stored in a JSON file outside the plugin folder and survive updates.

---

### [Multidisc Tagger](https://github.com/rpmzine/picard-plugin-multidisc-tagger)
Sets `work`, `movement`, and `showmovement` tags for multidisc releases, enabling hierarchical display in music players (Apple Music, Roon). **Automatic mode:** activates when MusicBrainz provides disc subtitles. **Manual mode:** right-click → *Make it a Multidisc* to enter disc subtitles via dialog.

---

### [Suffix Appender](https://github.com/rpmzine/picard-plugin-suffix-appender)
Appends formula-based suffixes to album or track titles via the right-click context menu. Uses a variable language with smart detection and conditional rendering. Includes 12 default templates and unlimited custom templates via the Template Manager.

Example formulas:

| Formula | Result |
|---------|--------|
| `[<releasecountry> <format>] [<bits_per_sample>-<sample_rate\|khz>]` | `[US FLAC] [24-96]` |
| `[<releasecountry> <catalognumber> <format>]` | `[Japan TOCP-12345 FLAC]` |
| `[<releasecountry> <formatsize> <recordtype>]` | `[US 12" LP]` |

---

### [Tag Filter & Joiner](https://github.com/rpmzine/picard-plugin-tag-filter-joiner)
Removes unwanted tags and/or joins multi-value tags with custom separators. Configured via **Options → Plugins → Tag Filter and Joiner**. Supports all 69 standard MusicBrainz tags — set each to Ignore, Join, or leave as-is, with a configurable separator (default: ` / `).

---

## Installation

### Picard 3.0

Each plugin has its own repository. Install directly in Picard:

1. **Options → Plugins → Install Plugin**
2. Paste the URL of the plugin's `__init__.py` from its GitHub repo  
   (e.g. `https://raw.githubusercontent.com/rpmzine/picard-plugin-cluster-refresh/main/__init__.py`)

Or copy the plugin folder to:

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/MusicBrainz/Picard/plugins3/` |

### Picard 2.x

Copy the plugin folder to:

| Platform | Path |
|----------|------|
| macOS / Linux | `~/.config/MusicBrainz/Picard/plugins/` |
| Windows | `%APPDATA%\MusicBrainz\Picard\plugins\` |

---

## Development

This monorepo is the development home. Each plugin is published to its own repository for Picard catalog submission.

```
publish_plugins.sh                   # push all plugins to their individual repos
publish_plugins.sh suffix_appender   # push one plugin only
install_plugins.sh                   # copy all plugins to local Picard plugins3/ for testing
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for architecture notes, the `_compat.py` shim design, and the Picard 2.x / 3.0 API patterns.

---

## License

Each plugin specifies its own license (MIT or GPL-2.0). See the individual plugin repositories for details.

**Author:** [rpmzine](https://github.com/rpmzine)
