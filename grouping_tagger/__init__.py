# -*- coding: utf-8 -*-
PLUGIN_NAME = "Grouping Tagger"
PLUGIN_AUTHOR = "rpmzine"
PLUGIN_DESCRIPTION = "Tag GROUPING field with customizable source and format tags via context menu. Uses JSON templates with detection variables (Vinyl/CD/Digital source, format, quality tier, channels, bootleg, remaster). Includes configurable fixed tags and auto-detection matrix."
PLUGIN_VERSION = "3.1.2"
PLUGIN_API_VERSIONS = ["2.10", "2.11", "2.12", "2.13"]
PLUGIN_LICENSE = "MIT"
PLUGIN_LICENSE_URL = "https://opensource.org/licenses/MIT"

from picard import config, log
from picard.config import BoolOption, TextOption, ListOption
from picard.ui.itemviews import BaseAction, register_album_action, register_track_action, register_file_action, register_cluster_action
from picard.ui.options import OptionsPage, register_options_page
from PyQt5 import QtWidgets, QtCore
import json

# Configuration options - Detection enables
BoolOption("setting", "grouping_tagger_detect_vinyl", True)
BoolOption("setting", "grouping_tagger_detect_cd", False)
BoolOption("setting", "grouping_tagger_detect_cassette", False)
BoolOption("setting", "grouping_tagger_detect_bootleg", True)
BoolOption("setting", "grouping_tagger_detect_digital", True)
BoolOption("setting", "grouping_tagger_detect_remaster", False)
BoolOption("setting", "grouping_tagger_detect_format", True)
BoolOption("setting", "grouping_tagger_detect_quality", False)

# Configuration options - Custom tag text for each detection
TextOption("setting", "grouping_tagger_vinyl_tag", "Vinyl")
TextOption("setting", "grouping_tagger_cd_tag", "CD")
TextOption("setting", "grouping_tagger_cassette_tag", "Cassette")
TextOption("setting", "grouping_tagger_bootleg_tag", "Bootleg")
TextOption("setting", "grouping_tagger_digital_tag", "Digital")
TextOption("setting", "grouping_tagger_remaster_tag", "Remastered")

# Configuration options - Behavior
BoolOption("setting", "grouping_tagger_append_mode", False)
TextOption("setting", "grouping_tagger_separator", ", ")
TextOption("setting", "grouping_tagger_manual_tags", "")

# Configuration options - Templates
TextOption("setting", "grouping_tagger_templates", "[]")  # JSON list of templates

# Configuration JSON file location (v3.1.0: now includes templates + fixed tags)
import os
# Store in a separate preferences/json folder to preserve config across plugin updates
JSON_PREFERENCES_DIR = os.path.expanduser("~/Library/Preferences/MusicBrainz/Picard/json")
CONFIG_JSON_PATH = os.path.join(JSON_PREFERENCES_DIR, "grouping_tagger_config.json")
# Legacy path for migration
LEGACY_TEMPLATES_JSON_PATH = os.path.join(JSON_PREFERENCES_DIR, "grouping_tagger_templates.json")

def load_templates_from_sources():
    """
    Load templates with priority: JSON file > Picard settings > empty list

    Returns:
        list: List of template dictionaries
    """
    templates = None

    # Priority 1: Try loading from new config JSON file (v3.1.0+)
    if os.path.exists(CONFIG_JSON_PATH):
        try:
            import codecs
            with codecs.open(CONFIG_JSON_PATH, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # New format: {"templates": [...], "fixed_tags": {...}}
            if isinstance(config_data, dict) and "templates" in config_data:
                templates = config_data["templates"]
                if isinstance(templates, list):
                    log.info(f"Grouping Tagger: Loaded {len(templates)} templates from config JSON")
                else:
                    templates = None
            # Legacy format: just array of templates
            elif isinstance(config_data, list):
                templates = config_data
                log.info(f"Grouping Tagger: Loaded {len(templates)} templates from legacy JSON format")
            else:
                templates = None
        except Exception as e:
            templates = None
            log.warning(f"Grouping Tagger: Failed to load config JSON: {e}, falling back")

    # Priority 1b: Try loading from legacy templates JSON file
    if templates is None and os.path.exists(LEGACY_TEMPLATES_JSON_PATH):
        try:
            import codecs
            with codecs.open(LEGACY_TEMPLATES_JSON_PATH, 'r', encoding='utf-8') as f:
                templates = json.load(f)
            if isinstance(templates, list):
                log.info(f"Grouping Tagger: Loaded {len(templates)} templates from legacy JSON file")
        except Exception as e:
            templates = None
            log.warning(f"Grouping Tagger: Failed to load legacy JSON: {e}")

    # Priority 2: Try loading from Picard settings
    if templates is None:
        try:
            templates_json = config.setting["grouping_tagger_templates"] if "grouping_tagger_templates" in config.setting else "[]"
            if templates_json:
                templates = json.loads(templates_json)
                if isinstance(templates, list) and len(templates) > 0:
                    log.info(f"Grouping Tagger: Loaded {len(templates)} templates from Picard settings")
                else:
                    templates = []
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            templates = []
            log.warning(f"Grouping Tagger: Failed to parse templates from settings: {e}")

    # Priority 3: Use empty list
    if templates is None:
        templates = []
        log.info("Grouping Tagger: No templates found, using empty list")

    return templates

def save_templates_to_json(templates):
    """
    Save templates to the JSON file location (legacy function for backward compatibility)

    Args:
        templates (list): List of template dictionaries

    Returns:
        bool: True if successful, False otherwise
    """
    # Now saves in the new combined format
    return save_config_to_json(templates=templates)

def save_config_to_json(templates=None, fixed_tags=None):
    """
    Save configuration (templates and/or fixed tags) to JSON file

    Args:
        templates (list): List of template dictionaries (optional)
        fixed_tags (dict): Dictionary of fixed tags (optional)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        json_dir = os.path.dirname(CONFIG_JSON_PATH)
        if not os.path.exists(json_dir):
            os.makedirs(json_dir)

        # Load existing config if it exists
        config_data = {}
        if os.path.exists(CONFIG_JSON_PATH):
            try:
                import codecs
                with codecs.open(CONFIG_JSON_PATH, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    if not isinstance(config_data, dict):
                        config_data = {}
            except Exception:
                config_data = {}

        # Update with provided data
        if templates is not None:
            config_data["templates"] = templates
        if fixed_tags is not None:
            config_data["fixed_tags"] = fixed_tags

        # Write JSON file
        import codecs
        with codecs.open(CONFIG_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        log.info(f"Grouping Tagger: Saved config to JSON file: {CONFIG_JSON_PATH}")
        return True
    except Exception as e:
        log.error(f"Grouping Tagger: Failed to save config to JSON file: {e}")
        return False

# Predefined tag options for user selection
TAG_OPTIONS = {
    "Vinyl": ["Vinyl", "LP", "Vinyl Rip", "Vinyl Source", "Record"],
    "CD": ["CD", "Compact Disc", "CD Rip"],
    "Cassette": ["Cassette", "Tape", "Cassette Rip"],
    "Bootleg": ["Bootleg", "Unofficial", "Pirate", "Boot", "Unofficial Release"],
    "Digital": ["Digital", "Digital Media", "Download", "Web", "Streaming", "Digital Files"],
    "Remaster": ["Remastered", "Remaster", "Digitally Remastered", "Reissue"],
}

# Default fixed tags for right-click menu
DEFAULT_FIXED_TAGS = {
    "Vinyl": "Vinyl",
    "CD": "CD",
    "Digital": "Digital",
    "Bootleg": "Bootleg",
    "MP3": "MP3",
    "FLAC": "FLAC",
    "WAV": "WAV",
    "APE": "APE",
    "AAC": "AAC",
    "Lossy": "Lossy",
    "Lossless": "Lossless",
    "Hi-Def": "Hi-Def",
    "Remastered": "Remastered",
    "Limited Edition": "Limited Edition",
    "Japanese Import": "Japanese Import",
    "Deluxe Edition": "Deluxe Edition",
}

# Config option for custom fixed tags
TextOption("setting", "grouping_tagger_custom_fixed_tags", json.dumps({}))

def get_all_fixed_tags():
    """Get merged fixed tags (defaults + custom)"""
    try:
        custom_tags = json.loads(config.setting["grouping_tagger_custom_fixed_tags"])
    except (json.JSONDecodeError, KeyError, TypeError):
        custom_tags = {}

    # Merge with defaults
    all_tags = DEFAULT_FIXED_TAGS.copy()
    all_tags.update(custom_tags)
    return all_tags

# Template variables
TEMPLATE_VARIABLES = {
    "{SOURCE}": "Detected source (Vinyl, CD, Cassette, Digital)",
    "{FORMAT}": "File format (MP3, FLAC, WAV, etc.)",
    "{QUALITY}": "Quality tier (Lossy, Lossless, Hi-Def)",
    "{CHANNELS}": "Audio channels (2.0, 5.1, 7.1, etc.)",
    "{BOOTLEG}": "Bootleg tag if detected",
    "{REMASTER}": "Remaster tag if detected",
    "{MANUAL}": "Manual/additional tags",
}

# Default templates
DEFAULT_TEMPLATES = [
    {"name": "Source + Format", "template": "{SOURCE} | {FORMAT}", "divider": " | "},
    {"name": "Source + Quality", "template": "{SOURCE} - {QUALITY}", "divider": " - "},
    {"name": "Full Info", "template": "{SOURCE}, {FORMAT}, {QUALITY}", "divider": ", "},
    {"name": "Simple Source", "template": "{SOURCE}", "divider": ", "},
]

# Detection functions
def _get_metadata_value(metadata, key, default=""):
    """Get metadata value safely"""
    try:
        value = metadata.get(key)
        if value is None:
            return default
        return str(value).strip() if isinstance(value, (str, int, float)) else default
    except (AttributeError, TypeError):
        return default

def _detect_vinyl(metadata):
    """Detect if release is from Vinyl source"""
    media = _get_metadata_value(metadata, "media").lower()
    return "vinyl" in media

def _detect_cd(metadata):
    """Detect if release is from CD source"""
    media = _get_metadata_value(metadata, "media").lower()
    return "cd" in media and "sacd" not in media

def _detect_cassette(metadata):
    """Detect if release is from Cassette source"""
    media = _get_metadata_value(metadata, "media").lower()
    return "cassette" in media or "tape" in media

def _detect_bootleg(metadata):
    """Detect if release is a bootleg"""
    # Check release status
    release_status = _get_metadata_value(metadata, "releasestatus").lower()
    if "bootleg" in release_status:
        return True

    # Check album and comment fields for bootleg keywords
    album = _get_metadata_value(metadata, "album").lower()
    comment = _get_metadata_value(metadata, "comment").lower()
    search_text = f"{album} {comment}"

    bootleg_keywords = ["bootleg", "unofficial", "pirate"]
    return any(keyword in search_text for keyword in bootleg_keywords)

def _detect_digital(metadata):
    """Detect if release is from Digital source"""
    media = _get_metadata_value(metadata, "media").lower()

    # Check for digital media indicators
    digital_indicators = ["digital", "download", "web", "streaming"]
    if any(indicator in media for indicator in digital_indicators):
        return True

    # Also check if media is empty but we have a digital format
    if not media:
        file_format = _get_metadata_value(metadata, "~format").lower()
        digital_formats = ["flac", "mp3", "aac", "ogg", "opus", "wav", "ape", "wv", "m4a"]
        if any(fmt in file_format for fmt in digital_formats):
            return True

    return False

def _detect_remaster(metadata):
    """Detect if release is a remaster"""
    album = _get_metadata_value(metadata, "album").lower()
    comment = _get_metadata_value(metadata, "comment").lower()
    version = _get_metadata_value(metadata, "version").lower()

    search_text = f"{album} {comment} {version}"

    remaster_keywords = ["remaster", "remastered", "digitally remastered", "reissue", "re-issue"]
    return any(keyword in search_text for keyword in remaster_keywords)

def _detect_format(metadata):
    """Detect the file format (e.g., MP3, FLAC, WAV)"""
    file_format = _get_metadata_value(metadata, "~format").upper()

    if file_format:
        # Map common format names to short codes
        format_map = {
            "MPEG-1 LAYER 3": "MP3",
            "MPEG-1 AUDIO": "MP3",
            "MPEG-1 LAYER 2": "MP2",
            "WINDOWS MEDIA AUDIO": "WMA",
            "FREE LOSSLESS AUDIO CODEC": "FLAC",
            "APPLE LOSSLESS": "ALAC",
            "ADVANCED AUDIO CODING": "AAC",
            "MONKEY'S AUDIO": "APE",
            "OGG VORBIS": "OGG",
            "VORBIS": "OGG",
            "WAVPACK": "WV",
            "TRUE AUDIO": "TTA",
        }

        # Check if format matches any known patterns
        for key, value in format_map.items():
            if key in file_format:
                return value

        # Return short formats as-is
        if len(file_format) <= 6:
            return file_format

        # Try to extract acronym for longer names
        words = file_format.split()
        if len(words) > 1:
            acronym = "".join(word[0] for word in words if word)
            if len(acronym) <= 6:
                return acronym

    return file_format if file_format else None


def _detect_channels(metadata):
    """Detect audio channels and format nicely"""
    channels = _get_metadata_value(metadata, "~channels")
    if not channels:
        return ""

    # Format common channel configurations
    channel_map = {
        "1": "1.0",
        "2": "2.0",
        "6": "5.1",
        "8": "7.1",
    }

    return channel_map.get(channels, f"{channels}ch")


def _apply_template(template_string, divider, metadata, manual_tags=""):
    """Apply template with variable substitution"""
    # Get all detected values
    source_tags = []

    if _detect_vinyl(metadata):
        source_tags.append(config.setting["grouping_tagger_vinyl_tag"])
    if _detect_cd(metadata):
        source_tags.append(config.setting["grouping_tagger_cd_tag"])
    if _detect_cassette(metadata):
        source_tags.append(config.setting["grouping_tagger_cassette_tag"])
    if _detect_digital(metadata):
        source_tags.append(config.setting["grouping_tagger_digital_tag"])

    source = divider.join(source_tags) if source_tags else ""

    file_format = _detect_format(metadata) or ""
    quality = _detect_quality(metadata) or ""
    channels = _detect_channels(metadata) or ""
    bootleg = config.setting["grouping_tagger_bootleg_tag"] if _detect_bootleg(metadata) else ""
    remaster = config.setting["grouping_tagger_remaster_tag"] if _detect_remaster(metadata) else ""

    # Build replacement dictionary
    replacements = {
        "{SOURCE}": source,
        "{FORMAT}": file_format,
        "{QUALITY}": quality,
        "{CHANNELS}": channels,
        "{BOOTLEG}": bootleg,
        "{REMASTER}": remaster,
        "{MANUAL}": manual_tags,
    }

    # Replace variables
    result = template_string
    for var, value in replacements.items():
        result = result.replace(var, value)

    # Clean up: remove empty parts and extra dividers
    parts = [p.strip() for p in result.split(divider)]
    parts = [p for p in parts if p]  # Remove empty strings

    return divider.join(parts) if parts else ""


def _detect_quality(metadata):
    """Detect audio quality tier (Lossy/Lossless/Hi-Def)"""
    file_format = _get_metadata_value(metadata, "~format").upper()

    # Get bit depth and sample rate for hi-def detection
    bits_per_sample = _get_metadata_value(metadata, "~bits_per_sample")
    sample_rate = _get_metadata_value(metadata, "~sample_rate")

    # Try to parse sample rate (might be in Hz or kHz)
    try:
        if sample_rate:
            sample_rate_value = int(sample_rate) if isinstance(sample_rate, (int, str)) else 0
    except (ValueError, TypeError):
        sample_rate_value = 0

    # Try to parse bit depth
    try:
        if bits_per_sample:
            bit_depth = int(bits_per_sample) if isinstance(bits_per_sample, (int, str)) else 0
    except (ValueError, TypeError):
        bit_depth = 0

    # Define lossy and lossless format patterns
    lossy_patterns = [
        "MP3", "MPEG-1 LAYER 3", "MPEG-1 AUDIO", "MPEG-1 LAYER 2", "MP2",
        "AAC", "ADVANCED AUDIO CODING", "M4A",
        "OGG", "VORBIS", "OGG VORBIS",
        "WMA", "WINDOWS MEDIA AUDIO",
        "OPUS",
        "AC3", "DOLBY DIGITAL",
    ]

    lossless_patterns = [
        "FLAC", "FREE LOSSLESS AUDIO CODEC",
        "ALAC", "APPLE LOSSLESS",
        "APE", "MONKEY'S AUDIO", "MONKEY",
        "WAV", "WAVE",
        "AIFF", "AIF",
        "WV", "WAVPACK",
        "TTA", "TRUE AUDIO",
    ]

    # Check if it's lossy
    for pattern in lossy_patterns:
        if pattern in file_format:
            return "Lossy"

    # Check if it's lossless
    for pattern in lossless_patterns:
        if pattern in file_format:
            # Determine if it's hi-def (24-bit or sample rate >= 88.2kHz)
            if bit_depth >= 24 or sample_rate_value >= 88200:
                return "Hi-Def"
            else:
                return "Lossless"

    return None


class TemplateEditorDialog(QtWidgets.QDialog):
    """Dialog for creating/editing templates"""

    def __init__(self, template_data=None, parent=None):
        super().__init__(parent)
        self.template_data = template_data or {}
        self.setWindowTitle("Edit Template" if template_data else "New Template")
        self.setMinimumSize(650, 550)
        self.create_ui()

    def create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Template name
        layout.addWidget(QtWidgets.QLabel("Template Name:"))
        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setText(self.template_data.get("name", ""))
        self.name_input.setPlaceholderText("e.g., Source + Format")
        layout.addWidget(self.name_input)

        # Template string
        layout.addWidget(QtWidgets.QLabel("Template Pattern (use | or - or , as separators):"))
        self.template_input = QtWidgets.QLineEdit()
        self.template_input.setText(self.template_data.get("template", ""))
        self.template_input.setPlaceholderText("e.g., {SOURCE} | {FORMAT} {QUALITY}")
        layout.addWidget(self.template_input)

        # Available variables with click-to-copy buttons
        variables_group = QtWidgets.QGroupBox("Available Variables (click to copy)")
        variables_outer_layout = QtWidgets.QVBoxLayout(variables_group)

        # Description
        desc_label = QtWidgets.QLabel(
            "<b>Click any variable below to copy it to clipboard, then paste into your template pattern.</b><br>"
            "Variables are automatically replaced with detected values when the template is applied."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 10px; margin-bottom: 8px;")
        variables_outer_layout.addWidget(desc_label)

        # Clickable variable buttons in grid
        button_layout = QtWidgets.QGridLayout()
        button_layout.setSpacing(6)

        self.variable_buttons = {}
        variables_list = [
            ("{SOURCE}", "Detected source (Vinyl, CD, Cassette, Digital)"),
            ("{FORMAT}", "File format (MP3, FLAC, WAV, etc.)"),
            ("{QUALITY}", "Quality tier (Lossy, Lossless, Hi-Def)"),
            ("{CHANNELS}", "Audio channels (2.0, 5.1, 7.1, etc.)"),
            ("{BOOTLEG}", "Bootleg tag if detected"),
            ("{REMASTER}", "Remaster tag if detected"),
            ("{MANUAL}", "Manual/additional tags"),
        ]

        row, col = 0, 0
        for var_name, var_desc in variables_list:
            btn = QtWidgets.QPushButton(var_name)
            btn.setToolTip(f"{var_desc}\nClick to copy to clipboard")
            btn.clicked.connect(lambda checked, v=var_name: self.copy_variable(v))
            btn.setStyleSheet("""
                QPushButton {
                    text-align: center;
                    padding: 8px 12px;
                    font-size: 11px;
                    font-family: monospace;
                    border-radius: 4px;
                    min-width: 100px;
                    font-weight: bold;
                }
            """)
            button_layout.addWidget(btn, row, col)
            self.variable_buttons[var_name] = btn

            col += 1
            if col > 2:
                col = 0
                row += 1

        variables_outer_layout.addLayout(button_layout)
        layout.addWidget(variables_group)

        # Preview
        preview_group = QtWidgets.QGroupBox("Preview Example")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)
        self.preview_label = QtWidgets.QTextEdit()
        self.preview_label.setReadOnly(True)
        self.preview_label.setMaximumHeight(100)
        # Use theme-aware colors for dark mode support
        self.preview_label.setStyleSheet("""
            QTextEdit {
                font-family: 'Courier New', monospace;
                padding: 8px;
            }
        """)
        preview_layout.addWidget(self.preview_label)
        layout.addWidget(preview_group)

        # Connect signals for live preview
        self.template_input.textChanged.connect(self.update_preview)

        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.update_preview()

    def copy_variable(self, var_name):
        """Copy variable to clipboard"""
        try:
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(var_name)

            # Show temporary tooltip
            btn = self.variable_buttons[var_name]
            QtWidgets.QToolTip.showText(
                btn.mapToGlobal(btn.rect().center()),
                f"Copied {var_name} to clipboard!",
                btn, btn.rect(), 1500
            )
        except Exception as e:
            log.error(f"Grouping Tagger: Error copying variable: {e}")

    def update_preview(self):
        """Update preview with comprehensive sample data using actual detection"""
        try:
            template = self.template_input.text()
            divider = ", "  # Use a standard divider for detection

            if not template:
                self.preview_label.setText("Enter a template pattern to see preview...")
                return

            # Create diverse sample metadata examples
            manual_tags = "Limited Edition"

            # Example 1: Vinyl rip (lossless stereo)
            vinyl_metadata = {
                "media": "Vinyl",
                "~format": "FLAC",
                "~bits_per_sample": "24",
                "~sample_rate": "96000",
                "~channels": "2",
                "releasestatus": "",
                "album": "",
                "comment": "",
                "version": ""
            }
            result1 = _apply_template(template, divider, vinyl_metadata, manual_tags)

            # Example 2: CD Bootleg
            cd_bootleg_metadata = {
                "media": "CD",
                "~format": "FLAC",
                "~bits_per_sample": "16",
                "~sample_rate": "44100",
                "~channels": "2",
                "releasestatus": "bootleg",
                "album": "",
                "comment": "audience recording",
                "version": ""
            }
            result2 = _apply_template(template, divider, cd_bootleg_metadata, "")

            # Example 3: Lossy web/MP3 file (stereo)
            mp3_metadata = {
                "media": "Digital Media",
                "~format": "MP3",
                "~bits_per_sample": "",
                "~sample_rate": "44100",
                "~channels": "2",
                "releasestatus": "",
                "album": "",
                "comment": "",
                "version": ""
            }
            result3 = _apply_template(template, divider, mp3_metadata, "")

            # Example 4: Digital multichannel/surround
            multichannel_metadata = {
                "media": "Digital Media",
                "~format": "FLAC",
                "~bits_per_sample": "24",
                "~sample_rate": "192000",
                "~channels": "6",
                "releasestatus": "",
                "album": "Abbey Road Remastered",
                "comment": "",
                "version": ""
            }
            result4 = _apply_template(template, divider, multichannel_metadata, "")

            # Build HTML preview with all examples
            preview_text = "<div style='line-height: 1.6;'>"
            preview_text += f"<b>1. Vinyl rip (FLAC 24/96 stereo):</b><br>"
            preview_text += f"&nbsp;&nbsp;→ <span style='color: #0066cc;'>{result1 if result1 else '(empty)'}</span><br><br>"

            preview_text += f"<b>2. CD Bootleg (FLAC 16/44 stereo):</b><br>"
            preview_text += f"&nbsp;&nbsp;→ <span style='color: #0066cc;'>{result2 if result2 else '(empty)'}</span><br><br>"

            preview_text += f"<b>3. Lossy web file (MP3 stereo):</b><br>"
            preview_text += f"&nbsp;&nbsp;→ <span style='color: #0066cc;'>{result3 if result3 else '(empty)'}</span><br><br>"

            preview_text += f"<b>4. Digital multichannel (FLAC 24/192 5.1):</b><br>"
            preview_text += f"&nbsp;&nbsp;→ <span style='color: #0066cc;'>{result4 if result4 else '(empty)'}</span>"
            preview_text += "</div>"

            self.preview_label.setHtml(preview_text)

        except Exception as e:
            self.preview_label.setText(f"Preview Error: {str(e)}")
            log.error(f"Grouping Tagger: Template preview error: {e}")

    def get_template_data(self):
        """Get the template data from inputs"""
        return {
            "name": self.name_input.text().strip(),
            "template": self.template_input.text().strip(),
            "divider": ", ",  # Use comma separator as standard
        }


class TagSelectionDialog(QtWidgets.QDialog):
    """Dialog for selecting tag text from predefined options"""

    def __init__(self, tag_type, current_tag, parent=None):
        super().__init__(parent)
        self.tag_type = tag_type
        self.current_tag = current_tag
        self.setWindowTitle(f"Select {tag_type} Tag")
        self.setMinimumSize(400, 300)
        self.create_ui()

    def create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(QtWidgets.QLabel(f"Select the tag text to use when {self.tag_type} is detected:"))

        self.tag_group = QtWidgets.QButtonGroup()

        # Add predefined options
        for option in TAG_OPTIONS.get(self.tag_type, []):
            radio = QtWidgets.QRadioButton(option)
            self.tag_group.addButton(radio)
            layout.addWidget(radio)

            if option == self.current_tag:
                radio.setChecked(True)

        # Add custom option
        layout.addWidget(QtWidgets.QLabel("Or enter custom tag:"))
        self.custom_input = QtWidgets.QLineEdit()
        self.custom_input.setPlaceholderText("Custom tag text...")
        layout.addWidget(self.custom_input)

        # If current tag is not in predefined options, set it as custom
        if self.current_tag not in TAG_OPTIONS.get(self.tag_type, []):
            self.custom_input.setText(self.current_tag)

        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_selected_tag(self):
        """Get the selected tag text"""
        custom = self.custom_input.text().strip()
        if custom:
            return custom

        checked_button = self.tag_group.checkedButton()
        if checked_button:
            return checked_button.text()

        return self.current_tag


class DetectionMatrixDialog(QtWidgets.QDialog):
    """Dialog for managing detection settings"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detection Matrix Configuration")
        self.setMinimumSize(700, 600)
        self.create_ui()
        self.load_settings()

    def create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Description
        desc = QtWidgets.QLabel(
            "Configure automatic detection rules. Enable/disable each rule and customize the tag text used."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("margin-bottom: 10px;")
        layout.addWidget(desc)

        # Detection Matrix
        detection_group = QtWidgets.QGroupBox("Detection Matrix (Enable any combination)")
        detection_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        detection_layout = QtWidgets.QVBoxLayout(detection_group)

        # Grid for checkboxes, tag display, and buttons
        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setColumnStretch(1, 1)

        # Headers
        header_enable = QtWidgets.QLabel("<b>Enable</b>")
        header_tag = QtWidgets.QLabel("<b>Tag Text</b>")
        header_button = QtWidgets.QLabel("<b>Change</b>")

        grid_layout.addWidget(header_enable, 0, 0)
        grid_layout.addWidget(header_tag, 0, 1)
        grid_layout.addWidget(header_button, 0, 2)

        row = 1

        # Vinyl detection
        self.vinyl_checkbox = QtWidgets.QCheckBox("Vinyl Source")
        self.vinyl_tag_label = QtWidgets.QLabel("")
        self.vinyl_tag_label.setStyleSheet("padding: 4px; border: 1px solid #ccc; border-radius: 3px; font-size: 10px;")
        self.vinyl_tag_button = QtWidgets.QPushButton("Change Tag...")
        self.vinyl_tag_button.clicked.connect(lambda: self.open_tag_dialog("Vinyl"))

        grid_layout.addWidget(self.vinyl_checkbox, row, 0)
        grid_layout.addWidget(self.vinyl_tag_label, row, 1)
        grid_layout.addWidget(self.vinyl_tag_button, row, 2)
        row += 1

        # CD detection
        self.cd_checkbox = QtWidgets.QCheckBox("CD Source")
        self.cd_tag_label = QtWidgets.QLabel("")
        self.cd_tag_label.setStyleSheet("padding: 4px; border: 1px solid #ccc; border-radius: 3px; font-size: 10px;")
        self.cd_tag_button = QtWidgets.QPushButton("Change Tag...")
        self.cd_tag_button.clicked.connect(lambda: self.open_tag_dialog("CD"))

        grid_layout.addWidget(self.cd_checkbox, row, 0)
        grid_layout.addWidget(self.cd_tag_label, row, 1)
        grid_layout.addWidget(self.cd_tag_button, row, 2)
        row += 1

        # Cassette detection
        self.cassette_checkbox = QtWidgets.QCheckBox("Cassette Source")
        self.cassette_tag_label = QtWidgets.QLabel("")
        self.cassette_tag_label.setStyleSheet("padding: 4px; border: 1px solid #ccc; border-radius: 3px; font-size: 10px;")
        self.cassette_tag_button = QtWidgets.QPushButton("Change Tag...")
        self.cassette_tag_button.clicked.connect(lambda: self.open_tag_dialog("Cassette"))

        grid_layout.addWidget(self.cassette_checkbox, row, 0)
        grid_layout.addWidget(self.cassette_tag_label, row, 1)
        grid_layout.addWidget(self.cassette_tag_button, row, 2)
        row += 1

        # Digital detection
        self.digital_checkbox = QtWidgets.QCheckBox("Digital Source")
        self.digital_tag_label = QtWidgets.QLabel("")
        self.digital_tag_label.setStyleSheet("padding: 4px; border: 1px solid #ccc; border-radius: 3px; font-size: 10px;")
        self.digital_tag_button = QtWidgets.QPushButton("Change Tag...")
        self.digital_tag_button.clicked.connect(lambda: self.open_tag_dialog("Digital"))

        grid_layout.addWidget(self.digital_checkbox, row, 0)
        grid_layout.addWidget(self.digital_tag_label, row, 1)
        grid_layout.addWidget(self.digital_tag_button, row, 2)
        row += 1

        # Bootleg detection
        self.bootleg_checkbox = QtWidgets.QCheckBox("Bootleg Release")
        self.bootleg_tag_label = QtWidgets.QLabel("")
        self.bootleg_tag_label.setStyleSheet("padding: 4px; border: 1px solid #ccc; border-radius: 3px; font-size: 10px;")
        self.bootleg_tag_button = QtWidgets.QPushButton("Change Tag...")
        self.bootleg_tag_button.clicked.connect(lambda: self.open_tag_dialog("Bootleg"))

        grid_layout.addWidget(self.bootleg_checkbox, row, 0)
        grid_layout.addWidget(self.bootleg_tag_label, row, 1)
        grid_layout.addWidget(self.bootleg_tag_button, row, 2)
        row += 1

        # Remaster detection
        self.remaster_checkbox = QtWidgets.QCheckBox("Remastered")
        self.remaster_tag_label = QtWidgets.QLabel("")
        self.remaster_tag_label.setStyleSheet("padding: 4px; border: 1px solid #ccc; border-radius: 3px; font-size: 10px;")
        self.remaster_tag_button = QtWidgets.QPushButton("Change Tag...")
        self.remaster_tag_button.clicked.connect(lambda: self.open_tag_dialog("Remaster"))

        grid_layout.addWidget(self.remaster_checkbox, row, 0)
        grid_layout.addWidget(self.remaster_tag_label, row, 1)
        grid_layout.addWidget(self.remaster_tag_button, row, 2)
        row += 1

        # Format detection
        self.format_checkbox = QtWidgets.QCheckBox("File Format")
        format_label = QtWidgets.QLabel("MP3, FLAC, WAV, APE, etc. - detected automatically")
        format_label.setStyleSheet("padding: 4px; font-size: 10px; font-style: italic;")

        grid_layout.addWidget(self.format_checkbox, row, 0)
        grid_layout.addWidget(format_label, row, 1, 1, 2)
        row += 1

        # Quality tier detection
        self.quality_checkbox = QtWidgets.QCheckBox("Quality Tier")
        quality_label = QtWidgets.QLabel("Lossy/Lossless/Hi-Def - detected automatically")
        quality_label.setStyleSheet("padding: 4px; font-size: 10px; font-style: italic;")

        grid_layout.addWidget(self.quality_checkbox, row, 0)
        grid_layout.addWidget(quality_label, row, 1, 1, 2)

        detection_layout.addLayout(grid_layout)
        layout.addWidget(detection_group)

        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def open_tag_dialog(self, tag_type):
        """Open tag selection dialog"""
        try:
            setting_key = f"grouping_tagger_{tag_type.lower()}_tag"

            # Safely get current tag from label or config
            label = getattr(self, f"{tag_type.lower()}_tag_label", None)
            if label and label.text():
                current_tag = label.text()
            else:
                current_tag = config.setting[setting_key] if setting_key in config.setting else tag_type

            dialog = TagSelectionDialog(tag_type, current_tag, self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                new_tag = dialog.get_selected_tag()

                # Update label
                if label:
                    label.setText(new_tag)

        except Exception as e:
            log.error(f"Grouping Tagger: Error opening tag dialog for {tag_type}: {e}")

    def load_settings(self):
        """Load settings from config"""
        try:
            self.vinyl_checkbox.setChecked(config.setting["grouping_tagger_detect_vinyl"])
            self.cd_checkbox.setChecked(config.setting["grouping_tagger_detect_cd"])
            self.cassette_checkbox.setChecked(config.setting["grouping_tagger_detect_cassette"])
            self.digital_checkbox.setChecked(config.setting["grouping_tagger_detect_digital"])
            self.bootleg_checkbox.setChecked(config.setting["grouping_tagger_detect_bootleg"])
            self.remaster_checkbox.setChecked(config.setting["grouping_tagger_detect_remaster"])
            self.format_checkbox.setChecked(config.setting["grouping_tagger_detect_format"])
            self.quality_checkbox.setChecked(config.setting["grouping_tagger_detect_quality"])

            # Load custom tags
            self.vinyl_tag_label.setText(config.setting["grouping_tagger_vinyl_tag"])
            self.cd_tag_label.setText(config.setting["grouping_tagger_cd_tag"])
            self.cassette_tag_label.setText(config.setting["grouping_tagger_cassette_tag"])
            self.digital_tag_label.setText(config.setting["grouping_tagger_digital_tag"])
            self.bootleg_tag_label.setText(config.setting["grouping_tagger_bootleg_tag"])
            self.remaster_tag_label.setText(config.setting["grouping_tagger_remaster_tag"])
        except Exception as e:
            log.error(f"Grouping Tagger: Error loading detection settings: {e}")

    def save_settings(self):
        """Save settings to config"""
        try:
            config.setting["grouping_tagger_detect_vinyl"] = self.vinyl_checkbox.isChecked()
            config.setting["grouping_tagger_detect_cd"] = self.cd_checkbox.isChecked()
            config.setting["grouping_tagger_detect_cassette"] = self.cassette_checkbox.isChecked()
            config.setting["grouping_tagger_detect_digital"] = self.digital_checkbox.isChecked()
            config.setting["grouping_tagger_detect_bootleg"] = self.bootleg_checkbox.isChecked()
            config.setting["grouping_tagger_detect_remaster"] = self.remaster_checkbox.isChecked()
            config.setting["grouping_tagger_detect_format"] = self.format_checkbox.isChecked()
            config.setting["grouping_tagger_detect_quality"] = self.quality_checkbox.isChecked()

            # Save tag texts
            config.setting["grouping_tagger_vinyl_tag"] = self.vinyl_tag_label.text()
            config.setting["grouping_tagger_cd_tag"] = self.cd_tag_label.text()
            config.setting["grouping_tagger_cassette_tag"] = self.cassette_tag_label.text()
            config.setting["grouping_tagger_digital_tag"] = self.digital_tag_label.text()
            config.setting["grouping_tagger_bootleg_tag"] = self.bootleg_tag_label.text()
            config.setting["grouping_tagger_remaster_tag"] = self.remaster_tag_label.text()
        except Exception as e:
            log.error(f"Grouping Tagger: Error saving detection settings: {e}")


class TemplateManagerDialog(QtWidgets.QDialog):
    """Dialog for managing templates"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Template Manager")
        self.setMinimumSize(800, 600)
        self.create_ui()
        self.load_templates()

    def create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Description
        desc = QtWidgets.QLabel(
            "Create custom templates with variables like {SOURCE}, {FORMAT}, {QUALITY}, etc. "
            "Templates can be applied from the right-click menu."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("margin-bottom: 10px;")
        layout.addWidget(desc)

        # Template list
        self.template_list = QtWidgets.QListWidget()
        self.template_list.setMinimumHeight(200)
        layout.addWidget(self.template_list)

        # Template buttons
        template_buttons = QtWidgets.QHBoxLayout()
        self.add_template_btn = QtWidgets.QPushButton("Add Template")
        self.edit_template_btn = QtWidgets.QPushButton("Edit")
        self.delete_template_btn = QtWidgets.QPushButton("Delete")
        self.reset_templates_btn = QtWidgets.QPushButton("Reset to Defaults")
        self.export_json_btn = QtWidgets.QPushButton("Export JSON")
        self.import_json_btn = QtWidgets.QPushButton("Import JSON")

        self.add_template_btn.clicked.connect(self.add_template)
        self.edit_template_btn.clicked.connect(self.edit_template)
        self.delete_template_btn.clicked.connect(self.delete_template)
        self.reset_templates_btn.clicked.connect(self.reset_templates)
        self.export_json_btn.clicked.connect(self.export_to_json)
        self.import_json_btn.clicked.connect(self.import_from_json)

        template_buttons.addWidget(self.add_template_btn)
        template_buttons.addWidget(self.edit_template_btn)
        template_buttons.addWidget(self.delete_template_btn)
        template_buttons.addWidget(self.reset_templates_btn)
        template_buttons.addWidget(self.export_json_btn)
        template_buttons.addWidget(self.import_json_btn)
        template_buttons.addStretch()

        layout.addLayout(template_buttons)

        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_templates(self):
        """Load templates from JSON file or settings"""
        try:
            self.template_list.clear()

            # Load from JSON file, Picard settings, or empty list
            templates = load_templates_from_sources()

            # Populate list
            for template in templates:
                name = template.get("name", "Unnamed")
                self.template_list.addItem(name)
                # Store full template data in item
                item = self.template_list.item(self.template_list.count() - 1)
                item.setData(QtCore.Qt.UserRole, template)

        except Exception as e:
            log.error(f"Grouping Tagger: Error loading templates: {e}")

    def save_templates(self):
        """Save templates to settings and JSON file"""
        try:
            templates = []
            for i in range(self.template_list.count()):
                item = self.template_list.item(i)
                template_data = item.data(QtCore.Qt.UserRole)
                if template_data:
                    templates.append(template_data)

            # Save to Picard settings (for backward compatibility)
            config.setting["grouping_tagger_templates"] = json.dumps(templates)

            # Save to JSON file (primary storage)
            save_templates_to_json(templates)

            log.info(f"Grouping Tagger: Saved {len(templates)} templates to settings and JSON file")
        except Exception as e:
            log.error(f"Grouping Tagger: Error saving templates: {e}")

    def add_template(self):
        """Add a new template"""
        try:
            dialog = TemplateEditorDialog(parent=self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                template_data = dialog.get_template_data()

                # Validate template name
                if not template_data.get("name"):
                    QtWidgets.QMessageBox.warning(
                        self, "Invalid Template",
                        "Template name cannot be empty."
                    )
                    return

                # Add to list
                self.template_list.addItem(template_data["name"])
                item = self.template_list.item(self.template_list.count() - 1)
                item.setData(QtCore.Qt.UserRole, template_data)

                log.info(f"Grouping Tagger: Added template '{template_data['name']}'")
        except Exception as e:
            log.error(f"Grouping Tagger: Error adding template: {e}")

    def edit_template(self):
        """Edit the selected template"""
        try:
            current_item = self.template_list.currentItem()
            if not current_item:
                QtWidgets.QMessageBox.information(
                    self, "No Selection",
                    "Please select a template to edit."
                )
                return

            template_data = current_item.data(QtCore.Qt.UserRole)
            dialog = TemplateEditorDialog(template_data, parent=self)

            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                new_data = dialog.get_template_data()

                # Validate template name
                if not new_data.get("name"):
                    QtWidgets.QMessageBox.warning(
                        self, "Invalid Template",
                        "Template name cannot be empty."
                    )
                    return

                # Update item
                current_item.setText(new_data["name"])
                current_item.setData(QtCore.Qt.UserRole, new_data)

                log.info(f"Grouping Tagger: Updated template '{new_data['name']}'")
        except Exception as e:
            log.error(f"Grouping Tagger: Error editing template: {e}")

    def delete_template(self):
        """Delete the selected template"""
        try:
            current_item = self.template_list.currentItem()
            if not current_item:
                QtWidgets.QMessageBox.information(
                    self, "No Selection",
                    "Please select a template to delete."
                )
                return

            template_name = current_item.text()
            reply = QtWidgets.QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete the template '{template_name}'?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                row = self.template_list.row(current_item)
                self.template_list.takeItem(row)
                log.info(f"Grouping Tagger: Deleted template '{template_name}'")
        except Exception as e:
            log.error(f"Grouping Tagger: Error deleting template: {e}")

    def reset_templates(self):
        """Reset templates to defaults"""
        try:
            reply = QtWidgets.QMessageBox.question(
                self, "Confirm Reset",
                "Are you sure you want to reset all templates to defaults? This will delete all custom templates.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                self.template_list.clear()

                # Load defaults
                for template in DEFAULT_TEMPLATES:
                    self.template_list.addItem(template["name"])
                    item = self.template_list.item(self.template_list.count() - 1)
                    item.setData(QtCore.Qt.UserRole, template)

                log.info("Grouping Tagger: Reset templates to defaults")
        except Exception as e:
            log.error(f"Grouping Tagger: Error resetting templates: {e}")

    def export_to_json(self):
        """Export templates to a JSON file"""
        try:
            # Collect all templates
            templates = []
            for i in range(self.template_list.count()):
                item = self.template_list.item(i)
                template_data = item.data(QtCore.Qt.UserRole)
                if template_data:
                    templates.append(template_data)

            if not templates:
                QtWidgets.QMessageBox.information(
                    self, "No Templates",
                    "There are no templates to export."
                )
                return

            # Open file dialog with default location
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Export Templates to JSON",
                CONFIG_JSON_PATH,  # Default to standard location
                "JSON Files (*.json);;All Files (*)"
            )

            if file_path:
                # Write JSON to file
                import codecs
                with codecs.open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(templates, f, indent=2, ensure_ascii=False)

                QtWidgets.QMessageBox.information(
                    self, "Export Successful",
                    f"Successfully exported {len(templates)} templates to:\n{file_path}"
                )
                log.info(f"Grouping Tagger: Exported {len(templates)} templates to {file_path}")

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Export Error",
                f"Failed to export templates:\n{str(e)}"
            )
            log.error(f"Grouping Tagger: Error exporting templates: {e}")

    def import_from_json(self):
        """Import templates from a JSON file"""
        try:
            # Open file dialog
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Import Templates from JSON",
                "",
                "JSON Files (*.json);;All Files (*)"
            )

            if not file_path:
                return

            # Read JSON file
            import codecs
            with codecs.open(file_path, 'r', encoding='utf-8') as f:
                templates = json.load(f)

            # Validate structure
            if not isinstance(templates, list):
                raise ValueError("JSON must contain a list of templates")

            valid_templates = []
            for template in templates:
                if not isinstance(template, dict):
                    continue
                if "name" not in template or "template" not in template:
                    continue
                valid_templates.append(template)

            if not valid_templates:
                QtWidgets.QMessageBox.warning(
                    self, "Invalid File",
                    "No valid templates found in the JSON file.\n\n"
                    "Each template must have 'name' and 'template' fields."
                )
                return

            # Ask user about merge or replace
            reply = QtWidgets.QMessageBox.question(
                self, "Import Templates",
                f"Found {len(valid_templates)} valid templates.\n\n"
                "Do you want to:\n"
                "• YES - Add to existing templates (merge)\n"
                "• NO - Replace all existing templates",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Cancel
            )

            if reply == QtWidgets.QMessageBox.Cancel:
                return

            if reply == QtWidgets.QMessageBox.No:
                # Replace all templates
                self.template_list.clear()

            # Add imported templates
            for template in valid_templates:
                self.template_list.addItem(template["name"])
                item = self.template_list.item(self.template_list.count() - 1)
                item.setData(QtCore.Qt.UserRole, template)

            QtWidgets.QMessageBox.information(
                self, "Import Successful",
                f"Successfully imported {len(valid_templates)} templates from:\n{file_path}\n\n"
                "Note: Changes will take effect after saving and restarting Picard."
            )
            log.info(f"Grouping Tagger: Imported {len(valid_templates)} templates from {file_path}")

        except json.JSONDecodeError as e:
            QtWidgets.QMessageBox.critical(
                self, "Invalid JSON",
                f"Failed to parse JSON file:\n{str(e)}"
            )
            log.error(f"Grouping Tagger: JSON parse error during import: {e}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Import Error",
                f"Failed to import templates:\n{str(e)}"
            )
            log.error(f"Grouping Tagger: Error importing templates: {e}")


class FixedTagsManagerDialog(QtWidgets.QDialog):
    """Dialog for managing fixed tags"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fixed Tags Manager")
        self.setMinimumSize(700, 600)
        self.create_ui()
        self.load_fixed_tags()

    def create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Description
        desc = QtWidgets.QLabel(
            "Manage the fixed tags that appear in the right-click menu under 'Add: [Tag]'. "
            "Edit existing tags or create new ones."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("margin-bottom: 10px;")
        layout.addWidget(desc)

        # Fixed tags list
        self.fixed_tags_list = QtWidgets.QListWidget()
        self.fixed_tags_list.setMinimumHeight(300)
        layout.addWidget(self.fixed_tags_list)

        # Fixed tags buttons
        fixed_tags_buttons = QtWidgets.QHBoxLayout()
        self.add_fixed_tag_btn = QtWidgets.QPushButton("Add Tag")
        self.edit_fixed_tag_btn = QtWidgets.QPushButton("Edit")
        self.delete_fixed_tag_btn = QtWidgets.QPushButton("Delete")
        self.reset_fixed_tags_btn = QtWidgets.QPushButton("Reset to Defaults")

        self.add_fixed_tag_btn.clicked.connect(self.add_fixed_tag)
        self.edit_fixed_tag_btn.clicked.connect(self.edit_fixed_tag)
        self.delete_fixed_tag_btn.clicked.connect(self.delete_fixed_tag)
        self.reset_fixed_tags_btn.clicked.connect(self.reset_fixed_tags)

        fixed_tags_buttons.addWidget(self.add_fixed_tag_btn)
        fixed_tags_buttons.addWidget(self.edit_fixed_tag_btn)
        fixed_tags_buttons.addWidget(self.delete_fixed_tag_btn)
        fixed_tags_buttons.addWidget(self.reset_fixed_tags_btn)
        fixed_tags_buttons.addStretch()

        layout.addLayout(fixed_tags_buttons)

        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_fixed_tags(self):
        """Load fixed tags from settings"""
        try:
            self.fixed_tags_list.clear()

            # Load custom tags
            try:
                custom_tags = json.loads(config.setting["grouping_tagger_custom_fixed_tags"])
            except (json.JSONDecodeError, KeyError):
                custom_tags = {}

            # Merge with defaults
            all_tags = DEFAULT_FIXED_TAGS.copy()
            all_tags.update(custom_tags)

            # Populate list (show as "Name: Value")
            for name, value in sorted(all_tags.items()):
                display = f"{name}: {value}"
                self.fixed_tags_list.addItem(display)
                item = self.fixed_tags_list.item(self.fixed_tags_list.count() - 1)
                item.setData(QtCore.Qt.UserRole, {"name": name, "value": value})

        except Exception as e:
            log.error(f"Grouping Tagger: Error loading fixed tags: {e}")

    def save_fixed_tags(self):
        """Save custom fixed tags to settings"""
        try:
            custom_tags = {}

            # Collect all tags from list
            for i in range(self.fixed_tags_list.count()):
                item = self.fixed_tags_list.item(i)
                data = item.data(QtCore.Qt.UserRole)
                name = data["name"]
                value = data["value"]

                # Only save if different from default
                if name not in DEFAULT_FIXED_TAGS or DEFAULT_FIXED_TAGS[name] != value:
                    custom_tags[name] = value

            config.setting["grouping_tagger_custom_fixed_tags"] = json.dumps(custom_tags)
            log.info(f"Grouping Tagger: Saved {len(custom_tags)} custom fixed tags")

        except Exception as e:
            log.error(f"Grouping Tagger: Error saving fixed tags: {e}")

    def add_fixed_tag(self):
        """Add new fixed tag"""
        try:
            # Ask for tag name
            name, ok = QtWidgets.QInputDialog.getText(
                self, "Add Fixed Tag",
                "Enter tag name (e.g., 'Japanese Import'):"
            )

            if not ok or not name.strip():
                return

            name = name.strip()

            # Check if already exists
            for i in range(self.fixed_tags_list.count()):
                item = self.fixed_tags_list.item(i)
                data = item.data(QtCore.Qt.UserRole)
                if data["name"] == name:
                    QtWidgets.QMessageBox.warning(
                        self, "Duplicate Tag",
                        f"A tag named '{name}' already exists. Use Edit to modify it."
                    )
                    return

            # Ask for tag value
            value, ok = QtWidgets.QInputDialog.getText(
                self, "Add Fixed Tag",
                f"Enter value for '{name}' (what will appear in GROUPING):",
                text=name
            )

            if not ok or not value.strip():
                return

            value = value.strip()

            # Add to list
            display = f"{name}: {value}"
            self.fixed_tags_list.addItem(display)
            item = self.fixed_tags_list.item(self.fixed_tags_list.count() - 1)
            item.setData(QtCore.Qt.UserRole, {"name": name, "value": value})

            log.info(f"Grouping Tagger: Added fixed tag '{name}: {value}'")

        except Exception as e:
            log.error(f"Grouping Tagger: Error adding fixed tag: {e}")

    def edit_fixed_tag(self):
        """Edit selected fixed tag"""
        try:
            current_item = self.fixed_tags_list.currentItem()
            if not current_item:
                QtWidgets.QMessageBox.information(
                    self, "No Selection",
                    "Please select a tag to edit."
                )
                return

            data = current_item.data(QtCore.Qt.UserRole)
            old_name = data["name"]
            old_value = data["value"]

            # Ask for new value
            new_value, ok = QtWidgets.QInputDialog.getText(
                self, "Edit Fixed Tag",
                f"Edit value for '{old_name}':",
                text=old_value
            )

            if not ok or not new_value.strip():
                return

            new_value = new_value.strip()

            # Update item
            current_item.setText(f"{old_name}: {new_value}")
            current_item.setData(QtCore.Qt.UserRole, {"name": old_name, "value": new_value})

            log.info(f"Grouping Tagger: Edited fixed tag '{old_name}': '{old_value}' → '{new_value}'")

        except Exception as e:
            log.error(f"Grouping Tagger: Error editing fixed tag: {e}")

    def delete_fixed_tag(self):
        """Delete selected fixed tag"""
        try:
            current_item = self.fixed_tags_list.currentItem()
            if not current_item:
                QtWidgets.QMessageBox.information(
                    self, "No Selection",
                    "Please select a tag to delete."
                )
                return

            data = current_item.data(QtCore.Qt.UserRole)
            name = data["name"]

            # Confirm deletion
            reply = QtWidgets.QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete the tag '{name}'?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                row = self.fixed_tags_list.row(current_item)
                self.fixed_tags_list.takeItem(row)

                log.info(f"Grouping Tagger: Deleted fixed tag '{name}'")

        except Exception as e:
            log.error(f"Grouping Tagger: Error deleting fixed tag: {e}")

    def reset_fixed_tags(self):
        """Reset fixed tags to defaults"""
        try:
            reply = QtWidgets.QMessageBox.question(
                self, "Confirm Reset",
                "Are you sure you want to reset all fixed tags to defaults? This will delete all custom tags.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                self.load_fixed_tags()
                log.info("Grouping Tagger: Reset fixed tags to defaults")

        except Exception as e:
            log.error(f"Grouping Tagger: Error resetting fixed tags: {e}")


class GroupingOptionsPage(OptionsPage):
    NAME = "grouping_tagger"
    TITLE = "Grouping Tagger"
    PARENT = "plugins"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.create_ui()

    def create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        title = QtWidgets.QLabel("Grouping Tagger")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(title)

        description = QtWidgets.QLabel(
            "Configure automatic detection rules and templates. "
            "Use the buttons below to open configuration dialogs. "
            "Right-click menu on albums/tracks provides tagging options."
        )
        description.setStyleSheet("font-size: 11px; margin-bottom: 10px;")
        description.setWordWrap(True)
        layout.addWidget(description)

        # Configuration buttons
        config_group = QtWidgets.QGroupBox("Configuration")
        config_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        config_layout = QtWidgets.QVBoxLayout(config_group)

        # Detection Matrix button
        detection_btn_layout = QtWidgets.QHBoxLayout()
        self.open_detection_btn = QtWidgets.QPushButton("Configure Detection Rules...")
        self.open_detection_btn.setMinimumHeight(40)
        self.open_detection_btn.clicked.connect(self.open_detection_dialog)
        self.open_detection_btn.setToolTip("Configure which sources/formats/qualities to detect")
        detection_btn_layout.addWidget(self.open_detection_btn)
        config_layout.addLayout(detection_btn_layout)

        # Templates button
        templates_btn_layout = QtWidgets.QHBoxLayout()
        self.open_templates_btn = QtWidgets.QPushButton("Manage Templates...")
        self.open_templates_btn.setMinimumHeight(40)
        self.open_templates_btn.clicked.connect(self.open_templates_dialog)
        self.open_templates_btn.setToolTip("Create and manage template patterns")
        templates_btn_layout.addWidget(self.open_templates_btn)
        config_layout.addLayout(templates_btn_layout)

        # Fixed Tags button
        fixed_tags_btn_layout = QtWidgets.QHBoxLayout()
        self.open_fixed_tags_btn = QtWidgets.QPushButton("Manage Fixed Tags...")
        self.open_fixed_tags_btn.setMinimumHeight(40)
        self.open_fixed_tags_btn.clicked.connect(self.open_fixed_tags_dialog)
        self.open_fixed_tags_btn.setToolTip("Manage right-click menu fixed tag options")
        fixed_tags_btn_layout.addWidget(self.open_fixed_tags_btn)
        config_layout.addLayout(fixed_tags_btn_layout)

        # Import/Export buttons (v3.1.0: combined templates + fixed tags)
        import_export_layout = QtWidgets.QHBoxLayout()
        self.export_config_btn = QtWidgets.QPushButton("Export Configuration (JSON)")
        self.export_config_btn.setMinimumHeight(35)
        self.export_config_btn.clicked.connect(self.export_configuration)
        self.export_config_btn.setToolTip("Export both templates and fixed tags to JSON file for backup or sharing")

        self.import_config_btn = QtWidgets.QPushButton("Import Configuration (JSON)")
        self.import_config_btn.setMinimumHeight(35)
        self.import_config_btn.clicked.connect(self.import_configuration)
        self.import_config_btn.setToolTip("Import templates and fixed tags from JSON file")

        import_export_layout.addWidget(self.export_config_btn)
        import_export_layout.addWidget(self.import_config_btn)
        config_layout.addLayout(import_export_layout)

        layout.addWidget(config_group)

        # Behavior options
        behavior_group = QtWidgets.QGroupBox("Behavior Options")
        behavior_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        behavior_layout = QtWidgets.QVBoxLayout(behavior_group)

        self.append_checkbox = QtWidgets.QCheckBox("Append to existing GROUPING (instead of replace)")
        self.append_checkbox.setToolTip("If checked, new tags will be appended to existing GROUPING value")
        behavior_layout.addWidget(self.append_checkbox)

        # Separator option
        separator_layout = QtWidgets.QHBoxLayout()
        separator_layout.addWidget(QtWidgets.QLabel("Tag separator:"))
        self.separator_input = QtWidgets.QLineEdit()
        self.separator_input.setMaximumWidth(100)
        self.separator_input.setToolTip("Characters to use between multiple tags (default: ', ')")
        separator_layout.addWidget(self.separator_input)
        separator_layout.addStretch()
        behavior_layout.addLayout(separator_layout)

        layout.addWidget(behavior_group)

        # Manual tags option
        manual_group = QtWidgets.QGroupBox("Additional Tags (Always Added)")
        manual_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        manual_layout = QtWidgets.QVBoxLayout(manual_group)

        manual_desc = QtWidgets.QLabel(
            "Add custom tags that will always be included (comma-separated).\n"
            "Example: 'Remastered, Limited Edition, Japanese Import'"
        )
        manual_desc.setStyleSheet("font-size: 10px; margin-bottom: 5px;")
        manual_desc.setWordWrap(True)
        manual_layout.addWidget(manual_desc)

        self.manual_tags_input = QtWidgets.QLineEdit()
        self.manual_tags_input.setPlaceholderText("e.g., Remastered, Limited Edition")
        manual_layout.addWidget(self.manual_tags_input)

        layout.addWidget(manual_group)

        # Preview section
        preview_group = QtWidgets.QGroupBox("Preview")
        preview_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)

        self.preview_text = QtWidgets.QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumHeight(100)
        self.preview_text.setMaximumHeight(120)
        self.preview_text.setStyleSheet(
            "QTextEdit { font-family: 'Courier New', monospace; font-size: 11px; "
            "padding: 8px; }"
        )
        preview_layout.addWidget(self.preview_text)

        layout.addWidget(preview_group)

        layout.addStretch()

        # Connect signals for live preview
        self.append_checkbox.stateChanged.connect(self.update_preview)
        self.separator_input.textChanged.connect(self.update_preview)
        self.manual_tags_input.textChanged.connect(self.update_preview)

    def open_detection_dialog(self):
        """Open detection configuration dialog"""
        try:
            dialog = DetectionMatrixDialog(self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                dialog.save_settings()
                self.update_preview()
                log.info("Grouping Tagger: Detection settings updated")
        except Exception as e:
            log.error(f"Grouping Tagger: Error opening detection dialog: {e}")

    def open_templates_dialog(self):
        """Open template manager dialog"""
        try:
            dialog = TemplateManagerDialog(self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                dialog.save_templates()
                log.info("Grouping Tagger: Templates updated")
        except Exception as e:
            log.error(f"Grouping Tagger: Error opening templates dialog: {e}")

    def open_fixed_tags_dialog(self):
        """Open fixed tags manager dialog"""
        try:
            dialog = FixedTagsManagerDialog(self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                dialog.save_fixed_tags()
                log.info("Grouping Tagger: Fixed tags updated")
        except Exception as e:
            log.error(f"Grouping Tagger: Error opening fixed tags dialog: {e}")

    def export_configuration(self):
        """Export both templates and fixed tags to JSON file (v3.1.0)"""
        try:
            # Collect current templates from settings
            templates = load_templates_from_sources()

            # Collect current fixed tags from settings
            try:
                fixed_tags_str = config.setting["grouping_tagger_custom_fixed_tags"] if "grouping_tagger_custom_fixed_tags" in config.setting else json.dumps({})
                fixed_tags = json.loads(fixed_tags_str)
            except (json.JSONDecodeError, TypeError):
                fixed_tags = {}

            # Show file save dialog
            default_path = os.path.join(JSON_PREFERENCES_DIR, "grouping_tagger_config.json")
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Export Configuration (Templates + Fixed Tags)",
                default_path,
                "JSON Files (*.json)"
            )

            if file_path:
                # Ensure .json extension
                if not file_path.endswith('.json'):
                    file_path += '.json'

                # Save using combined export function
                save_config_to_json(templates=templates, fixed_tags=fixed_tags)

                # If user chose a different path, copy the file there too
                if file_path != CONFIG_JSON_PATH:
                    import shutil
                    shutil.copy(CONFIG_JSON_PATH, file_path)

                QtWidgets.QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Configuration exported successfully to:\n{file_path}\n\n"
                    f"Templates: {len(templates)}\n"
                    f"Fixed Tags: {len(fixed_tags)}"
                )
                log.info(f"Grouping Tagger: Configuration exported to {file_path}")

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export configuration:\n{str(e)}"
            )
            log.error(f"Grouping Tagger: Export failed: {e}")

    def import_configuration(self):
        """Import templates and fixed tags from JSON file (v3.1.0)"""
        try:
            # Show file open dialog
            default_path = JSON_PREFERENCES_DIR
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Import Configuration (Templates + Fixed Tags)",
                default_path,
                "JSON Files (*.json)"
            )

            if not file_path:
                return

            # Load the JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            # Determine what we're importing
            has_templates = False
            has_fixed_tags = False
            imported_templates = []
            imported_fixed_tags = {}

            # Check if it's the new combined format
            if isinstance(import_data, dict):
                if "templates" in import_data:
                    imported_templates = import_data["templates"]
                    has_templates = True
                if "fixed_tags" in import_data:
                    imported_fixed_tags = import_data["fixed_tags"]
                    has_fixed_tags = True
            # Check if it's legacy template-only format
            elif isinstance(import_data, list):
                imported_templates = import_data
                has_templates = True

            if not has_templates and not has_fixed_tags:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Invalid File",
                    "The selected file does not contain valid templates or fixed tags."
                )
                return

            # Build message about what will be imported
            import_info = []
            if has_templates:
                import_info.append(f"Templates: {len(imported_templates)}")
            if has_fixed_tags:
                import_info.append(f"Fixed Tags: {len(imported_fixed_tags)}")

            # Ask user if they want to merge or replace
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Question)
            msg.setWindowTitle("Import Configuration")
            msg.setText(f"Found:\n" + "\n".join(import_info) + "\n\nHow do you want to import?")
            msg.setInformativeText(
                "Merge: Add imported items to your existing configuration\n"
                "Replace: Completely replace your current configuration"
            )
            merge_btn = msg.addButton("Merge", QtWidgets.QMessageBox.AcceptRole)
            replace_btn = msg.addButton("Replace", QtWidgets.QMessageBox.DestructiveRole)
            cancel_btn = msg.addButton("Cancel", QtWidgets.QMessageBox.RejectRole)
            msg.setDefaultButton(merge_btn)

            msg.exec_()
            clicked = msg.clickedButton()

            if clicked == cancel_btn:
                return

            merge_mode = (clicked == merge_btn)

            # Import templates
            if has_templates:
                if merge_mode:
                    # Merge: add imported templates to existing ones
                    current_templates = load_templates_from_sources()
                    # Avoid duplicates by name
                    existing_names = {t["name"] for t in current_templates}
                    for template in imported_templates:
                        if template["name"] not in existing_names:
                            current_templates.append(template)
                    final_templates = current_templates
                else:
                    # Replace: use only imported templates
                    final_templates = imported_templates

                # Save templates to both settings and JSON
                config.setting["grouping_tagger_templates"] = json.dumps(final_templates)
                saved = save_config_to_json(templates=final_templates, fixed_tags=None)
                if not saved:
                    raise RuntimeError("Failed to write templates to JSON file")

            # Import fixed tags
            if has_fixed_tags:
                if merge_mode:
                    # Merge: combine with existing tags
                    try:
                        current_tags_str = config.setting["grouping_tagger_custom_fixed_tags"] if "grouping_tagger_custom_fixed_tags" in config.setting else json.dumps({})
                        current_tags = json.loads(current_tags_str)
                    except (json.JSONDecodeError, TypeError):
                        current_tags = {}
                    # Update existing tags with imported ones
                    for key, value in imported_fixed_tags.items():
                        current_tags[key] = value
                    final_tags = current_tags
                else:
                    # Replace: use only imported tags
                    final_tags = imported_fixed_tags

                # Save fixed tags to both settings and JSON
                config.setting["grouping_tagger_custom_fixed_tags"] = json.dumps(final_tags)
                saved = save_config_to_json(templates=None, fixed_tags=final_tags)
                if not saved:
                    raise RuntimeError("Failed to write fixed tags to JSON file")

            # Show success message
            action_text = "merged with" if merge_mode else "replaced"
            QtWidgets.QMessageBox.information(
                self,
                "Import Successful",
                f"Configuration successfully {action_text} your existing settings!\n\n" +
                "\n".join(import_info) + "\n\n"
                "Restart Picard to apply changes to the right-click menu."
            )
            log.info(f"Grouping Tagger: Configuration imported from {file_path} (merge={merge_mode})")

        except json.JSONDecodeError as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Import Failed",
                f"Invalid JSON file:\n{str(e)}"
            )
            log.error(f"Grouping Tagger: Import failed - invalid JSON: {e}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Import Failed",
                f"Failed to import configuration:\n{str(e)}"
            )
            log.error(f"Grouping Tagger: Import failed: {e}")

    def update_preview(self):
        """Update preview with current settings"""
        try:
            # Sample scenarios
            examples = []

            # Get current settings from config (since widgets are in dialogs now)
            detect_vinyl = config.setting["grouping_tagger_detect_vinyl"]
            detect_cd = config.setting["grouping_tagger_detect_cd"]
            detect_digital = config.setting["grouping_tagger_detect_digital"]
            detect_bootleg = config.setting["grouping_tagger_detect_bootleg"]
            detect_remaster = config.setting["grouping_tagger_detect_remaster"]
            detect_format = config.setting["grouping_tagger_detect_format"]
            detect_quality = config.setting["grouping_tagger_detect_quality"]
            separator = self.separator_input.text() or ", "
            manual_tags = self.manual_tags_input.text().strip()

            vinyl_tag = config.setting["grouping_tagger_vinyl_tag"]
            cd_tag = config.setting["grouping_tagger_cd_tag"]
            digital_tag = config.setting["grouping_tagger_digital_tag"]
            bootleg_tag = config.setting["grouping_tagger_bootleg_tag"]
            remaster_tag = config.setting["grouping_tagger_remaster_tag"]

            # Example 1: Vinyl FLAC release (format + lossless)
            tags1 = []
            if detect_vinyl:
                tags1.append(vinyl_tag)
            if detect_format:
                tags1.append("FLAC")
            if detect_quality:
                tags1.append("Lossless")
            if manual_tags:
                tags1.extend([tag.strip() for tag in manual_tags.split(",") if tag.strip()])
            example1 = separator.join(tags1) if tags1 else "(no tags)"
            examples.append(f"Vinyl FLAC 16-bit: '{example1}'")

            # Example 2: Digital MP3 release (format + lossy)
            tags2 = []
            if detect_digital:
                tags2.append(digital_tag)
            if detect_format:
                tags2.append("MP3")
            if detect_quality:
                tags2.append("Lossy")
            if manual_tags:
                tags2.extend([tag.strip() for tag in manual_tags.split(",") if tag.strip()])
            example2 = separator.join(tags2) if tags2 else "(no tags)"
            examples.append(f"Digital MP3: '{example2}'")

            # Example 3: CD Remaster 24-bit (format + hi-def)
            tags3 = []
            if detect_cd:
                tags3.append(cd_tag)
            if detect_remaster:
                tags3.append(remaster_tag)
            if detect_format:
                tags3.append("FLAC")
            if detect_quality:
                tags3.append("Hi-Def")
            if manual_tags:
                tags3.extend([tag.strip() for tag in manual_tags.split(",") if tag.strip()])
            example3 = separator.join(tags3) if tags3 else "(no tags)"
            examples.append(f"CD Remaster FLAC 24-bit: '{example3}'")

            # Example 4: Just format detection
            tags4 = []
            if detect_bootleg:
                tags4.append(bootleg_tag)
            if detect_format:
                tags4.append("WAV")
            if manual_tags:
                tags4.extend([tag.strip() for tag in manual_tags.split(",") if tag.strip()])
            example4 = separator.join(tags4) if tags4 else "(no tags)"
            examples.append(f"Bootleg WAV (format only): '{example4}'")

            self.preview_text.setText("\n".join(examples))

        except Exception as e:
            self.preview_text.setText(f"Preview Error: {str(e)}")

    def load(self):
        """Load settings"""
        try:
            self.append_checkbox.setChecked(config.setting["grouping_tagger_append_mode"])
            self.separator_input.setText(config.setting["grouping_tagger_separator"])
            self.manual_tags_input.setText(config.setting["grouping_tagger_manual_tags"])

            self.update_preview()
        except Exception as e:
            log.error(f"Grouping Tagger: Error loading settings: {e}")

    def save(self):
        """Save settings"""
        try:
            config.setting["grouping_tagger_append_mode"] = self.append_checkbox.isChecked()
            config.setting["grouping_tagger_separator"] = self.separator_input.text()
            config.setting["grouping_tagger_manual_tags"] = self.manual_tags_input.text()

            # Detection settings, templates, and fixed tags are saved via their respective dialogs
        except Exception as e:
            log.error(f"Grouping Tagger: Error saving settings: {e}")


class GroupingActionAuto(BaseAction):
    """Auto-detection action using configured rules"""
    NAME = "Auto-Detect"
    MENU = ("Grouping",)

    def callback(self, objs):
        try:
            # Get settings
            detect_vinyl = config.setting["grouping_tagger_detect_vinyl"]
            detect_cd = config.setting["grouping_tagger_detect_cd"]
            detect_cassette = config.setting["grouping_tagger_detect_cassette"]
            detect_bootleg = config.setting["grouping_tagger_detect_bootleg"]
            detect_digital = config.setting["grouping_tagger_detect_digital"]
            detect_remaster = config.setting["grouping_tagger_detect_remaster"]
            detect_format = config.setting["grouping_tagger_detect_format"]
            detect_quality = config.setting["grouping_tagger_detect_quality"]
            append_mode = config.setting["grouping_tagger_append_mode"]
            separator = config.setting["grouping_tagger_separator"]
            manual_tags = config.setting["grouping_tagger_manual_tags"]

            # Get custom tag texts
            vinyl_tag = config.setting["grouping_tagger_vinyl_tag"]
            cd_tag = config.setting["grouping_tagger_cd_tag"]
            cassette_tag = config.setting["grouping_tagger_cassette_tag"]
            bootleg_tag = config.setting["grouping_tagger_bootleg_tag"]
            digital_tag = config.setting["grouping_tagger_digital_tag"]
            remaster_tag = config.setting["grouping_tagger_remaster_tag"]

            processed_objects = set()
            changed = 0

            for obj, metadata in self._iter_unique_metadata_with_objects(objs, processed_objects):
                if self._apply_grouping_tags(
                    metadata, detect_vinyl, detect_cd, detect_cassette, detect_bootleg,
                    detect_digital, detect_remaster, detect_format, detect_quality, append_mode, separator,
                    manual_tags, vinyl_tag, cd_tag, cassette_tag, bootleg_tag,
                    digital_tag, remaster_tag
                ):
                    changed += 1
                    # Update UI
                    if hasattr(obj, 'update'):
                        obj.update()

            log.info(f"Grouping Tagger: Auto-tagged {changed} items")

        except Exception as e:
            log.error(f"Grouping Tagger: Auto action callback failed: {e}")

    def _iter_unique_metadata_with_objects(self, objs, processed_objects):
        """Yield all metadata objects from selection"""
        for obj in objs:
            obj_id = id(obj)
            if obj_id in processed_objects:
                continue

            processed_objects.add(obj_id)
            class_name = obj.__class__.__name__

            if class_name in ("File",):
                if hasattr(obj, 'metadata'):
                    yield (obj, obj.metadata)
            elif class_name in ("Track",):
                if hasattr(obj, 'metadata'):
                    yield (obj, obj.metadata)
            elif class_name in ("Album",):
                if hasattr(obj, 'metadata'):
                    yield (obj, obj.metadata)
                for track in getattr(obj, "tracks", []):
                    track_id = id(track)
                    if track_id not in processed_objects and hasattr(track, 'metadata'):
                        processed_objects.add(track_id)
                        yield (track, track.metadata)
                        for file_obj in getattr(track, "linked_files", []):
                            file_id = id(file_obj)
                            if file_id not in processed_objects and hasattr(file_obj, 'metadata'):
                                processed_objects.add(file_id)
                                yield (file_obj, file_obj.metadata)
            elif class_name in ("Cluster",):
                for file_obj in getattr(obj, "files", []):
                    file_id = id(file_obj)
                    if file_id not in processed_objects and hasattr(file_obj, 'metadata'):
                        processed_objects.add(file_id)
                        yield (file_obj, file_obj.metadata)
            else:
                if hasattr(obj, 'metadata'):
                    yield (obj, obj.metadata)

    def _apply_grouping_tags(self, metadata, detect_vinyl, detect_cd, detect_cassette,
                            detect_bootleg, detect_digital, detect_remaster, detect_format, detect_quality,
                            append_mode, separator, manual_tags, vinyl_tag, cd_tag,
                            cassette_tag, bootleg_tag, digital_tag, remaster_tag):
        """Apply GROUPING tags to metadata"""
        try:
            tags = []

            # Detect and collect tags with custom text
            if detect_vinyl and _detect_vinyl(metadata):
                tags.append(vinyl_tag)

            if detect_cd and _detect_cd(metadata):
                tags.append(cd_tag)

            if detect_cassette and _detect_cassette(metadata):
                tags.append(cassette_tag)

            if detect_bootleg and _detect_bootleg(metadata):
                tags.append(bootleg_tag)

            if detect_digital and _detect_digital(metadata):
                tags.append(digital_tag)

            if detect_remaster and _detect_remaster(metadata):
                tags.append(remaster_tag)

            # Format detection (just format name: MP3, FLAC, WAV, etc.)
            if detect_format:
                file_format = _detect_format(metadata)
                if file_format:
                    tags.append(file_format)

            # Quality tier detection (Lossy, Lossless, Hi-Def)
            if detect_quality:
                quality = _detect_quality(metadata)
                if quality:
                    tags.append(quality)

            # Add manual tags
            if manual_tags:
                manual_tag_list = [tag.strip() for tag in manual_tags.split(",") if tag.strip()]
                tags.extend(manual_tag_list)

            # Apply to GROUPING field
            if tags:
                new_grouping = separator.join(tags)

                if append_mode:
                    existing_grouping = _get_metadata_value(metadata, "grouping")
                    if existing_grouping:
                        # Avoid duplicates
                        existing_tags = [t.strip() for t in existing_grouping.split(separator)]
                        for tag in tags:
                            if tag not in existing_tags:
                                existing_tags.append(tag)
                        new_grouping = separator.join(existing_tags)

                metadata["grouping"] = new_grouping
                log.debug(f"Grouping Tagger: Set GROUPING = '{new_grouping}'")
                return True

            return False

        except Exception as e:
            log.error(f"Grouping Tagger: Error applying tags: {e}")
            return False


def create_template_action(template_name, template_string, divider):
    """Factory function to create a template action class with NAME at class level"""

    class GroupingActionTemplate(BaseAction):
        """Template action - applies a template pattern"""
        NAME = f"Template: {template_name}"
        MENU = ("Grouping",)

        def __init__(self):
            super().__init__()
            self.template_name = template_name
            self.template_string = template_string
            self.divider = divider

        def callback(self, objs):
            try:
                append_mode = config.setting["grouping_tagger_append_mode"]
                separator = config.setting["grouping_tagger_separator"]
                manual_tags = config.setting["grouping_tagger_manual_tags"]

                processed_objects = set()
                changed = 0

                for obj, metadata in self._iter_unique_metadata_with_objects(objs, processed_objects):
                    # Apply template to generate grouping value
                    grouping_value = _apply_template(self.template_string, self.divider, metadata, manual_tags)

                    if grouping_value:
                        if append_mode:
                            existing_grouping = _get_metadata_value(metadata, "grouping")
                            if existing_grouping:
                                # Combine with existing
                                metadata["grouping"] = f"{existing_grouping}{separator}{grouping_value}"
                            else:
                                metadata["grouping"] = grouping_value
                        else:
                            metadata["grouping"] = grouping_value

                        changed += 1

                        # Update UI
                        if hasattr(obj, 'update'):
                            obj.update()

                log.info(f"Grouping Tagger: Applied template '{self.template_name}' to {changed} items")

            except Exception as e:
                log.error(f"Grouping Tagger: Template action failed: {e}")

        def _iter_unique_metadata_with_objects(self, objs, processed_objects):
            """Yield all metadata objects from selection"""
            for obj in objs:
                obj_id = id(obj)
                if obj_id in processed_objects:
                    continue

                processed_objects.add(obj_id)
                class_name = obj.__class__.__name__

                if class_name in ("File",):
                    if hasattr(obj, 'metadata'):
                        yield (obj, obj.metadata)
                elif class_name in ("Track",):
                    if hasattr(obj, 'metadata'):
                        yield (obj, obj.metadata)
                elif class_name in ("Album",):
                    if hasattr(obj, 'metadata'):
                        yield (obj, obj.metadata)
                    for track in getattr(obj, "tracks", []):
                        track_id = id(track)
                        if track_id not in processed_objects and hasattr(track, 'metadata'):
                            processed_objects.add(track_id)
                            yield (track, track.metadata)
                            for file_obj in getattr(track, "linked_files", []):
                                file_id = id(file_obj)
                                if file_id not in processed_objects and hasattr(file_obj, 'metadata'):
                                    processed_objects.add(file_id)
                                    yield (file_obj, file_obj.metadata)
                elif class_name in ("Cluster",):
                    for file_obj in getattr(obj, "files", []):
                        file_id = id(file_obj)
                        if file_id not in processed_objects and hasattr(file_obj, 'metadata'):
                            processed_objects.add(file_id)
                            yield (file_obj, file_obj.metadata)
                else:
                    if hasattr(obj, 'metadata'):
                        yield (obj, obj.metadata)

    return GroupingActionTemplate


def create_fixed_action(tag_name, tag_value):
    """Factory function to create a fixed tag action class with NAME at class level"""

    class GroupingActionFixed(BaseAction):
        """Fixed tag action - applies a specific tag"""
        NAME = f"Add: {tag_value}"
        MENU = ("Grouping",)

        def __init__(self):
            super().__init__()
            self.tag_value = tag_value

        def callback(self, objs):
            try:
                append_mode = config.setting["grouping_tagger_append_mode"]
                separator = config.setting["grouping_tagger_separator"]

                processed_objects = set()
                changed = 0

                for obj, metadata in self._iter_unique_metadata_with_objects(objs, processed_objects):
                    existing_grouping = _get_metadata_value(metadata, "grouping")

                    if append_mode and existing_grouping:
                        # Check if tag already exists
                        existing_tags = [t.strip() for t in existing_grouping.split(separator)]
                        if self.tag_value not in existing_tags:
                            existing_tags.append(self.tag_value)
                            metadata["grouping"] = separator.join(existing_tags)
                            changed += 1
                    else:
                        metadata["grouping"] = self.tag_value
                        changed += 1

                    # Update UI
                    if hasattr(obj, 'update'):
                        obj.update()

                log.info(f"Grouping Tagger: Added '{self.tag_value}' to {changed} items")

            except Exception as e:
                log.error(f"Grouping Tagger: Fixed tag action failed: {e}")

        def _iter_unique_metadata_with_objects(self, objs, processed_objects):
            """Yield all metadata objects from selection"""
            for obj in objs:
                obj_id = id(obj)
                if obj_id in processed_objects:
                    continue

                processed_objects.add(obj_id)
                class_name = obj.__class__.__name__

                if class_name in ("File",):
                    if hasattr(obj, 'metadata'):
                        yield (obj, obj.metadata)
                elif class_name in ("Track",):
                    if hasattr(obj, 'metadata'):
                        yield (obj, obj.metadata)
                elif class_name in ("Album",):
                    if hasattr(obj, 'metadata'):
                        yield (obj, obj.metadata)
                    for track in getattr(obj, "tracks", []):
                        track_id = id(track)
                        if track_id not in processed_objects and hasattr(track, 'metadata'):
                            processed_objects.add(track_id)
                            yield (track, track.metadata)
                            for file_obj in getattr(track, "linked_files", []):
                                file_id = id(file_obj)
                                if file_id not in processed_objects and hasattr(file_obj, 'metadata'):
                                    processed_objects.add(file_id)
                                    yield (file_obj, file_obj.metadata)
                elif class_name in ("Cluster",):
                    for file_obj in getattr(obj, "files", []):
                        file_id = id(file_obj)
                        if file_id not in processed_objects and hasattr(file_obj, 'metadata'):
                            processed_objects.add(file_id)
                            yield (file_obj, file_obj.metadata)
                else:
                    if hasattr(obj, 'metadata'):
                        yield (obj, obj.metadata)

    return GroupingActionFixed


# Register the auto-detection action
_grouping_action_auto = GroupingActionAuto()
register_album_action(_grouping_action_auto)
register_track_action(_grouping_action_auto)
register_file_action(_grouping_action_auto)
register_cluster_action(_grouping_action_auto)

# Register fixed tag actions (defaults + custom)
all_fixed_tags = get_all_fixed_tags()
for tag_name, tag_value in all_fixed_tags.items():
    ActionClass = create_fixed_action(tag_name, tag_value)
    action = ActionClass()
    register_album_action(action)
    register_track_action(action)
    register_file_action(action)
    register_cluster_action(action)

log.info(f"Grouping Tagger: Registered {len(all_fixed_tags)} fixed tag actions")

# Register template actions
try:
    # Load templates from JSON file, Picard settings, or defaults
    templates = load_templates_from_sources()

    # Register each template as a context menu action
    for template in templates:
        template_name = template.get("name", "Unnamed")
        template_string = template.get("template", "")
        divider = template.get("divider", " | ")

        if template_string:
            ActionClass = create_template_action(template_name, template_string, divider)
            action = ActionClass()
            register_album_action(action)
            register_track_action(action)
            register_file_action(action)
            register_cluster_action(action)

    log.info(f"Grouping Tagger: Registered {len(templates)} template actions")
except Exception as e:
    log.error(f"Grouping Tagger: Failed to register template actions: {e}")

# Register the options page
try:
    register_options_page(GroupingOptionsPage)
except Exception as e:
    log.error(f"Grouping Tagger: Options page registration failed: {e}")

log.info("Grouping Tagger: Plugin loaded successfully")
