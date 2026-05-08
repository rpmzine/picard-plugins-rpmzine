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

# ── Item actions & BaseAction ──────────────────────────────────────────────────
try:
    from picard.extension_points.item_actions import (
        BaseAction,
        register_album_action,
        register_cluster_action,
        register_file_action,
        register_track_action,
    )
except ImportError:
    from picard.ui.itemviews import (
        BaseAction,
        register_album_action,
        register_cluster_action,
        register_file_action,
        register_track_action,
    )

# ── Options pages ──────────────────────────────────────────────────────────────
try:
    from picard.extension_points.options_pages import register_options_page
except ImportError:
    from picard.ui.options import register_options_page
