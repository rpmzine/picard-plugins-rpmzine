# Artwork Searcher Plugin — Development Notes

## Overview

Two `BaseAction` subclasses registered on all four Picard context menus (file, track, cluster, album). Each opens one browser tab per unique search query derived from the selected objects' metadata.

---

## Architecture

### Query building (`_get_query`)

Priority order:
1. `albumartist` (or `artist`) + `album` tag → `"Artist Album album cover"`
2. `albumartist` (or `artist`) + parent folder name of the first file → fallback when `album` tag is absent
3. Returns `None` if neither artist nor album/folder can be resolved

### Deduplication (`_collect_queries`)

Iterates objects, calls `_get_query` on each, collects into an ordered list with a `seen` set to suppress duplicates. One browser tab per unique query.

### Actions

| Class | Menu label | URL pattern |
|---|---|---|
| `SearchArtworkGoogle` | Search Artwork → Google Images | `google.com/search?q=...&tbm=isch&tbs=isz:l` |
| `SearchArtworkBing` | Search Artwork → Bing Images | `bing.com/images/search?q=...&qft=+filterui:imagesize-large` |

### Registration guard

`_registered` flag prevents double-registration if both import-time and `plugin_loaded` paths run.

---

## Version History

- **1.0.0** — Initial release

---

## When Resuming Development

- Adding more search engines: subclass `BaseAction`, build the URL, add the instance to the loop in `_register_actions`
- The `→` arrows in `NAME` are Unicode U+2192 — Picard renders them correctly in context menus
- `webbrowser.open` uses the system default browser; no control over which browser opens
- If Picard ever exposes a `thumbnail_url` on album objects, that could seed a reverse image search

Current stable version: **1.0.0**
Last updated: 2026-05-07
