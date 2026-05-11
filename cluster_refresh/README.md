# Cluster Refresh

**Version:** 1.0.0
**Author:** rpmzine
**API Versions:** 2.10, 2.11, 2.12, 2.13, 3.0
**License:** MIT

## Description

When you edit files in an external tagger (e.g. Yate) while Picard is open, Picard does not automatically detect the changes. Previously, the only way to see updated metadata was to delete the files from Picard's cluster panel and re-drag them from Finder.

This plugin adds a **"Refresh from Disk"** right-click menu option that re-reads the files directly, without touching Finder.

Works with any file format Picard supports: FLAC, M4A/AAC, MP3, AIFF, WAV, etc.

## Installation

1. Copy the `cluster_refresh` folder to your Picard plugins directory:
   - macOS: `~/.config/MusicBrainz/Picard/plugins`
2. Restart MusicBrainz Picard
3. Enable the plugin in Options → Plugins

## Usage

1. Edit your files in Yate (or any other external tagger) and save
2. In Picard, right-click on a **cluster** or one or more **individual files** in the cluster panel
3. Select **"Refresh from Disk"**
4. Picard re-reads the files from disk — updated metadata appears immediately

### Notes

- If metadata changes cause files to belong to a different album, Picard may re-cluster them automatically
- Works on single files, multiple selected files, or an entire cluster at once
- The action is only available in the cluster (left) panel — not on matched albums

## Changelog

### Version 1.0.0
- Initial release
- "Refresh from Disk" action available on clusters and individual cluster files
- Supports all file formats: FLAC, M4A/AAC, MP3, AIFF, WAV, and more
- Picard 3.0 compatible: uses V3 API (`enable(api)`) and reads `.files` attribute directly from cluster/album objects
