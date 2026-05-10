PLUGIN_NAME = "Multidisc Tagger"
PLUGIN_AUTHOR = "rpmzine"
PLUGIN_DESCRIPTION = "When multidisc releases are detected, this plugin tags them appropriately, using Work and Movement similar to Classical Music tagging. Also allows manual multidisc creation via context menu."
PLUGIN_VERSION = "2.6.0"
PLUGIN_API_VERSIONS = ["2.10", "2.11", "2.12", "2.13"]

from picard import log
from picard.metadata import (
    register_album_metadata_processor,
    register_track_metadata_processor,
)
from picard.ui.itemviews import BaseAction, register_album_action, register_cluster_action
from PyQt5 import QtWidgets, QtCore

# Storage for manual disc subtitles per album
_manual_disc_subtitles = {}

# Storage for open dialogs to prevent duplicates
_open_dialogs = {}

class DiscSubtitleDialog(QtWidgets.QDialog):
    """Dialog for entering disc subtitles for multidisc releases"""
    
    def __init__(self, disc_total, album_title="", parent=None):
        super().__init__(parent)
        self.disc_total = disc_total
        self.disc_subtitles = {}
        self.setWindowTitle("Create Multidisc Subtitles")
        self.setMinimumSize(500, 300)
        self.create_ui(album_title)
    
    def create_ui(self, album_title):
        layout = QtWidgets.QVBoxLayout(self)
        
        # Header
        if album_title:
            title_label = QtWidgets.QLabel(f"Album: {album_title}")
            title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
            layout.addWidget(title_label)
        
        description = QtWidgets.QLabel(
            f"Enter subtitles for each disc (Total: {self.disc_total} discs)\n"
            "Leave empty if you don't want a subtitle for that disc."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Scroll area for disc inputs
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        
        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        
        self.disc_inputs = {}
        for disc_num in range(1, self.disc_total + 1):
            disc_group = QtWidgets.QGroupBox(f"Disc {disc_num}")
            disc_layout = QtWidgets.QVBoxLayout(disc_group)
            
            subtitle_input = QtWidgets.QLineEdit()
            subtitle_input.setPlaceholderText(f"e.g., 'The Hits', 'Rarities', 'Live Tracks'...")
            subtitle_input.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            disc_layout.addWidget(subtitle_input)
            
            self.disc_inputs[disc_num] = subtitle_input
            scroll_layout.addWidget(disc_group)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Buttons - use vertical layout to prevent wrapping issues
        button_section = QtWidgets.QVBoxLayout()
        
        # Preset buttons row
        preset_layout = QtWidgets.QHBoxLayout()
        presets_label = QtWidgets.QLabel("Quick Presets:")
        preset_layout.addWidget(presets_label)
        
        cd_preset_btn = QtWidgets.QPushButton("CD 1, CD 2...")
        cd_preset_btn.clicked.connect(self.apply_cd_preset)
        preset_layout.addWidget(cd_preset_btn)
        
        disc_preset_btn = QtWidgets.QPushButton("Disc 1, Disc 2...")
        disc_preset_btn.clicked.connect(self.apply_disc_preset)
        preset_layout.addWidget(disc_preset_btn)
        
        preset_layout.addStretch()
        button_section.addLayout(preset_layout)
        
        # Dialog buttons row
        dialog_button_layout = QtWidgets.QHBoxLayout()
        dialog_buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)
        
        dialog_button_layout.addStretch()  # Push dialog buttons to the right
        dialog_button_layout.addWidget(dialog_buttons)
        button_section.addLayout(dialog_button_layout)
        
        layout.addLayout(button_section)
    
    def apply_cd_preset(self):
        """Apply CD 1, CD 2... preset"""
        for disc_num, input_field in self.disc_inputs.items():
            input_field.setText(f"CD {disc_num}")
    
    def apply_disc_preset(self):
        """Apply Disc 1, Disc 2... preset"""
        for disc_num, input_field in self.disc_inputs.items():
            input_field.setText(f"Disc {disc_num}")
    
    def get_disc_subtitles(self):
        """Get the entered disc subtitles"""
        subtitles = {}
        for disc_num, input_field in self.disc_inputs.items():
            subtitle = input_field.text().strip()
            if subtitle:  # Only store non-empty subtitles
                subtitles[disc_num] = subtitle
        return subtitles

class MakeMultidiscAction(BaseAction):
    NAME = "Make it a Multidisc"
    
    def __init__(self):
        super().__init__()
        log.info("Multidisc Tagger: MakeMultidiscAction initialized")
    
    def callback(self, objs):
        log.info(f"Multidisc Tagger: Context menu action callback called with {len(objs)} objects")
        try:
            # Process each selected album or cluster
            for obj in objs:
                # Handle different object types
                if hasattr(obj, 'tracks') and hasattr(obj, 'metadata'):
                    # This is an Album object
                    self._process_album(obj)
                elif hasattr(obj, 'files'):
                    # This is a Cluster object
                    self._process_cluster(obj)
                else:
                    log.debug(f"Multidisc Tagger: Skipping unsupported object type: {type(obj)}")
                    continue
        
        except Exception as e:
            log.error(f"Multidisc Tagger: Error in Make Multidisc action: {e}")
            QtWidgets.QMessageBox.critical(
                None, "Error", 
                f"An error occurred while creating multidisc tags:\n{str(e)}"
            )
    
    def _process_album(self, album):
        """Process an album object"""
        # Check if dialog is already open for this album
        album_id = id(album)
        if album_id in _open_dialogs:
            existing_dialog = _open_dialogs[album_id]
            if existing_dialog and existing_dialog.isVisible():
                existing_dialog.raise_()  # Bring existing dialog to front
                existing_dialog.activateWindow()
                return
        
        # Check if it's a multidisc release (disc total > 1)
        disc_total = self._get_disc_total_from_album(album)
        if disc_total <= 1:
            disc_word = "disc" if disc_total == 1 else "discs"
            QtWidgets.QMessageBox.information(
                None, "Not Multidisc", 
                f"This album has only {disc_total} {disc_word}. "
                "Multidisc tagging is only useful for albums with multiple discs."
            )
            return
        
        # Get album title for the dialog
        album_title = album.metadata.get("album", "Unknown Album")
        
        # Show disc subtitle dialog (non-modal)
        dialog = DiscSubtitleDialog(disc_total, album_title)
        dialog.setModal(False)  # Allow navigation while dialog is open
        
        # Store reference to prevent garbage collection and duplicates
        dialog.album_ref = album
        _open_dialogs[album_id] = dialog
        dialog.finished.connect(lambda result: self._handle_album_dialog_result(dialog, result))
        dialog.show()
    
    def _handle_album_dialog_result(self, dialog, result):
        """Handle the result when album dialog is closed"""
        album = dialog.album_ref
        
        if result == QtWidgets.QDialog.Accepted:
            disc_subtitles = dialog.get_disc_subtitles()
            
            if disc_subtitles:
                # Store the disc subtitles for this album
                album_id = id(album)
                _manual_disc_subtitles[album_id] = disc_subtitles
                
                # Apply the subtitles to all tracks
                self._apply_disc_subtitles_to_album(album, disc_subtitles)
                
                log.info(f"Multidisc Tagger: Applied manual subtitles to {len(disc_subtitles)} discs")
                
                # Show success message
                QtWidgets.QMessageBox.information(
                    None, "Multidisc Created", 
                    f"Successfully applied disc subtitles to {len(disc_subtitles)} discs.\n"
                    "Work and Movement tags have been updated."
                )
            else:
                QtWidgets.QMessageBox.information(
                    None, "No Subtitles", 
                    "No disc subtitles were entered. No changes made."
                )
        
        # Clean up references
        album_id = id(album)
        if album_id in _open_dialogs:
            del _open_dialogs[album_id]
        dialog.album_ref = None
    
    def _process_cluster(self, cluster):
        """Process a cluster object"""
        # Check if dialog is already open for this cluster
        cluster_id = id(cluster)
        if cluster_id in _open_dialogs:
            existing_dialog = _open_dialogs[cluster_id]
            if existing_dialog and existing_dialog.isVisible():
                existing_dialog.raise_()  # Bring existing dialog to front
                existing_dialog.activateWindow()
                return
        
        # For clusters, we need to analyze the files to determine disc structure
        disc_total = self._get_disc_total_from_cluster(cluster)
        if disc_total <= 1:
            disc_word = "disc" if disc_total == 1 else "discs"
            QtWidgets.QMessageBox.information(
                None, "Not Multidisc", 
                f"This cluster has only {disc_total} {disc_word}. "
                "Multidisc tagging is only useful for clusters with multiple discs."
            )
            return
        
        # Try to get cluster name or use a generic title
        cluster_title = getattr(cluster, 'title', 'Unknown Release')
        
        # Show disc subtitle dialog (non-modal)
        dialog = DiscSubtitleDialog(disc_total, cluster_title)
        dialog.setModal(False)  # Allow navigation while dialog is open
        
        # Store reference to prevent garbage collection and duplicates
        dialog.cluster_ref = cluster
        _open_dialogs[cluster_id] = dialog
        dialog.finished.connect(lambda result: self._handle_cluster_dialog_result(dialog, result))
        dialog.show()
    
    def _handle_cluster_dialog_result(self, dialog, result):
        """Handle the result when cluster dialog is closed"""
        cluster = dialog.cluster_ref
        
        if result == QtWidgets.QDialog.Accepted:
            disc_subtitles = dialog.get_disc_subtitles()
            
            if disc_subtitles:
                # Apply the subtitles to all files in the cluster
                self._apply_disc_subtitles_to_cluster(cluster, disc_subtitles)
                
                log.info(f"Multidisc Tagger: Applied manual subtitles to {len(disc_subtitles)} discs in cluster")
                
                # Show success message
                QtWidgets.QMessageBox.information(
                    None, "Multidisc Created", 
                    f"Successfully applied disc subtitles to {len(disc_subtitles)} discs.\n"
                    "Work and Movement tags have been updated."
                )
            else:
                QtWidgets.QMessageBox.information(
                    None, "No Subtitles", 
                    "No disc subtitles were entered. No changes made."
                )
        
        # Clean up references
        cluster_id = id(cluster)
        if cluster_id in _open_dialogs:
            del _open_dialogs[cluster_id]
        dialog.cluster_ref = None
    
    def _get_disc_total_from_album(self, album):
        """Get the total number of discs in the album"""
        max_disc = 0
        for track in album.tracks:
            if hasattr(track, 'metadata'):
                try:
                    disc_num_str = track.metadata.get("discnumber")
                    if disc_num_str:
                        disc_num = int(disc_num_str)
                        max_disc = max(max_disc, disc_num)
                except (ValueError, TypeError):
                    pass
        
        # Also check disc total metadata
        try:
            disc_total = int(album.metadata.get("totaldiscs", max_disc))
            return max(max_disc, disc_total)
        except (ValueError, TypeError):
            return max_disc or 1
    
    def _get_disc_total_from_cluster(self, cluster):
        """Get the total number of discs in the cluster"""
        max_disc = 0
        for file_obj in getattr(cluster, 'files', []):
            if hasattr(file_obj, 'metadata'):
                try:
                    disc_num_str = file_obj.metadata.get("discnumber")
                    if disc_num_str:
                        disc_num = int(disc_num_str)
                        max_disc = max(max_disc, disc_num)
                except (ValueError, TypeError):
                    pass
        
        # Also check disc total metadata from the first file
        for file_obj in getattr(cluster, 'files', []):
            if hasattr(file_obj, 'metadata'):
                try:
                    disc_total = int(file_obj.metadata.get("totaldiscs", max_disc))
                    return max(max_disc, disc_total)
                except (ValueError, TypeError):
                    continue
        
        return max_disc or 1
    
    def _apply_disc_subtitles_to_album(self, album, disc_subtitles):
        """Apply disc subtitles to all tracks in the album"""
        total_discs = max(disc_subtitles.keys()) if disc_subtitles else 1
        
        for track in album.tracks:
            if hasattr(track, 'metadata'):
                try:
                    disc_num = int(track.metadata.get("discnumber", "1"))
                    
                    # Always set totaldiscs to ensure proper multidisc identification
                    track.metadata["totaldiscs"] = str(total_discs)
                    
                    if disc_num in disc_subtitles:
                        # Set the manual disc subtitle
                        track.metadata["discsubtitle"] = disc_subtitles[disc_num]
                        
                        # Apply multidisc tagging
                        self._apply_multidisc_tags(track.metadata)
                        
                        # Update the track to refresh UI
                        if hasattr(track, 'update'):
                            track.update()
                
                except (ValueError, TypeError):
                    continue
    
    def _apply_disc_subtitles_to_cluster(self, cluster, disc_subtitles):
        """Apply disc subtitles to all files in the cluster"""
        total_discs = max(disc_subtitles.keys()) if disc_subtitles else 1
        
        for file_obj in getattr(cluster, 'files', []):
            if hasattr(file_obj, 'metadata'):
                try:
                    disc_num = int(file_obj.metadata.get("discnumber", "1"))
                    
                    # Always set totaldiscs to ensure proper multidisc identification
                    file_obj.metadata["totaldiscs"] = str(total_discs)
                    
                    if disc_num in disc_subtitles:
                        # Set the manual disc subtitle
                        file_obj.metadata["discsubtitle"] = disc_subtitles[disc_num]
                        
                        # Apply multidisc tagging
                        self._apply_multidisc_tags(file_obj.metadata)
                        
                        # Update the file to refresh UI
                        if hasattr(file_obj, 'update'):
                            file_obj.update()
                
                except (ValueError, TypeError):
                    continue
    
    def _apply_multidisc_tags(self, metadata):
        """Apply work/movement tagging from disc subtitle"""
        discsubtitle = metadata.get("discsubtitle")
        if discsubtitle:
            metadata["work"] = discsubtitle
            metadata["showmovement"] = "1"
            title = metadata.get("title")
            if title:
                metadata["movement"] = title

def set_multidisc_tags_album(tagger, metadata, release):
    # Album processor only needed for discsubtitle/number, handled elsewhere if needed
    pass

def set_multidisc_tags_track(tagger, metadata, track, release):
    """Automatic multidisc tagging from disc subtitle.

    Picard translates work/movement/showmovement to the correct
    format-native tags when writing (WORK for Vorbis, ©wrk for M4A).
    """
    discsubtitle = metadata.get("discsubtitle")
    if not discsubtitle:
        return

    metadata["work"] = discsubtitle
    metadata["showmovement"] = "1"
    title = metadata.get("title")
    if title:
        metadata["movement"] = title

# Register processors and actions
register_album_metadata_processor(set_multidisc_tags_album)
register_track_metadata_processor(set_multidisc_tags_track)
log.info("Multidisc Tagger: Plugin loaded, metadata processors registered")

# Register the context menu action
try:
    _multidisc_action = MakeMultidiscAction()
    register_album_action(_multidisc_action)      # Post-processing (albums)
    register_cluster_action(_multidisc_action)    # Pre-processing (clusters)
    log.info("Multidisc Tagger: Context menu action registered for albums and clusters")
except Exception as e:
    log.error(f"Multidisc Tagger: Failed to register context menu action: {e}")