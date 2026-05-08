PLUGIN_NAME = "Tag Filter & Joiner"
PLUGIN_AUTHOR = "rpmzine"
PLUGIN_DESCRIPTION = "Ignore selected tags and/or join multi-value tags with custom separators."
PLUGIN_VERSION = "0.9.5"
PLUGIN_API_VERSIONS = ["2.10", "2.11", "2.12", "2.13"]
PLUGIN_LICENSE = "MIT"
PLUGIN_LICENSE_URL = "https://opensource.org/licenses/MIT"

from picard import config, log
from picard.config import BoolOption, TextOption
from ._compat import (
    OptionsPage,
    QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QVBoxLayout, QWidget, Qt,
    register_options_page,
    register_track_metadata_processor,
)

# Standard tags to show in the UI - comprehensive MusicBrainz tag list, alphabetically sorted
STANDARD_TAGS = [
    "albumartist", "albumartistsort", "album", "albumsort", "arranger", "artist", "artists", "artistsort", 
    "asin", "barcode", "bpm", "catalognumber", "comment", "compilation", "composer", "composersort", 
    "conductor", "conductor_sort", "copyright", "date", "discnumber", "discsubtitle", "encodedby", 
    "engineer", "genre", "grouping", "isrc", "key", "label", "language", "lyricist", "lyricistsort", 
    "lyrics", "media", "mixer", "mood", "movement", "movementnumber", "movementsort", "movementtotal", 
    "musicbrainz_albumartistid", "musicbrainz_albumid", "musicbrainz_artistid", "musicbrainz_discid", 
    "musicbrainz_recordingid", "musicbrainz_releasegroupid", "musicbrainz_releasetrackid", 
    "musicbrainz_trackid", "musicbrainz_workid", "originaldate", "originalyear", "performer", 
    "performersort", "producer", "releasecountry", "releasestatus", "releasetype", "remixer", 
    "script", "subtitle", "title", "titlesort", "totaldiscs", "totaltracks", "tracknumber", 
    "website", "work", "worksort", "writer", "year"
]

# Define options for all tags
options = []
for tag in STANDARD_TAGS:
    options.extend([
        BoolOption("setting", f"tag_filter_ignore_{tag}", False),
        BoolOption("setting", f"tag_filter_join_{tag}", False),
        TextOption("setting", f"tag_filter_sep_{tag}", " / "),
    ])

class TagFilterOptionsPage(OptionsPage):
    NAME = "tag_filter_joiner"
    TITLE = "Tag Filter and Joiner" 
    PARENT = "plugins"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ignore_checkboxes = {}
        self.join_checkboxes = {}
        self.separators = {}
        
        # Create the UI directly (no external UI files)
        self._create_ui()

    def _create_ui(self):
        """Create the user interface"""
        main_layout = QVBoxLayout(self)
        
        # Description
        desc_label = QLabel("Configure which tags to ignore or join when they have multiple values.")
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # Content widget with grid layout
        content_widget = QWidget()
        grid = QGridLayout(content_widget)
        grid.setSpacing(5)
        
        # Headers with better styling
        header_style = "font-weight: bold; padding: 5px; background-color: #f0f0f0;"
        
        tag_header = QLabel("Tag")
        tag_header.setStyleSheet(header_style)
        tag_header.setMinimumWidth(200)
        grid.addWidget(tag_header, 0, 0)
        
        ignore_header = QLabel("Ignore")
        ignore_header.setStyleSheet(header_style)
        ignore_header.setMinimumWidth(80)
        ignore_header.setAlignment(Qt.AlignCenter)
        grid.addWidget(ignore_header, 0, 1)
        
        join_header = QLabel("Join Multi-values")
        join_header.setStyleSheet(header_style)
        join_header.setMinimumWidth(120)
        join_header.setAlignment(Qt.AlignCenter)
        grid.addWidget(join_header, 0, 2)
        
        separator_header = QLabel("Separator")
        separator_header.setStyleSheet(header_style)
        separator_header.setMinimumWidth(150)
        grid.addWidget(separator_header, 0, 3)
        
        # Add controls for each tag
        for row, tag in enumerate(STANDARD_TAGS, start=1):
            # Tag name
            tag_label = QLabel(tag)
            tag_label.setMinimumWidth(200)
            if row % 2 == 0:  # Alternating row colors
                tag_label.setStyleSheet("background-color: #f9f9f9; padding: 2px;")
            grid.addWidget(tag_label, row, 0)
            
            # Ignore checkbox
            cb_ignore = QCheckBox()
            cb_ignore.setMinimumWidth(80)
            self.ignore_checkboxes[tag] = cb_ignore
            if row % 2 == 0:
                cb_ignore.setStyleSheet("background-color: #f9f9f9;")
            grid.addWidget(cb_ignore, row, 1, Qt.AlignCenter)
            
            # Join checkbox  
            cb_join = QCheckBox()
            cb_join.setMinimumWidth(120)
            self.join_checkboxes[tag] = cb_join
            if row % 2 == 0:
                cb_join.setStyleSheet("background-color: #f9f9f9;")
            grid.addWidget(cb_join, row, 2, Qt.AlignCenter)
            
            # Separator input
            sep = QLineEdit(" / ")
            sep.setPlaceholderText("e.g. ' / ' or '; '")
            sep.setEnabled(False)
            sep.setMinimumWidth(150)
            self.separators[tag] = sep
            if row % 2 == 0:
                sep.setStyleSheet("background-color: #f9f9f9;")
            grid.addWidget(sep, row, 3)
            
            # Connect checkbox to enable/disable separator
            cb_join.stateChanged.connect(
                lambda state, separator=sep: separator.setEnabled(state == Qt.Checked)
            )
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def load(self):
        """Load settings from config"""
        log.debug("Tag Filter & Joiner: load() called")
        
        for tag in STANDARD_TAGS:
            ignore_key = f"tag_filter_ignore_{tag}"
            join_key = f"tag_filter_join_{tag}"
            sep_key = f"tag_filter_sep_{tag}"
            
            # Load values using the properly defined options
            ignore_value = config.setting[ignore_key]
            join_value = config.setting[join_key]
            sep_value = config.setting[sep_key]
            
            self.ignore_checkboxes[tag].setChecked(ignore_value)
            self.join_checkboxes[tag].setChecked(join_value)
            self.separators[tag].setText(sep_value)
            
            # Debug logging for loaded values
            if ignore_value or join_value:
                log.debug(f"Tag Filter & Joiner: Loading {tag} - ignore:{ignore_value}, join:{join_value}, sep:'{sep_value}'")
            
            self.separators[tag].setEnabled(join_value)

    def save(self):
        """Save settings to config"""
        log.debug("Tag Filter & Joiner: save() called")
        for tag in STANDARD_TAGS:
            ignore_key = f"tag_filter_ignore_{tag}"
            join_key = f"tag_filter_join_{tag}"
            sep_key = f"tag_filter_sep_{tag}"
            
            ignore_val = self.ignore_checkboxes[tag].isChecked()
            join_val = self.join_checkboxes[tag].isChecked()
            sep_val = self.separators[tag].text()
            
            # Save using the properly defined options
            config.setting[ignore_key] = ignore_val
            config.setting[join_key] = join_val
            config.setting[sep_key] = sep_val
            
            if ignore_val or join_val:  # Only log if there's something to save
                log.debug(f"Tag Filter & Joiner: Saving {tag} - ignore:{ignore_val}, join:{join_val}, sep:'{sep_val}'")

def process_track_metadata(album, metadata, track, release):
    """Process track metadata according to plugin settings"""
    log.debug(f"Tag Filter & Joiner: process_track_metadata called with {len([album, metadata, track, release])} arguments")
    try:
        tags_to_process = list(metadata.keys())
        
        for tag in tags_to_process:
            # Check if tag should be ignored
            ignore_key = f"tag_filter_ignore_{tag}"
            if ignore_key in config.setting and config.setting[ignore_key]:
                if tag in metadata:
                    del metadata[tag]
                    log.debug(f"Tag Filter & Joiner: Removed tag '{tag}'")
                continue

            # Check if tag should be joined
            join_key = f"tag_filter_join_{tag}"
            if not (join_key in config.setting and config.setting[join_key]):
                continue

            # Join multi-value tags
            if tag in metadata:
                try:
                    values = metadata.getall(tag)
                except AttributeError:
                    raw_value = metadata[tag]
                    values = raw_value if isinstance(raw_value, list) else [raw_value]

                if values and len(values) > 1:
                    sep_key = f"tag_filter_sep_{tag}"
                    separator = config.setting[sep_key] if sep_key in config.setting else " / "
                    
                    filtered_values = [str(v).strip() for v in values if v is not None and str(v).strip()]
                    
                    if len(filtered_values) > 1:
                        joined_value = separator.join(filtered_values)
                        metadata[tag] = joined_value
                        log.debug(f"Tag Filter & Joiner: Joined tag '{tag}': {joined_value}")

    except Exception as e:
        log.error(f"Tag Filter & Joiner: Error processing metadata - {e}")

def enable(api):
    register_options_page(TagFilterOptionsPage)
    register_track_metadata_processor(process_track_metadata)
    log.info("Tag Filter & Joiner: Plugin loaded")