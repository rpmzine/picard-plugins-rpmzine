# Picard 2.x / 3.0 import compatibility shim.
# In Picard 3.0 all register_* functions AND BaseAction moved to
# picard.extension_points.*. PyQt5 → PyQt6.

# ── PyQt ───────────────────────────────────────────────────────────────────────
try:
    from PyQt6 import QtCore, QtGui, QtWidgets
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFrame, QGridLayout,
        QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
        QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
    )
    _PYQT6 = True
except ImportError:
    from PyQt5 import QtCore, QtGui, QtWidgets
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import (
        QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFrame, QGridLayout,
        QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
        QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
    )
    _PYQT6 = False

# ── File event processors ──────────────────────────────────────────────────────
try:
    from picard.extension_points.event_hooks import (
        register_file_post_load_processor,
        register_file_post_save_processor,
        register_file_pre_save_processor,
    )
except ImportError:
    # Picard 2.x
    try:
        from picard.file import register_file_post_load_processor
    except ImportError:
        register_file_post_load_processor = None
    try:
        from picard.file import register_file_post_save_processor
    except ImportError:
        register_file_post_save_processor = None
    register_file_pre_save_processor = None

# ── Metadata processors ────────────────────────────────────────────────────────
try:
    from picard.extension_points.metadata import (
        register_album_metadata_processor,
        register_track_metadata_processor,
    )
except ImportError:
    from picard.metadata import (
        register_album_metadata_processor,
        register_track_metadata_processor,
    )

# ── Item actions: register_* functions ────────────────────────────────────────
try:
    from picard.extension_points.item_actions import (
        register_album_action,
        register_cluster_action,
        register_file_action,
        register_track_action,
    )
except ImportError:
    from picard.ui.itemviews import (
        register_album_action,
        register_cluster_action,
        register_file_action,
        register_track_action,
    )

# ── BaseAction ─────────────────────────────────────────────────────────────────
# Use broad except: mypyc-compiled builds can raise non-ImportError on circular
# imports between picard.extension_points.item_actions and picard.plugin.
try:
    from picard.extension_points.item_actions import BaseAction
except Exception:
    try:
        from picard.ui.itemviews import BaseAction
    except Exception:
        _QActionBase = QtGui.QAction if _PYQT6 else QtWidgets.QAction

        class BaseAction(_QActionBase):
            NAME = "Unknown"
            MENU = []

            def __init__(self, api=None, parent=None):
                super().__init__(getattr(self, 'TITLE', self.NAME), parent)
                self.tagger = QtCore.QCoreApplication.instance()
                self.triggered.connect(self._run_callback)

            def _run_callback(self):
                if self.tagger and hasattr(self.tagger, 'window'):
                    self.callback(self.tagger.window.selected_objects)

            def callback(self, objs):
                raise NotImplementedError

# ── Options pages ──────────────────────────────────────────────────────────────
try:
    from picard.extension_points.options_pages import register_options_page
except ImportError:
    from picard.ui.options import register_options_page
