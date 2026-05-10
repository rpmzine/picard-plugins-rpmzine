# Album Subfolder Plugin — Development Notes

## Overview

After Picard saves a file to a flat destination folder, moves it into a subfolder named `Albumartist - Album` (or `Artist - Album` if albumartist is absent). No naming script changes required — works transparently via a post-save hook.

Example: `Picarded/1-01 Artist - Title.flac` → `Picarded/Artist - Album/1-01 Artist - Title.flac`

Context: Picard's file naming script (Preset 4: `[discnumber]-$num(track#) [artist] - [title]`) saves all files flat into the destination directory. This plugin adds the missing album-level subfolder without requiring script edits.

**Requirement**: Picard's "Move additional files" option must be **DISABLED**. With it enabled, Picard independently moves extras (jpg, cue, etc.) to the destination, which interferes with the plugin's sweep. With it disabled, all non-audio items stay in the source folder and the plugin moves everything itself.

---

## Architecture

### Two-phase operation

**Phase 1 — load time** (`_on_file_loaded` via `register_file_post_load_processor`):
Captures `source_dir = os.path.dirname(file.filename)` into `_source_map[id(file)]` before Picard moves anything. This is the only reliable moment: after save, `file.filename` already points to the destination.

**Phase 2 — save time** (`_album_subfolder` via `register_file_post_save_processor`):

Four sub-phases (see below).

---

### `_album_subfolder` — four phases

**Phase 1 — establish per-album state:**

- Pops `source_dir` from `_source_map` (captured at load time). If `source_dir == dest_dir` (retroactive re-save of already-saved files), clears it so sweep is skipped.
- Key is `source_dir` when available, otherwise `id(file)` as fallback.
- If key is new: snapshots extras from `source_dir` (files + dirs), creates state dict with `decision='pending'` and a `threading.Event`, sets `show_dialog = True`.
- Determines `is_last`: checks whether any entries in `_source_map` still point to the same `source_dir`. If none remain, this is the last file from that source.

**Phase 2 — resolve user decision:**

- If `show_dialog`: calls `_broker.ask(folder_name)` (blocks worker thread until user responds), then stores result in `_album_state[key]['decision']` and sets the `decision_event`.
- Otherwise: waits on `decision_event` (up to 600 s), then reads the stored decision under lock.
- Results: `'move'` (proceed), `'skip'` (one-time skip), `'disable'` (permanent disable).

**Phase 3 — collect sweep data on last file:**

- If `is_last`: pops the album state entry and extracts `sweep_source`, `sweep_files`, `sweep_dirs` for use in Phase 4.

**Phase 4 — apply decision:**

- `'disable'`: sets `config.setting["album_subfolder_move_files"] = False`; returns.
- `'skip'` (or timeout): returns without moving.
- `'move'`: `os.makedirs(target_dir)`, `shutil.move(dest_path, target_path)`, updates `file.filename`, then if `is_last` calls `_sweep`.

---

### `_DialogBroker` — thread-safe dialog

`_broker` is a `QObject` created on the main thread at module load time. Worker threads cannot call Qt UI functions directly, so the broker uses a queued signal/slot:

- `_request = pyqtSignal(str)` connected to `_show` with `Qt.QueuedConnection` — Qt delivers the signal on the main thread's event loop.
- `ask(folder_name)`: called from worker thread. Clears `threading.Event`, emits `_request`, then blocks with `_event.wait(timeout=600)`.
- `_show(folder_name)`: slot on the main thread. Shows a `QMessageBox` with three buttons:

  - **Move to Subfolder** (AcceptRole) → `'move'`
  - **Cancel** (RejectRole) → `'skip'` — skips this album once, plugin stays active
  - **Save Without Moving** (ActionRole) → `'disable'` — permanently disables the plugin

- After `msg.exec_()`, sets `_result` and calls `_event.set()`, unblocking the worker thread.

Multi-file albums: the first file's thread shows the dialog; other threads wait on `decision_event` inside `_album_state`. All threads read the same decision once it is set.

---

### Source-only sweep

With "Move additional files" disabled, nothing ever goes to `dest_dir` except the audio files Picard saves. All extras (artwork, cue sheets, checksums, `ARTWORK/` subdirectory, etc.) remain in `source_dir` until the plugin moves them.

`_sweep` therefore pulls exclusively from `source_dir` → `target_dir`. No destination scanning at all — eliminates any possibility of cross-album contamination in batch saves.

---

### "Last from source" detection

Replaces the earlier `_get_total` approach (which counted all album tracks and broke when saving a partial subset).

After popping the current file from `_source_map`, count how many remaining entries in `_source_map` still point to the same `source_dir`. If zero, this is the last file and `_sweep` should run.

This is exact and works for any batch size — a partial re-save of 3 out of 10 tracks triggers the sweep after the third file, not the tenth.

---

### Album-level state (`_album_state`)

A thread-safe dict (guarded by `threading.Lock`) keyed by `source_dir` (or `id(file)` as fallback when source is unavailable).

| Field | Purpose |
| --- | --- |
| `source_dir` | Original file location (e.g. `/Temp/Artist - Album/`) |
| `target_dir` | Album subfolder (e.g. `Picarded/Artist - Album/`) |
| `extra_files` | Non-audio filenames found in `source_dir` at init |
| `extra_dirs` | Subdirectory names found in `source_dir` at init |
| `decision` | `'pending'` → `'move'` / `'skip'` / `'disable'` |
| `decision_event` | `threading.Event` — set when decision is resolved |

Entry deleted once the last file from that source is processed.

---

### `_snapshot_extras`

Called once on first file of an album (only when `source_dir` is set and `source_dir != target_dir`). Lists everything in `source_dir`:

- `extra_files`: files whose extension is in `_ADDITIONAL_EXTS` (jpg, png, cue, log, etc.)
- `extra_dirs`: all subdirectories (e.g. `ARTWORK/`)

The `source_dir != target_dir` guard prevents snapshotting files that are already in the target, which would cause `shutil.move` to fail with "same file" errors.

---

### Side effect: retroactive organiser

Files already in the flat destination (`Picarded/track.flac`) have `dest_dir` equal to their load-time dir, so `source_dir` is cleared and sweep is skipped. Audio files are still moved to the subfolder. Intentional and useful.

---

## Options page

`AlbumSubfolderOptionsPage` (registered under `PARENT = "plugins"`) shows a single checkbox:

> Move files into 'Albumartist – Album' subfolder after saving

Backed by `config.setting["album_subfolder_move_files"]` (BoolOption, default `True`).

The dialog's **Save Without Moving** button also writes `False` to this setting, so the checkbox reflects both the manual and dialog-driven disable.

---

## Version History

- **1.0.0** — Initial release. Post-save mover, albumartist/artist fallback, filesystem sanitisation.
- **1.1.0** — Added sweep of artwork, cue sheets, checksums from flat destination.
- **1.2.0** — Sweep extended to subdirectories (e.g. `ARTWORK/`).
- **2.0.0** — Architecture rewrite. Deferred sweep (album completion). Source-folder reference via `file.orig_filename`. Thread-safe.
- **2.1.0** — Load-time source capture via `register_file_post_load_processor` + `_source_map`. Dropped `file.orig_filename` (unreliable across Picard versions). Sweep now pulls exclusively from `source_dir`; no destination scanning. Requires "Move additional files" to be disabled in Picard. Added `try/except` to `_on_file_loaded` to prevent SIGABRT from unhandled exception in PyQt5 event handler.
- **2.2.0** — Removed `_get_total`. Replaced with "last from source_dir" detection: counts remaining `_source_map` entries for the same `source_dir`. Added `source_dir != target_dir` guard before `_snapshot_extras` to prevent shutil.move same-path errors on retroactive re-saves.
- **2.3.0** — Added `BoolOption` and `AlbumSubfolderOptionsPage` with enable/disable checkbox.
- **2.4.0** — Added per-save confirmation dialog via `_DialogBroker`. Three buttons: Move to Subfolder (move), Cancel (one-time skip), Save Without Moving (permanent disable). Multi-file albums share a single dialog via `decision_event` coordination. Dialog runs on main thread via queued signal/slot; worker threads block on `threading.Event`.

---

## When Resuming Development

1. `_on_file_loaded` captures source dir at load time — this is the critical invariant. If `register_file_post_load_processor` fires after Picard has already moved the file (in a future Picard version), the plugin breaks. Verify with a quick print/log of `file.filename` inside `_on_file_loaded`.

2. "Move additional files" in Picard options must be **off**. If it is on, Picard moves extras to `dest_dir` before our sweep runs — they will not be in `source_dir` and will not be swept.

3. `extra_files` and `extra_dirs` are both swept from `source_dir` (not `dest_dir`). Do not change this without also re-evaluating the "disabled Move additional files" contract.

4. `file.filename` setter updates Picard's internal path reference after the audio file is moved.

5. `_album_state` key is `source_dir` (path string) when available — stable, album-specific. Falls back to `id(file)` only when source is unavailable (retroactive re-save).

6. If `source_dir` is unavailable or equals `dest_dir`, extras sweep is skipped — acceptable degraded behaviour.

7. `_broker` is a module-level singleton created at import time on the main thread. Its `threading.Event` is shared across all `ask()` calls — never call `ask()` concurrently from two threads. Current design serialises this naturally (one album at a time shows a dialog; others wait on `decision_event`).

8. The `_show` slot sets `_result` before `_event.set()`. If the dialog times out (600 s), `_result` retains its last value (`'move'` initial / previous call's result). This is benign: the most recently chosen action is used as the default.

Current stable version: **2.4.0**
Last updated: 2026-04-28
