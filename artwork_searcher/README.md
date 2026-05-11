# Artwork Searcher

**Version:** 1.0.0
**Author:** rpmzine
**API Versions:** 2.10, 2.11, 2.12, 2.13, 3.0
**License:** GPL-2.0

## Description

Adds right-click context menu actions that open a browser image search for album artwork using the artist and album title. Works on files, tracks, clusters, and albums. Supports both Google Images and Bing Images, filtered to large images.

## Installation

1. Copy the `artwork_searcher` folder to your Picard plugins directory:
   - macOS: `~/.config/MusicBrainz/Picard/plugins`
2. Restart MusicBrainz Picard
3. Enable the plugin in Options → Plugins

## Usage

1. Right-click any file, track, cluster, or album in Picard
2. Choose **"Search Artwork → Google Images"** or **"Search Artwork → Bing Images"**
3. A browser tab opens with a large-image-filtered search for `<Albumartist> <Album> album cover`

### Query resolution

| Available metadata | Search query used |
|---|---|
| `albumartist` + `album` tag | `Albumartist Album album cover` |
| `artist` + `album` tag | `Artist Album album cover` |
| `albumartist`/`artist` + folder name | `Artist FolderName album cover` (fallback when no album tag) |

- If multiple objects are selected, duplicate queries are suppressed — one browser tab per unique query
- Google search uses `tbm=isch&tbs=isz:l` (Images, Large)
- Bing search uses `qft=+filterui:imagesize-large` (Large)

## Changelog

### Version 1.0.0
- Initial release
- Google Images and Bing Images actions on file, track, cluster, and album context menus
- Folder-name fallback when album tag is absent
- Duplicate query suppression for multi-selection
