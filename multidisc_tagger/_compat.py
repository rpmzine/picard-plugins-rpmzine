# Picard 2.x / 3.0 import compatibility shim.
#
# In Picard 3.0 (PyInstaller / mypyc bundle) `from PyQt6 import ...` inside a
# plugin can raise non-ImportError exceptions. We therefore read Qt modules from
# sys.modules, which Picard has already populated at startup. On Picard 2.x we
# do a normal PyQt5 import as a fallback.
#
# All register_* helpers use lazy lookup: they resolve from sys.modules at each
# *call*, not at import time. This makes them safe whether called at module
# level or inside enable(api), regardless of Picard's initialisation order.

import sys as _sys

# ── PyQt ───────────────────────────────────────────────────────────────────────
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

if QtCore is None:
    try:
        from PyQt6 import QtCore, QtGui, QtWidgets
        _PYQT6 = True
    except Exception:
        from PyQt5 import QtCore, QtGui, QtWidgets
        _PYQT6 = False

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
_QActionBase = QtGui.QAction if _PYQT6 else QtWidgets.QAction


class BaseAction(_QActionBase):
    """Compatibility base class for plugin context-menu actions."""
    NAME = "Unknown"
    TITLE = None
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


for _mod_name in ('picard.plugin3.api', 'picard.extension_points.item_actions',
                  'picard.ui.itemviews'):
    _mod = _sys.modules.get(_mod_name)
    if _mod is not None and hasattr(_mod, 'BaseAction'):
        BaseAction = _mod.BaseAction  # noqa: F811
        break

# ── OptionsPage ────────────────────────────────────────────────────────────────
# Resolved lazily at access time; falls back to a no-op stub so class definitions
# that inherit from it don't fail when running outside Picard.
def _resolve_options_page():
    for _mod_name in ('picard.ui.options', 'picard.extension_points.options_pages'):
        _mod = _sys.modules.get(_mod_name)
        if _mod is not None:
            cls = getattr(_mod, 'OptionsPage', None)
            if cls is not None:
                return cls
    return None

OptionsPage = _resolve_options_page()

if OptionsPage is None:
    try:
        from picard.ui.options import OptionsPage
    except Exception:
        class OptionsPage:  # noqa: F811
            """Stub used outside Picard."""
            NAME = ""
            TITLE = ""
            PARENT = "plugins"
            def __init__(self, parent=None): pass
            def load(self): pass
            def save(self): pass

# ── Lazy registration helpers ──────────────────────────────────────────────────

def _lazy(fn_name, *module_names):
    """Return a wrapper that looks up fn_name in sys.modules at call time."""
    def _wrapper(*args, **kwargs):
        for mod_name in module_names:
            mod = _sys.modules.get(mod_name)
            if mod is not None:
                fn = getattr(mod, fn_name, None)
                if fn is not None:
                    return fn(*args, **kwargs)
    return _wrapper

def _has_register(fn_name, *module_names):
    """Return True if fn_name is currently available in any of the modules."""
    for mod_name in module_names:
        mod = _sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, fn_name):
            return True
    return False

# ── File event processors ──────────────────────────────────────────────────────
register_file_post_load_processor = _lazy(
    'register_file_post_load_processor',
    'picard.extension_points.event_hooks', 'picard.file')
register_file_post_save_processor = _lazy(
    'register_file_post_save_processor',
    'picard.extension_points.event_hooks', 'picard.file')
register_file_pre_save_processor = _lazy(
    'register_file_pre_save_processor',
    'picard.extension_points.event_hooks', 'picard.file')

# ── Metadata processors ────────────────────────────────────────────────────────
register_album_metadata_processor = _lazy(
    'register_album_metadata_processor',
    'picard.extension_points.metadata', 'picard.metadata')
register_track_metadata_processor = _lazy(
    'register_track_metadata_processor',
    'picard.extension_points.metadata', 'picard.metadata')

# ── Item actions ───────────────────────────────────────────────────────────────
register_album_action = _lazy(
    'register_album_action',
    'picard.extension_points.item_actions', 'picard.ui.itemviews')
register_cluster_action = _lazy(
    'register_cluster_action',
    'picard.extension_points.item_actions', 'picard.ui.itemviews')
register_file_action = _lazy(
    'register_file_action',
    'picard.extension_points.item_actions', 'picard.ui.itemviews')
register_track_action = _lazy(
    'register_track_action',
    'picard.extension_points.item_actions', 'picard.ui.itemviews')

# ── Options pages ──────────────────────────────────────────────────────────────
register_options_page = _lazy(
    'register_options_page',
    'picard.extension_points.options_pages', 'picard.ui.options')
