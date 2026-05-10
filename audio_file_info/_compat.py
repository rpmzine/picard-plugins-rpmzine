# Picard 2.x / 3.0 import compatibility shim.
#
# Detection strategy: probe for PyQt6 *features* rather than relying on
# sys.modules key names, which PyInstaller/mypyc bundles may register
# differently.  If QMessageBox.StandardButton exists we are on PyQt6 and
# build compat subclasses; otherwise we are on PyQt5 and do nothing.
#
# exec_() was renamed to exec() in PyQt6.  We add it back as a real Python
# wrapper method (not a SIP slot alias, which fails with unbound-method errors).
#
# Qt enum proxy: _QtNS.__getattr__ tries flat access first (PyQt5 style),
# then searches scoped namespaces (PyQt6 style), so Qt.UserRole etc. work
# regardless of which Qt binding is in use.

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

if QtCore is None:
    try:
        from PyQt6 import QtCore, QtGui, QtWidgets
    except Exception:
        from PyQt5 import QtCore, QtGui, QtWidgets

# ── Universal Qt namespace proxy ───────────────────────────────────────────────
# Tries flat access first (PyQt5), then searches scoped enum namespaces (PyQt6).
_sentinel = object()
_QT6_SCOPES = (
    'AlignmentFlag', 'CheckState', 'ScrollBarPolicy', 'ItemDataRole',
    'TextFormat', 'WindowType', 'CursorShape', 'FocusPolicy',
    'ContextMenuPolicy', 'Orientation', 'LayoutDirection', 'SortOrder',
    'MatchFlag', 'ItemFlag', 'TextInteractionFlag', 'ToolButtonStyle',
    'WindowModality', 'Key', 'Modifier', 'DropAction', 'ScrollHint',
)

class _QtNS:
    def __getattr__(self, name):
        val = getattr(QtCore.Qt, name, _sentinel)
        if val is not _sentinel:
            return val
        for _scope_name in _QT6_SCOPES:
            _scope = getattr(QtCore.Qt, _scope_name, None)
            if _scope is not None:
                val = getattr(_scope, name, _sentinel)
                if val is not _sentinel:
                    return val
        raise AttributeError(f"Qt has no attribute {name!r}")

Qt = _QtNS()

# ── PyQt6 scoped-enum widget compat ────────────────────────────────────────────
# Probe by trying to access QMessageBox.StandardButton (PyQt6 only).
# On PyQt5 the AttributeError is caught and we leave Qt widgets untouched.
try:
    _MB = QtWidgets.QMessageBox.StandardButton  # KeyError / AttributeError on PyQt5

    class QMessageBox(QtWidgets.QMessageBox):
        Yes         = _MB.Yes
        No          = _MB.No
        Ok          = _MB.Ok
        Cancel      = _MB.Cancel
        Question    = QtWidgets.QMessageBox.Icon.Question
        Information = QtWidgets.QMessageBox.Icon.Information
        Warning     = QtWidgets.QMessageBox.Icon.Warning
        Critical    = QtWidgets.QMessageBox.Icon.Critical
        AcceptRole      = QtWidgets.QMessageBox.ButtonRole.AcceptRole
        RejectRole      = QtWidgets.QMessageBox.ButtonRole.RejectRole
        DestructiveRole = QtWidgets.QMessageBox.ButtonRole.DestructiveRole
        def exec_(self): return super().exec()

    class QDialogButtonBox(QtWidgets.QDialogButtonBox):
        Ok     = QtWidgets.QDialogButtonBox.StandardButton.Ok
        Cancel = QtWidgets.QDialogButtonBox.StandardButton.Cancel
        Yes    = QtWidgets.QDialogButtonBox.StandardButton.Yes
        No     = QtWidgets.QDialogButtonBox.StandardButton.No

    class QDialog(QtWidgets.QDialog):
        Accepted = QtWidgets.QDialog.DialogCode.Accepted
        Rejected = QtWidgets.QDialog.DialogCode.Rejected
        def exec_(self): return super().exec()

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

    # Patch compat classes back so QtWidgets.QMessageBox.Yes etc. work everywhere
    QtWidgets.QMessageBox      = QMessageBox
    QtWidgets.QDialogButtonBox = QDialogButtonBox
    QtWidgets.QDialog          = QDialog
    QtWidgets.QSizePolicy      = QSizePolicy
    QtWidgets.QFrame           = QFrame

    _PYQT6 = True

except AttributeError:
    # PyQt5: flat enums already work, no compat subclasses needed
    QMessageBox      = QtWidgets.QMessageBox
    QDialogButtonBox = QtWidgets.QDialogButtonBox
    QDialog          = QtWidgets.QDialog
    QSizePolicy      = QtWidgets.QSizePolicy
    QFrame           = QtWidgets.QFrame
    _PYQT6 = False

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
# QAction moved from QtWidgets to QtGui in Qt6/PyQt6.
_QActionBase = getattr(QtGui, 'QAction', None) or getattr(QtWidgets, 'QAction', None)


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
