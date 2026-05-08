# Picard 2.x / 3.0 import compatibility shim.
#
# In Picard 3.0 (PyInstaller / mypyc bundle) `from PyQt6 import ...` inside a
# plugin can raise non-ImportError exceptions. We therefore read Qt modules from
# sys.modules, which Picard has already populated at startup. On Picard 2.x we
# do a normal PyQt5 import as a fallback.

import sys as _sys

# ── PyQt ───────────────────────────────────────────────────────────────────────
# Prefer whatever Qt the running Picard already loaded (safe in frozen builds).
QtCore = (
    _sys.modules.get('PyQt6.QtCore')
    or _sys.modules.get('PyQt5.QtCore')
)
QtGui = (
    _sys.modules.get('PyQt6.QtGui')
    or _sys.modules.get('PyQt5.QtGui')
)
QtWidgets = (
    _sys.modules.get('PyQt6.QtWidgets')
    or _sys.modules.get('PyQt5.QtWidgets')
)

_PYQT6 = bool(_sys.modules.get('PyQt6.QtCore'))

# If not yet in sys.modules (e.g. running tests outside Picard), fall back to
# a direct import.
if QtCore is None:
    try:
        from PyQt6 import QtCore, QtGui, QtWidgets
        _PYQT6 = True
    except Exception:
        from PyQt5 import QtCore, QtGui, QtWidgets
        _PYQT6 = False

# Convenience re-exports for plugins that do `from .._compat import Qt, QLabel ...`
Qt = QtCore.Qt

QCheckBox = QtWidgets.QCheckBox
QComboBox = QtWidgets.QComboBox
QDialog = QtWidgets.QDialog
QDialogButtonBox = QtWidgets.QDialogButtonBox
QFrame = QtWidgets.QFrame
QGridLayout = QtWidgets.QGridLayout
QGroupBox = QtWidgets.QGroupBox
QHBoxLayout = QtWidgets.QHBoxLayout
QLabel = QtWidgets.QLabel
QLineEdit = QtWidgets.QLineEdit
QMessageBox = QtWidgets.QMessageBox
QPushButton = QtWidgets.QPushButton
QScrollArea = QtWidgets.QScrollArea
QSizePolicy = QtWidgets.QSizePolicy
QVBoxLayout = QtWidgets.QVBoxLayout
QWidget = QtWidgets.QWidget

# ── BaseAction ─────────────────────────────────────────────────────────────────
# Define our own guaranteed fallback first so the name is always bound.
_QActionBase = QtGui.QAction if _PYQT6 else QtWidgets.QAction


class BaseAction(_QActionBase):
    """Compatibility base class for plugin context-menu actions."""
    NAME = "Unknown"
    TITLE = None    # Picard 3.0 style; falls back to NAME
    MENU = []

    def __init__(self, api=None, parent=None):
        title = self.TITLE if self.TITLE is not None else self.NAME
        super().__init__(title, parent)
        self.tagger = QtCore.QCoreApplication.instance()
        self.triggered.connect(self._run_callback)

    def _run_callback(self):
        if self.tagger and hasattr(self.tagger, 'window'):
            self.callback(self.tagger.window.selected_objects)

    def callback(self, objs):
        raise NotImplementedError


# Try to upgrade to the real Picard BaseAction (already in sys.modules).
# picard.plugin3.api is the official V3 path; picard.ui.itemviews is Picard 2.x.
for _mod_name in ('picard.plugin3.api', 'picard.extension_points.item_actions',
                  'picard.ui.itemviews'):
    _mod = _sys.modules.get(_mod_name)
    if _mod is not None and hasattr(_mod, 'BaseAction'):
        BaseAction = _mod.BaseAction  # noqa: F811
        break

# ── File event processors ──────────────────────────────────────────────────────
_event_hooks = _sys.modules.get('picard.extension_points.event_hooks')
if _event_hooks is not None:
    register_file_post_load_processor = getattr(_event_hooks, 'register_file_post_load_processor', None)
    register_file_post_save_processor = getattr(_event_hooks, 'register_file_post_save_processor', None)
    register_file_pre_save_processor = getattr(_event_hooks, 'register_file_pre_save_processor', None)
else:
    _picard_file = _sys.modules.get('picard.file')
    register_file_post_load_processor = getattr(_picard_file, 'register_file_post_load_processor', None)
    register_file_post_save_processor = getattr(_picard_file, 'register_file_post_save_processor', None)
    register_file_pre_save_processor = None

# ── Metadata processors ────────────────────────────────────────────────────────
_meta = _sys.modules.get('picard.extension_points.metadata') or _sys.modules.get('picard.metadata')
register_album_metadata_processor = getattr(_meta, 'register_album_metadata_processor', None)
register_track_metadata_processor = getattr(_meta, 'register_track_metadata_processor', None)

# ── Item actions: register_* functions ────────────────────────────────────────
_item_actions = (
    _sys.modules.get('picard.extension_points.item_actions')
    or _sys.modules.get('picard.ui.itemviews')
)
register_album_action = getattr(_item_actions, 'register_album_action', None)
register_cluster_action = getattr(_item_actions, 'register_cluster_action', None)
register_file_action = getattr(_item_actions, 'register_file_action', None)
register_track_action = getattr(_item_actions, 'register_track_action', None)

# ── Options pages ──────────────────────────────────────────────────────────────
_opts = (
    _sys.modules.get('picard.extension_points.options_pages')
    or _sys.modules.get('picard.ui.options')
)
register_options_page = getattr(_opts, 'register_options_page', None)
