# Tag Filter & Joiner Plugin — Development Notes

## Overview

Adds an Options page (Picard preferences → Plugins → Tag Filter and Joiner) to configure per-tag behaviour during metadata processing:
- **Ignore**: delete the tag from metadata before it is written to files
- **Join**: collapse multi-value tags into a single string using a configurable separator (default ` / `)

Processes all standard MusicBrainz tags listed in `STANDARD_TAGS`.

---

## Architecture

### Options page
Scrollable grid UI built entirely in code (no external `.ui` file referenced at runtime — the `options_tag_filter_joiner.ui` file in this folder is a legacy artefact). One row per tag with: tag name label, Ignore checkbox, Join checkbox, Separator text field (enabled only when Join is checked).

### Processing
`process_track_metadata()` is registered as a `register_track_metadata_processor`. On each track:
1. Iterates over all tags in metadata
2. If `tag_filter_ignore_<tag>` is `True` → deletes the tag
3. If `tag_filter_join_<tag>` is `True` and the tag has multiple values → joins them with the configured separator

### Settings storage
Per-tag settings stored in Picard config as:
- `tag_filter_ignore_<tag>` (bool)
- `tag_filter_join_<tag>` (bool)
- `tag_filter_sep_<tag>` (str, default ` / `)

`BoolOption` and `TextOption` are declared at module level for all tags in `STANDARD_TAGS` to ensure they exist in config before the options page loads.

### Registration note
`plugin_loaded()` is never called in this installation — components are registered at import time as a workaround. The `plugin_loaded` function is kept for completeness but logs a warning if it fires.

---

## Version History

- **0.9.5** — Current. Full tag list, scrollable grid UI, join separator per tag.

---

## When Resuming Development

1. Check `PLUGIN_VERSION` in `__init__.py`
2. `options_tag_filter_joiner.py` and `.ui` in this folder are legacy files — the active UI is built inline in `__init__.py`; do not rely on the `.ui` file
3. If adding new tags, add them to `STANDARD_TAGS` and bump the version — the `BoolOption`/`TextOption` declarations are generated from that list automatically
4. The `plugin_loaded` timing issue is why registration is done at import time — do not move it

Current stable version: **0.9.5**
Last updated: 2026-04-25
