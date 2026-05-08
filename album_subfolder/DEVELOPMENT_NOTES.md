# Album Subfolder Plugin — Development Notes

## Overview

Registers two Picard post-processors:
1. `_on_file_loaded` — captures the source directory of each file at load time
2. `_album_subfolder` — runs after each save; moves the file into `<dest>/<Albumartist - Album>/` and, once all files from the same source folder are saved, sweeps companion files and subdirectories across

---

## Architecture

### State

| Variable | Purpose |
|---|---|
| `_source_map` | `id(file) → source_dir` — captured at load time, popped on save |
| `_album_state` | `source_dir → {source_dir, target_dir, extra_files, extra_dirs}` — per-album sweep state |
| `_lock` | `threading.Lock` protecting both dicts |

### Flow

1. **File loaded** → `_on_file_loaded` stores `os.path.dirname(file.filename)` in `_source_map`
2. **File saved** → `_album_subfolder` runs:
   - Pops the pre-save source from `_source_map`
   - Sanitises `Albumartist - Album` (strips illegal filesystem chars)
   - Skips if the file is already in the correct subfolder
   - On first file from a source dir, snapshots companion files/subdirs via `_snapshot_extras`
   - Moves the audio file via `shutil.move`
   - If this is the last file from that source dir (`remaining == 0`), triggers `_sweep`

### Companion sweep (`_sweep`)

Moves each snapshotted file/dir from `source_dir` to `target_dir`. Errors are logged but do not abort the sweep.

### Retroactive re-save guard

If `source_dir == dest_dir` at save time, it means the file was already in the destination (a re-save, not a first-time move). In that case `source_dir` is set to `None` and the sweep is skipped.

---

## Key risks

- **OneDrive / network drives** — `shutil.move` across volumes does a copy+delete; if interrupted mid-move, files can be lost. Consider adding a pre-move copy check for network paths.
- **Parallel saves** — the lock protects `_source_map` and `_album_state`, but `shutil.move` itself is not atomic.
- **Missing tags** — if `albumartist`/`artist` or `album` is empty, the plugin skips the file silently.

---

## Version History

- **2.2.0** — Thread-safe with `threading.Lock`; subdirectories swept in addition to flat files; snapshot taken at load time
- **2.1.x** — Extra-files snapshot at load time to avoid race conditions
- **2.0.0** — Initial release

---

## When Resuming Development

- Check `register_file_post_save_processor` signature if upgrading Picard API target
- `_source_map` uses `id(file)` as key — safe within a session, but `id` can be reused if a file object is garbage-collected and a new one allocated before save; mitigated by popping immediately on save
- `_snapshot_extras` runs inside the lock — keep it fast (just `os.listdir`, no I/O)

Current stable version: **2.2.0**
Last updated: 2026-05-07
