# -*- coding: utf-8 -*-
PLUGIN_NAME = "Album Subfolder"
PLUGIN_AUTHOR = "rpmzine"
PLUGIN_DESCRIPTION = (
    "After saving, moves files into a subfolder named "
    "'Albumartist - Album' inside the destination folder. "
    "Also moves artwork, cue sheets, and subfolders (e.g. ARTWORK/) "
    "from the source folder into the subfolder. "
    "Requires 'Move additional files' to be DISABLED in Picard options."
)
PLUGIN_VERSION = "2.3.0"
PLUGIN_API_VERSIONS = ["2.10", "2.11", "2.12", "2.13"]
PLUGIN_LICENSE = "GPL-2.0"
PLUGIN_LICENSE_URL = "https://www.gnu.org/licenses/gpl-2.0.html"

import os
import re
import shutil
import threading

from picard import config, log
from picard.config import BoolOption
from picard.file import register_file_post_save_processor
from picard.metadata import register_track_metadata_processor
from picard.ui.options import OptionsPage, register_options_page

try:
    from PyQt6.QtWidgets import QCheckBox, QLabel, QVBoxLayout
except ImportError:
    from PyQt5.QtWidgets import QCheckBox, QLabel, QVBoxLayout

_ILLEGAL_CHARS = re.compile(r'[\x00-\x1f<>:"/\\|?*]')

_ADDITIONAL_EXTS = {
    '.jpg', '.jpeg', '.png', '.gif',
    '.bmp', '.tif', '.tiff', '.webp',
    '.cue', '.log', '.txt', '.nfo', '.pdf',
    '.md5', '.ffp', '.sha', '.sha256',
    '.m3u', '.m3u8',
}

_lock = threading.Lock()
_source_map = {}   # id(file) -> source_dir, captured before save
_album_state = {}  # key -> state dict (per album)

options = [
    BoolOption("setting", "album_subfolder_enabled", True),
]


# ── Options Page ───────────────────────────────────────────────────────────────

class AlbumSubfolderOptionsPage(OptionsPage):
    NAME = "album_subfolder"
    TITLE = "Album Subfolder"
    PARENT = "plugins"

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.enabled_cb = QCheckBox(
            "Move files into 'Albumartist - Album' subfolder after saving"
        )
        layout.addWidget(self.enabled_cb)

        note = QLabel(
            "When enabled, saved files are automatically moved into a subfolder\n"
            "named 'Albumartist - Album' inside the destination folder.\n"
            "Companion files (artwork, cue sheets, logs, subdirs) are moved too.\n\n"
            "Requires 'Move additional files' to be DISABLED in Picard options."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()

    def load(self):
        self.enabled_cb.setChecked(config.setting["album_subfolder_enabled"])

    def save(self):
        config.setting["album_subfolder_enabled"] = self.enabled_cb.isChecked()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sanitize(text):
    return _ILLEGAL_CHARS.sub('_', text).strip('. ')


def _snapshot_extras(source_dir):
    extra_files, extra_dirs = [], []
    try:
        for name in os.listdir(source_dir):
            path = os.path.join(source_dir, name)
            if os.path.isdir(path):
                extra_dirs.append(name)
            elif (os.path.isfile(path)
                  and os.path.splitext(name)[1].lower()
                  in _ADDITIONAL_EXTS):
                extra_files.append(name)
    except Exception as e:
        log.error("Album Subfolder: snapshot of %r failed — %s", source_dir, e)
    return extra_files, extra_dirs


def _sweep(source_dir, target_dir, extra_files, extra_dirs):
    for name in extra_files:
        src = os.path.join(source_dir, name)
        if os.path.isfile(src):
            try:
                shutil.move(src, os.path.join(target_dir, name))
                log.debug("Album Subfolder: file %r -> subfolder", name)
            except Exception as e:
                log.error("Album Subfolder: could not move %r — %s", src, e)
    for name in extra_dirs:
        src = os.path.join(source_dir, name)
        if os.path.exists(src):
            try:
                shutil.move(src, os.path.join(target_dir, name))
                log.debug("Album Subfolder: dir %r -> subfolder", name)
            except Exception as e:
                log.error("Album Subfolder: could not move %r — %s", src, e)


# ── Processors ────────────────────────────────────────────────────────────────

def _on_file_loaded(file):
    """Picard 2.x: capture source dir at file-load time."""
    try:
        with _lock:
            _source_map[id(file)] = os.path.dirname(file.filename)
    except Exception as e:
        log.error("Album Subfolder: failed to capture source dir — %s", e)


def _capture_source_from_track(tagger, metadata, track, release):
    """Picard 3.0 fallback: capture source dirs via track metadata processor.

    Runs before the user saves, so file.filename is still the source location.
    Only stores the id if not already present (avoids overwriting on re-process).
    """
    for f in getattr(track, 'linked_files', []):
        try:
            with _lock:
                if id(f) not in _source_map:
                    _source_map[id(f)] = os.path.dirname(f.filename)
        except Exception as e:
            log.error("Album Subfolder: failed to capture source dir — %s", e)


def _album_subfolder(file):
    if not config.setting.get("album_subfolder_enabled", True):
        return

    try:
        with _lock:
            pre_source = _source_map.pop(id(file), None)

        meta = file.metadata
        artist = (meta.get('albumartist') or meta.get('artist') or '').strip()
        album_tag = (meta.get('album') or '').strip()

        if not artist or not album_tag:
            log.debug("Album Subfolder: skipping %r — missing tags", file.filename)
            return

        folder_name = _sanitize(f"{artist} - {album_tag}")
        dest_path = file.filename
        dest_dir = os.path.dirname(dest_path)

        if os.path.basename(dest_dir) == folder_name:
            return  # already in the correct subfolder

        target_dir = os.path.join(dest_dir, folder_name)
        target_path = os.path.join(target_dir, os.path.basename(dest_path))

        with _lock:
            source_dir = pre_source
            if source_dir == dest_dir:
                source_dir = None  # retroactive re-save — skip sweep

            key = source_dir if source_dir else id(file)

            if key not in _album_state:
                extra_files, extra_dirs = [], []
                if source_dir and source_dir != target_dir:
                    extra_files, extra_dirs = _snapshot_extras(source_dir)
                _album_state[key] = {
                    'source_dir': source_dir,
                    'target_dir': target_dir,
                    'extra_files': extra_files,
                    'extra_dirs': extra_dirs,
                }

            if source_dir:
                remaining = sum(1 for s in _source_map.values() if s == source_dir)
                is_last = (remaining == 0)
            else:
                is_last = True

        os.makedirs(target_dir, exist_ok=True)
        shutil.move(dest_path, target_path)
        file.filename = target_path
        log.debug("Album Subfolder: %r -> %r", dest_path, target_path)

        if is_last:
            with _lock:
                s = _album_state.pop(key, None)
            if s and s['source_dir']:
                _sweep(s['source_dir'], target_dir, s['extra_files'], s['extra_dirs'])

    except Exception as e:
        log.error("Album Subfolder: failed to organise %r — %s", file.filename, e)


# ── Registration ───────────────────────────────────────────────────────────────

# Source-dir capture: post-load processor (Picard 2.x) or track metadata
# processor (Picard 3.0, which removed register_file_post_load_processor).
try:
    from picard.file import register_file_post_load_processor
    register_file_post_load_processor(_on_file_loaded)
except ImportError:
    register_track_metadata_processor(_capture_source_from_track, priority=0)

register_file_post_save_processor(_album_subfolder)
register_options_page(AlbumSubfolderOptionsPage)
