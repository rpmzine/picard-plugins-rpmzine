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
#
# PyQt6 moved from flat to scoped enums (QMessageBox.Yes →
# QMessageBox.StandardButton.Yes etc.). We expose compat subclasses that add
# the flat names back so plugin code works unchanged in both Qt versions.

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

# ── PyQt6 scoped-enum compatibility ────────────────────────────────────────────
# PyQt6 replaced flat enums with scoped ones. We create thin subclasses that
# re-expose the PyQt5 names, then patch them back onto the QtWidgets module so
# that `QtWidgets.QMessageBox.Yes` etc. continue to work.

if _PYQT6:
    class QMessageBox(QtWidgets.QMessageBox):
        Yes         = QtWidgets.QMessageBox.StandardButton.Yes
        No          = QtWidgets.QMessageBox.StandardButton.No
        Ok          = QtWidgets.QMessageBox.StandardButton.Ok
        Cancel      = QtWidgets.QMessageBox.StandardButton.Cancel
        Question    = QtWidgets.QMessageBox.Icon.Question
        Information = QtWidgets.QMessageBox.Icon.Information
        Warning     = QtWidgets.QMessageBox.Icon.Warning
        Critical    = QtWidgets.QMessageBox.Icon.Critical

    class QDialogButtonBox(QtWidgets.QDialogButtonBox):
        Ok     = QtWidgets.QDialogButtonBox.StandardButton.Ok
        Cancel = QtWidgets.QDialogButtonBox.StandardButton.Cancel
        Yes    = QtWidgets.QDialogButtonBox.StandardButton.Yes
        No     = QtWidgets.QDialogButtonBox.StandardButton.No

    class QDialog(QtWidgets.QDialog):
        Accepted = QtWidgets.QDialog.DialogCode.Accepted
        Rejected = QtWidgets.QDialog.DialogCode.Rejected

    class QSizePolicy(QtWidgets.QSizePolicy):
        Expanding = QtWidgets.QSizePolicy.Policy.Expanding
        Fixed     = QtWidgets.QSizePolicy.Policy.Fixed
        Minimum   = QtWidgets.QSizePolicy.Policy.Minimum
        Maximum   = QtWidgets.QSizePolicy.Policy.Maximum
        Preferred = QtWidgets.QSizePolicy.Policy.Preferred

    class QFrame(QtWidgets.QFrame):
        NoFrame     = QtWidgets.QFrame.Shape.NoFrame
        StyledPanel = QtWidgets.QFrame.Shape.StyledPanel
        Panel       = QtWidgets.QFrame.Shape.Panel
        Sunken      = QtWidgets.QFrame.Shadow.Sunken
        Raised      = QtWidgets.QFrame.Shadow.Raised
        Plain       = QtWidgets.QFrame.Shadow.Plain

    # Patch back onto QtWidgets so code using QtWidgets.QMessageBox.Yes etc. works
    QtWidgets.QMessageBox     = QMessageBox
    QtWidgets.QDialogButtonBox = QDialogButtonBox
    QtWidgets.QDialog         = QDialog
    QtWidgets.QSizePolicy     = QSizePolicy
    QtWidgets.QFrame          = QFrame

    # Qt namespace proxy: exposes PyQt5-style flat names for the common enums
    class _QtNS:
        AlignCenter  = QtCore.Qt.AlignmentFlag.AlignCenter
        AlignLeft    = QtCore.Qt.AlignmentFlag.AlignLeft
        AlignRight   = QtCore.Qt.AlignmentFlag.AlignRight
        AlignTop     = QtCore.Qt.AlignmentFlag.AlignTop
        AlignBottom  = QtCore.Qt.AlignmentFlag.AlignBottom
        AlignVCenter = QtCore.Qt.AlignmentFlag.AlignVCenter
        AlignHCenter = QtCore.Qt.AlignmentFlag.AlignHCenter
        Checked          = QtCore.Qt.CheckState.Checked
        Unchecked        = QtCore.Qt.CheckState.Unchecked
        PartiallyChecked = QtCore.Qt.CheckState.PartiallyChecked
        ScrollBarAsNeeded  = QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        ScrollBarAlwaysOff = QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        ScrollBarAlwaysOn  = QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn

        def __getattr__(self, name):
            return getattr(QtCore.Qt, name)

    Qt = _QtNS()
else:
    QMessageBox     = QtWidgets.QMessageBox
    QDialogButtonBox = QtWidgets.QDialogButtonBox
    QDialog         = QtWidgets.QDialog
    QSizePolicy     = QtWidgets.QSizePolicy
    QFrame          = QtWidgets.QFrame
    Qt              = QtCore.Qt

# ── Remaining widget aliases ───────────────────────────────────────────────────
QCheckBox    = QtWidgets.QCheckBox
QComboBox    = QtWidgets.QComboBox
QGridLayout  = QtWidgets.QGridLayout
QGroupBox    = QtWidgets.QGroupBox
QHBoxLayout  = QtWidgets.QHBoxLayout
QLabel       = QtWidgets.QLabel
QLineEdit    = QtWidgets.QLineEdit
QPushButton  = QtWidgets.QPushButton
QScrollArea  = QtWidgets.QScrollArea
QVBoxLayout  = QtWidgets.QVBoxLayout
QWidget      = QtWidgets.QWidget

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
