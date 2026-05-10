# Artwork Searcher — Development Notes

## Version History

### 1.0.0 (2026-04-11)
- Initial release.
- Two context menu actions: **Search Artwork → Google Images** and **Search Artwork → Bing Images**.
- Registered for files, tracks, clusters, and albums.
- Query = `albumartist` (or `artist`) + `album` tag + `"album cover"`.
- Falls back to folder name when no `album` tag is present (useful for untagged clusters).
- Deduplication: multiple selected files from the same album open only one browser tab.
- High-quality filter applied: Google `tbs=isz:l`, Bing `filterui:imagesize-large`.
- Uses Python `webbrowser.open()` — no GUI, just opens the default browser.
