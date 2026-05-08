# Cluster Refresh Plugin — Development Notes

## Overview

Adds a "Refresh from Disk" context menu action to clusters and individual files. Removes the selected files from Picard's internal state and re-adds them by filename, triggering a fresh metadata read from disk — useful after editing tags externally without wanting to re-drag files into Picard.

---

## Architecture

Single `BaseAction` subclass (`RefreshFromDiskAction`):
1. Resolves the full file list from the selection via `tagger.get_files_from_objects()`
2. Saves all filenames
3. Calls `tagger.remove_files(files, from_parent=True)`
4. Calls `tagger.add_files(filenames)`

Registered on both cluster and file context menus.

No configuration, no options page.

---

## Version History

- **1.0.0** — Initial release. Cluster and file context menu action.

---

## When Resuming Development

- Simple plugin; main risk area is Picard API changes to `remove_files` / `add_files` signatures across API versions
- If behaviour changes in a future Picard version, check `tagger.remove_files` signature first

Current stable version: **1.0.0**
Last updated: 2026-04-25
