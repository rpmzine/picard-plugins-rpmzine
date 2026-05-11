# -*- coding: utf-8 -*-
PLUGIN_NAME = "Suffix Appender"
PLUGIN_AUTHOR = "rpmzine"
PLUGIN_DESCRIPTION = "Append custom, formula-based suffixes to Album, Track Title, Comment, Disc Subtitle, or Work fields via context menu. Uses JSON templates with metadata variables (country, format, bit depth, sample rate, bitstream codec, etc.). Includes EP/Single/Vinyl/CD detection."
PLUGIN_VERSION = "2.4.0"
PLUGIN_API_VERSIONS = ["2.10", "2.11", "2.12", "2.13", "3.0"]
PLUGIN_LICENSE = "MIT"
PLUGIN_LICENSE_URL = "https://opensource.org/licenses/MIT"

import re
import json
from picard import config, log
from picard.config import BoolOption, TextOption
from ._compat import (
    OptionsPage,
    BaseAction,
    Qt, QtCore, QtGui, QtWidgets,
    register_album_action, register_cluster_action,
    register_file_action, register_options_page, register_track_action,
)

# Configuration options with proper defaults
BoolOption("setting", "suffix_appender_avoid_duplicates", True)
TextOption("setting", "suffix_appender_active_formula", " [<releasecountry> <format>] [<bits_per_sample>-<sample_rate[:2]>]")
TextOption("setting", "suffix_appender_active_preset", "Country + Format")
BoolOption("setting", "suffix_appender_target_album", True)
BoolOption("setting", "suffix_appender_target_title", False)
BoolOption("setting", "suffix_appender_target_comment", False)
BoolOption("setting", "suffix_appender_target_discsubtitle", False)
BoolOption("setting", "suffix_appender_target_work", False)
TextOption("setting", "suffix_appender_templates", "")  # JSON list of templates
BoolOption("setting", "suffix_appender_templates_initialized", False)  # Track if templates have been set up

# Enhanced detection options with wrappers
BoolOption("setting", "suffix_appender_add_ep", True)
BoolOption("setting", "suffix_appender_add_single", True) 
BoolOption("setting", "suffix_appender_add_cd", False)
BoolOption("setting", "suffix_appender_add_vinyl", False)
TextOption("setting", "suffix_appender_ep_wrapper", " EP")
TextOption("setting", "suffix_appender_single_wrapper", " [Single]")
TextOption("setting", "suffix_appender_cd_wrapper", " [CD]")
TextOption("setting", "suffix_appender_vinyl_wrapper", " [Vinyl]")

TextOption("setting", "suffix_appender_key_aliases", json.dumps({
    "releasecountry": ["releasecountry", "country"],
    "format": ["media", "releaseformat", "format"],
    "file_format": ["~format", "media"],
    "catalognumber": ["catalognumber", "catalognum"],
    "bits_per_sample": ["~bits_per_sample", "bitspersample"],
    "sample_rate": ["~sample_rate", "samplerate"],
    "channels": ["~channels"],
    "releasedate": ["date", "releasedate", "originaldate"],
    "label": ["label", "publisher"],
    "year": ["date", "year"],
    "originalyear": ["originalyear", "originaldate"],
    "primaryreleasetype": ["~primaryreleasetype"],
    "discsubtitle": ["discsubtitle"],
    "bitstream_codec": ["bitstream_codec"]
}))

# Compiled regex patterns
_RE_TRAILING_BRACKET = re.compile(r'\s*\[[^\]]*\]\s*$')
_RE_SIZE_FROM_TEXT = re.compile(r'(?<!\d)(7|10|12)\s*(?:[""]|-?inch|in\.?)?', re.I)

# Vinyl size detection mapping
MEDIA_SIZE_MAPPING = {
    '7" vinyl': "7", '10" vinyl': "10", '12" vinyl': "12",
    '7"': "7", '10"': "10", '12"': "12",
    '7-inch': "7", '10-inch': "10", '12-inch': "12",
    'vinyl': None, 'lp': None,
}

# Variable definitions with descriptions
VARIABLES_INFO = {
    "releasecountry": {"desc": "Release country", "example": "US, UK, Japan"},
    "format": {"desc": "Format/media type", "example": "FLAC, MP3, CD"},
    "file_format": {"desc": "File format", "example": "FLAC, MP3, AAC"},
    "catalognumber": {"desc": "Catalog number", "example": "ABC-123, TOCP-12345"},
    "bits_per_sample": {"desc": "Bit depth", "example": "16, 24, 32"},
    "sample_rate": {"desc": "Sample rate", "example": "44100, 48000, 96000"},
    "channels": {"desc": "Audio channels (raw)", "example": "1, 2, 6, 8"},
    "channelconfig": {"desc": "Channel configuration", "example": "Mono, Stereo, 5.1, 7.1"},
    "releasedate": {"desc": "Release date", "example": "2023-01-15, 2023"},
    "year": {"desc": "Release year", "example": "2023, 1995"},
    "originalyear": {"desc": "Original release year", "example": "1967, 2001"},
    "label": {"desc": "Record label", "example": "Warner, Sony Music"},
    "formatsize": {"desc": "Vinyl size only", "example": "12\", 7\", 10\""},
    "mediatype": {"desc": "Media type", "example": "Vinyl, CD, Digital"},
    "recordtype": {"desc": "Release type", "example": "EP, LP, Single"},
    "specialtype": {"desc": "Special editions", "example": "Promo, WL, TP, Ltd"},
    "discsubtitle": {"desc": "Disc subtitle (multidisc)", "example": "Act I, Disc 2"},
    "bitstream_codec": {"desc": "Bitstream codec in lossless", "example": "DTS, Dolby Digital, PCM"}
}

def _get_metadata_value(metadata, key, default=""):
    """Get metadata value safely with type checking"""
    try:
        value = metadata.get(key)
        if value is None:
            return default
        return str(value).strip() if isinstance(value, (str, int, float)) else default
    except (AttributeError, TypeError):
        return default

def _infer_size_from_text(media_val, album_val=""):
    """Extract vinyl size from text with error handling"""
    try:
        for text in [media_val, album_val]:
            if text:
                match = _RE_SIZE_FROM_TEXT.search(text)
                if match:
                    return match.group(1)
        return ""
    except (AttributeError, TypeError):
        return ""

def _map_media_to_size(media_val):
    """Map media value to vinyl size with fallback"""
    try:
        media_lower = media_val.lower().strip()
        for key, value in MEDIA_SIZE_MAPPING.items():
            if key in media_lower:
                return value or _infer_size_from_text(media_val)
        return _infer_size_from_text(media_val)
    except (AttributeError, TypeError):
        return ""

def _detect_vinyl_format_size(metadata):
    """Detect vinyl format size only"""
    media = _get_metadata_value(metadata, "media")
    album = _get_metadata_value(metadata, "album")
    
    if "vinyl" not in media.lower():
        return ""
    
    size = _map_media_to_size(media)
    if not size and media.lower().strip() == "vinyl":
        size = _infer_size_from_text(media, album)
    
    return f'{size}"' if size else ""

def _detect_media_type(metadata):
    """Detect media type with fallback handling"""
    media = _get_metadata_value(metadata, "media").lower()
    
    if "vinyl" in media:
        return "Vinyl"
    elif "cd" in media:
        return "CD"
    elif "digital" in media or "download" in media:
        return "Digital"
    elif media:
        return media.title()
    
    return ""

def _detect_record_type(metadata):
    """Detect record type from release metadata"""
    release_type = _get_metadata_value(metadata, "~primaryreleasetype").lower()
    
    type_mapping = {
        "ep": "EP",
        "single": "Single", 
        "album": "LP"
    }
    
    return type_mapping.get(release_type, release_type.title() if release_type else "")

def _detect_special_type(metadata):
    """Detect special editions with keyword matching"""
    album = _get_metadata_value(metadata, "album").lower()
    comment = _get_metadata_value(metadata, "comment").lower()
    search_text = f"{album} {comment}"

    special_types = [
        (("promo", "promotional"), "Promo"),
        (("white label", "wl"), "WL"),
        (("test pressing", "tp", "test press"), "TP"),
        (("advance", "advanced"), "Advance"),
        (("demo", "demonstration"), "Demo"),
        (("limited edition", "ltd", "limited"), "Ltd")
    ]

    for terms, result in special_types:
        if any(term in search_text for term in terms):
            return result

    return ""

def _detect_channel_config(metadata):
    """Convert channel count to friendly configuration name"""
    channels = _get_metadata_value(metadata, "~channels")

    if not channels:
        return ""

    try:
        # Convert to string and clean up
        channels_str = str(channels).strip()

        # Handle numeric channel counts
        channel_mapping = {
            "1": "Mono",
            "2": "Stereo",
            "3": "3.0",
            "4": "4.0",
            "5": "5.0",
            "6": "5.1",
            "7": "6.1",
            "8": "7.1",
            "10": "7.1.2",
            "12": "7.1.4"
        }

        # Return mapped value if found
        if channels_str in channel_mapping:
            return channel_mapping[channels_str]

        # If already in format like "5.1", return as-is
        if "." in channels_str:
            return channels_str

        # Otherwise return the number with "ch" suffix
        return f"{channels_str}ch"

    except Exception:
        return ""

def _ep_already_present(original_value):
    """Check if EP is already present in the title"""
    try:
        if not original_value:
            return False

        # Check for EP at the end of the title (most common case)
        if original_value.strip().upper().endswith(" EP"):
            return True

        # Check for EP in brackets at the end
        if original_value.strip().upper().endswith("[EP]") or original_value.strip().upper().endswith("(EP)"):
            return True

        # Check if title contains " EP " or ends with " EP"
        upper_value = original_value.upper()
        return " EP " in upper_value or upper_value.endswith(" EP")
    except Exception:
        return False

def get_preview_examples():
    """Get standard preview examples - single source of truth for all preview displays"""
    return [
        {
            "label": "Vinyl EP (24/192 stereo)",
            "title": "Kind of Blue",
            "metadata": {
                "releasecountry": "US", "media": "12\" Vinyl", "~format": "FLAC",
                "catalognumber": "ABC-123", "~bits_per_sample": "24", "~sample_rate": "192000",
                "~channels": "2", "date": "2023-05-15", "year": "2023", "label": "Blue Note Records",
                "~primaryreleasetype": "ep", "album": "Kind of Blue EP (Promo)",
                "title": "So What", "comment": "Promotional White Label Test Pressing"
            }
        },
        {
            "label": "CD Album (16/44 stereo)",
            "title": "Nevermind",
            "metadata": {
                "releasecountry": "Japan", "media": "CD", "~format": "FLAC",
                "catalognumber": "TOCP-50001", "~bits_per_sample": "16", "~sample_rate": "44100",
                "~channels": "2", "date": "1995-03-20", "year": "1995", "label": "Sony Music",
                "~primaryreleasetype": "album", "album": "Nevermind",
                "title": "Smells Like Teen Spirit", "comment": "SHM-CD Remaster"
            }
        },
        {
            "label": "Digital Album (24/96 stereo)",
            "title": "Random Access Memories",
            "metadata": {
                "releasecountry": "XW", "media": "Digital Media", "~format": "FLAC",
                "catalognumber": "", "~bits_per_sample": "24", "~sample_rate": "96000",
                "~channels": "2", "date": "2020-06-15", "year": "2020", "label": "Def Jam",
                "~primaryreleasetype": "album", "album": "Random Access Memories",
                "title": "Get Lucky", "comment": ""
            }
        },
        {
            "label": "DSF Hi-Res (DSD64 stereo)",
            "title": "Time Out",
            "metadata": {
                "releasecountry": "US", "media": "Digital Media", "~format": "DSF",
                "catalognumber": "COL-8192", "~bits_per_sample": "1", "~sample_rate": "2822400",
                "~channels": "2", "date": "2015-08-10", "year": "2015", "originalyear": "1959", "label": "Columbia",
                "~primaryreleasetype": "album", "album": "Time Out",
                "title": "Take Five", "comment": "DSD64 Remaster"
            }
        },
        {
            "label": "SACD Classical (24/88 4.0ch)",
            "title": "Symphony No. 9",
            "metadata": {
                "releasecountry": "DE", "media": "SACD", "~format": "FLAC",
                "catalognumber": "DG-4797090", "~bits_per_sample": "24", "~sample_rate": "88200",
                "~channels": "4", "date": "2010-03-15", "year": "2010", "originalyear": "1824", "label": "Deutsche Grammophon",
                "~primaryreleasetype": "album", "album": "Beethoven: Symphony No. 9",
                "title": "IV. Finale: Ode to Joy", "comment": "Quadraphonic Mix"
            }
        },
        {
            "label": "Multichannel (24/96 5.1ch)",
            "title": "The Dark Side of the Moon",
            "metadata": {
                "releasecountry": "US", "media": "Blu-ray", "~format": "FLAC",
                "catalognumber": "BDA-96024", "~bits_per_sample": "24", "~sample_rate": "96000",
                "~channels": "6", "date": "2018-11-20", "year": "2018", "originalyear": "1973", "label": "Warner",
                "~primaryreleasetype": "album", "album": "The Dark Side of the Moon",
                "title": "Time", "comment": "Surround Sound Mix"
            }
        }
    ]

class FormulaRenderer:
    """Handles parsing and rendering of formula DSL with optimizations"""
    
    def __init__(self, metadata, key_aliases=None):
        self.metadata = metadata
        self.key_aliases = key_aliases or {}
        self._value_cache = {}
    
    def resolve_metadata_value(self, key):
        """Resolve metadata value using key aliases with caching"""
        if key in self._value_cache:
            return self._value_cache[key]
        
        computed_vars = {
            "formatsize": lambda: _detect_vinyl_format_size(self.metadata),
            "mediatype": lambda: _detect_media_type(self.metadata),
            "recordtype": lambda: _detect_record_type(self.metadata),
            "specialtype": lambda: _detect_special_type(self.metadata),
            "channelconfig": lambda: _detect_channel_config(self.metadata)
        }
        
        if key in computed_vars:
            result = computed_vars[key]()
            self._value_cache[key] = result
            return result
        
        aliases = self.key_aliases.get(key, [key])
        for alias in aliases:
            value = self.metadata.get(alias)
            if value:
                result = str(value).strip()
                self._value_cache[key] = result
                return result
        
        self._value_cache[key] = ""
        return ""
    
    def apply_transform(self, value, transform):
        """Apply transforms with error handling"""
        if not value:
            return ""
        
        try:
            if transform.startswith("[:") and transform.endswith("]"):
                slice_end = int(transform[2:-1])
                return value[:slice_end]
            elif transform.startswith(":"):
                slice_end = int(transform[1:])
                return value[:slice_end]
            elif transform == "upper":
                return value.upper()
            elif transform == "lower":
                return value.lower()
            elif transform == "title":
                return value.title()
            elif transform == "digits":
                return re.sub(r'[^\d]', '', value)
            elif transform == "khz":
                # Smart sample rate formatting: 44100 -> 44, 48000 -> 48, 96000 -> 96, 192000 -> 192
                return self._format_sample_rate_khz(value)
        except (ValueError, IndexError, TypeError):
            pass
        
        return value
    
    def _format_sample_rate_khz(self, value):
        """Smart sample rate formatting for kHz display"""
        try:
            # Extract numeric part
            numeric_str = re.sub(r'[^\d]', '', str(value))
            if not numeric_str:
                return value
                
            rate = int(numeric_str)
            
            # Convert to kHz and format intelligently
            if rate >= 1000:
                khz = rate // 1000
                remainder = rate % 1000
                
                # For clean kHz values (44100 -> 44, 48000 -> 48, 96000 -> 96)
                if remainder == 0:
                    return str(khz)
                # For rates like 44100, 48000 where remainder is just 100, 000 etc
                elif remainder <= 100:
                    return str(khz)
                # For other cases, show decimal (like 22050 -> 22.05, 88200 -> 88.2)
                else:
                    khz_decimal = rate / 1000.0
                    if khz_decimal == int(khz_decimal):
                        return str(int(khz_decimal))
                    else:
                        return f"{khz_decimal:.1f}".rstrip('0').rstrip('.')
            else:
                # For rates under 1000Hz, just return as-is
                return str(rate)
                
        except (ValueError, TypeError):
            # Fallback: just take first few significant characters
            clean_value = str(value)
            if len(clean_value) >= 5:
                return clean_value[:3]  # 192000 -> 192, 96000 -> 96 (fallback only)
            return clean_value
    
    def parse_variable(self, var_expr):
        """Parse variable expressions with improved error handling"""
        try:
            var_expr = var_expr.strip('<>')
            
            if '|' in var_expr:
                var_name, transform = var_expr.split('|', 1)
                value = self.resolve_metadata_value(var_name.strip())
                return self.apply_transform(value, transform.strip())
            elif '[' in var_expr and ']' in var_expr:
                bracket_start = var_expr.find('[')
                var_name = var_expr[:bracket_start]
                slice_part = var_expr[bracket_start:]
                value = self.resolve_metadata_value(var_name.strip())
                return self.apply_transform(value, slice_part)
            elif ':' in var_expr and not var_expr.startswith(':'):
                var_name, slice_part = var_expr.split(':', 1)
                value = self.resolve_metadata_value(var_name.strip())
                return self.apply_transform(value, slice_part)
            else:
                return self.resolve_metadata_value(var_expr)
        except Exception:
            return ""
    
    def render_formula(self, formula):
        """Render formula with optimized processing"""
        if not formula:
            return ""
        
        result = formula
        
        def process_group(match):
            try:
                group_content = match.group(1)
                group_rendered = re.sub(r'<([^>]+)>', 
                                     lambda m: self.parse_variable(m.group(0)), 
                                     group_content)
                
                group_rendered = re.sub(r'\s+', ' ', group_rendered).strip()
                group_rendered = re.sub(r'^[-\s]+|[-\s]+$', '', group_rendered)
                group_rendered = re.sub(r'\s*-\s*$|^\s*-\s*', '', group_rendered)
                
                return f"[{group_rendered}]" if group_rendered else ""
            except Exception:
                return ""
        
        pattern = r'\[([^\[\]]*(?:<[^>]*>[^\[\]]*)*)\]'
        result = re.sub(pattern, process_group, result)
        
        result = re.sub(r'<([^>]+)>', 
                       lambda m: self.parse_variable(m.group(0)), 
                       result)
        
        return re.sub(r'\s+', ' ', result).rstrip()

class TemplateEditorDialog(QtWidgets.QDialog):
    """Dialog for creating/editing formula templates"""

    def __init__(self, template_data=None, parent=None):
        super().__init__(parent)
        self.template_data = template_data or {}
        self.setWindowTitle("Edit Template" if template_data else "New Template")
        self.setMinimumSize(800, 650)
        self.create_ui()

    def create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Template name
        layout.addWidget(QtWidgets.QLabel("Template Name:"))
        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setText(self.template_data.get("name", ""))
        self.name_input.setPlaceholderText("e.g., My Custom Format")
        layout.addWidget(self.name_input)

        # Template formula
        layout.addWidget(QtWidgets.QLabel("Formula Pattern:"))
        self.formula_input = QtWidgets.QPlainTextEdit()
        self.formula_input.setPlainText(self.template_data.get("formula", ""))
        self.formula_input.setPlaceholderText("e.g., [<releasecountry> <format>] [<bits_per_sample>-<sample_rate|khz>]")
        self.formula_input.setMinimumHeight(60)
        self.formula_input.setMaximumHeight(80)
        self.formula_input.setStyleSheet("font-family: 'Courier New', monospace; font-size: 12px;")
        layout.addWidget(self.formula_input)

        # Available variables with click-to-copy buttons
        variables_group = QtWidgets.QGroupBox("Available Variables (click to copy)")
        variables_outer_layout = QtWidgets.QVBoxLayout(variables_group)

        # Description
        desc_label = QtWidgets.QLabel(
            "<b>Click any variable below to copy it to clipboard, then paste into your formula.</b><br>"
            "Use angle brackets &lt;variable&gt; for metadata. Use square brackets [group] for conditional groups."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 10px; margin-bottom: 8px; background-color: palette(base); color: palette(text); padding: 8px; border-radius: 4px;")
        variables_outer_layout.addWidget(desc_label)

        # Scroll area for variables
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(200)
        scroll_area.setMaximumHeight(250)

        scroll_content = QtWidgets.QWidget()
        variables_layout = QtWidgets.QVBoxLayout(scroll_content)

        # Clickable variable buttons in grid
        button_layout = QtWidgets.QGridLayout()
        button_layout.setSpacing(6)

        self.variable_buttons = {}
        row, col = 0, 0
        for var_name, info in VARIABLES_INFO.items():
            btn = QtWidgets.QPushButton(f"<{var_name}>")
            btn.setToolTip(f"{info['desc']}\nExamples: {info['example']}\nClick to copy to clipboard")
            btn.clicked.connect(lambda checked, v=var_name: self.copy_variable(v))
            btn.setStyleSheet("""
                QPushButton {
                    text-align: center;
                    padding: 6px 8px;
                    font-size: 10px;
                    font-family: monospace;
                    border-radius: 4px;
                    min-width: 120px;
                }
            """)
            button_layout.addWidget(btn, row, col)
            self.variable_buttons[var_name] = btn

            col += 1
            if col > 3:
                col = 0
                row += 1

        variables_layout.addLayout(button_layout)

        scroll_area.setWidget(scroll_content)
        variables_outer_layout.addWidget(scroll_area)

        # Variable Enhancers guide
        enhancers_label = QtWidgets.QLabel(
            "<b>Variable Enhancers:</b><br>"
            "• Slice: <code>&lt;year[:4]&gt;</code> = first 4 characters (e.g., '2023')<br>"
            "• Upper: <code>&lt;format|upper&gt;</code> = FLAC<br>"
            "• Lower: <code>&lt;format|lower&gt;</code> = flac<br>"
            "• Title: <code>&lt;format|title&gt;</code> = Flac<br>"
            "• Digits: <code>&lt;sample_rate|digits&gt;</code> = extract numbers only<br>"
            "• kHz: <code>&lt;sample_rate|khz&gt;</code> = smart kHz (192000 → 192, 44100 → 44)"
        )
        enhancers_label.setWordWrap(True)
        enhancers_label.setTextFormat(Qt.RichText)
        enhancers_label.setStyleSheet("font-size: 10px; margin-top: 8px; padding: 8px; background-color: palette(midlight); border-radius: 4px;")
        variables_outer_layout.addWidget(enhancers_label)

        layout.addWidget(variables_group)

        # Preview
        preview_group = QtWidgets.QGroupBox("Preview Example")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)
        self.preview_label = QtWidgets.QTextEdit()
        self.preview_label.setReadOnly(True)
        self.preview_label.setMaximumHeight(100)
        self.preview_label.setStyleSheet("""
            QTextEdit {
                font-family: 'Courier New', monospace;
                padding: 8px;
            }
        """)
        preview_layout.addWidget(self.preview_label)
        layout.addWidget(preview_group)

        # Connect signals for live preview
        self.formula_input.textChanged.connect(self.update_preview)

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
            clipboard.setText(f"<{var_name}>")

            # Show temporary tooltip
            btn = self.variable_buttons[var_name]
            QtWidgets.QToolTip.showText(
                btn.mapToGlobal(btn.rect().center()),
                f"Copied <{var_name}> to clipboard!",
                btn, btn.rect(), 1500
            )
        except Exception as e:
            log.error(f"Suffix Appender: Error copying variable: {e}")

    def update_preview(self):
        """Update preview with sample data using shared examples"""
        try:
            formula = self.formula_input.toPlainText()
            if not formula:
                self.preview_label.setText("Enter a formula to see preview...")
                return

            try:
                key_aliases = json.loads(config.setting["suffix_appender_key_aliases"])
            except (json.JSONDecodeError, TypeError, KeyError):
                key_aliases = {}

            # Build HTML preview using shared examples
            preview_text = "<div style='line-height: 1.6;'>"

            examples = get_preview_examples()
            for i, example in enumerate(examples):
                result = FormulaRenderer(example["metadata"], key_aliases).render_formula(formula)
                preview_text += f"<b>{example['label']}:</b><br>"
                preview_text += f"&nbsp;&nbsp;'{example['title']}' → '{example['title']}<span style='color: #0066cc;'>{result if result else '(empty)'}</span>'"
                if i < len(examples) - 1:
                    preview_text += "<br><br>"

            preview_text += "</div>"
            self.preview_label.setHtml(preview_text)

        except Exception as e:
            self.preview_label.setText(f"Preview Error: {str(e)}")
            log.error(f"Suffix Appender: Template preview error: {e}")

    def get_template_data(self):
        """Get the template data from inputs"""
        return {
            "name": self.name_input.text().strip(),
            "formula": self.formula_input.toPlainText(),  # Don't strip - leading space is intentional
        }


class TemplateManagerDialog(QtWidgets.QDialog):
    """Dialog for managing formula templates"""

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
            "Create custom formula templates with variables like <releasecountry>, <format>, etc. "
            "Templates can be applied from the right-click menu."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("margin-bottom: 10px;")
        layout.addWidget(desc)

        # Template list
        self.template_list = QtWidgets.QListWidget()
        self.template_list.setMinimumHeight(200)
        layout.addWidget(self.template_list)

        # Template buttons (two rows to avoid overflow)
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

        template_row1 = QtWidgets.QHBoxLayout()
        template_row1.addWidget(self.add_template_btn)
        template_row1.addWidget(self.edit_template_btn)
        template_row1.addWidget(self.delete_template_btn)
        template_row1.addStretch()

        template_row2 = QtWidgets.QHBoxLayout()
        template_row2.addWidget(self.reset_templates_btn)
        template_row2.addWidget(self.export_json_btn)
        template_row2.addWidget(self.import_json_btn)
        template_row2.addStretch()

        template_buttons = QtWidgets.QVBoxLayout()
        template_buttons.setSpacing(4)
        template_buttons.addLayout(template_row1)
        template_buttons.addLayout(template_row2)

        layout.addLayout(template_buttons)

        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_templates(self):
        """Load templates from settings"""
        try:
            self.template_list.clear()
            templates_json = config.setting["suffix_appender_templates"]

            # Parse JSON, fallback to default templates if empty or invalid
            try:
                templates = json.loads(templates_json) if templates_json else []
            except json.JSONDecodeError:
                templates = []

            # If no templates, use defaults
            if not templates:
                templates = DEFAULT_TEMPLATES

            # Sort templates alphabetically by name
            templates = sorted(templates, key=lambda t: t.get("name", "").lower())

            # Populate list
            for template in templates:
                name = template.get("name", "Unnamed")
                self.template_list.addItem(name)
                # Store full template data in item
                item = self.template_list.item(self.template_list.count() - 1)
                item.setData(Qt.UserRole, template)

        except Exception as e:
            log.error(f"Suffix Appender: Error loading templates: {e}")

    def save_templates(self):
        """Save templates to settings and JSON file"""
        try:
            templates = []
            for i in range(self.template_list.count()):
                item = self.template_list.item(i)
                template_data = item.data(Qt.UserRole)
                if template_data:
                    templates.append(template_data)

            # Save to Picard settings (for backward compatibility)
            config.setting["suffix_appender_templates"] = json.dumps(templates)

            # Save to JSON file (primary storage)
            save_templates_to_json(templates)

            log.info(f"Suffix Appender: Saved {len(templates)} templates to settings and JSON file")
        except Exception as e:
            log.error(f"Suffix Appender: Error saving templates: {e}")

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
                item.setData(Qt.UserRole, template_data)

                log.info(f"Suffix Appender: Added template '{template_data['name']}'")
        except Exception as e:
            log.error(f"Suffix Appender: Error adding template: {e}")

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

            template_data = current_item.data(Qt.UserRole)
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
                current_item.setData(Qt.UserRole, new_data)

                log.info(f"Suffix Appender: Updated template '{new_data['name']}'")
        except Exception as e:
            log.error(f"Suffix Appender: Error editing template: {e}")

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
                f"Are you sure you want to delete the template '{template_name}'?\n\n"
                "Note: Restart Picard to update the right-click menu.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                row = self.template_list.row(current_item)
                self.template_list.takeItem(row)
                log.info(f"Suffix Appender: Deleted template '{template_name}'")
        except Exception as e:
            log.error(f"Suffix Appender: Error deleting template: {e}")

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
                    item.setData(Qt.UserRole, template)

                log.info("Suffix Appender: Reset templates to defaults")
        except Exception as e:
            log.error(f"Suffix Appender: Error resetting templates: {e}")

    def export_to_json(self):
        """Export templates to a JSON file"""
        try:
            # Collect all templates
            templates = []
            for i in range(self.template_list.count()):
                item = self.template_list.item(i)
                template_data = item.data(Qt.UserRole)
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
                TEMPLATES_JSON_PATH,  # Default to standard location
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
                log.info(f"Suffix Appender: Exported {len(templates)} templates to {file_path}")

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Export Error",
                f"Failed to export templates:\n{str(e)}"
            )
            log.error(f"Suffix Appender: Error exporting templates: {e}")

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
                if "name" not in template or "formula" not in template:
                    continue
                valid_templates.append(template)

            if not valid_templates:
                QtWidgets.QMessageBox.warning(
                    self, "Invalid File",
                    "No valid templates found in the JSON file.\n\n"
                    "Each template must have 'name' and 'formula' fields."
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
                item.setData(Qt.UserRole, template)

            QtWidgets.QMessageBox.information(
                self, "Import Successful",
                f"Successfully imported {len(valid_templates)} templates from:\n{file_path}\n\n"
                "Note: Changes will take effect after saving and restarting Picard."
            )
            log.info(f"Suffix Appender: Imported {len(valid_templates)} templates from {file_path}")

        except json.JSONDecodeError as e:
            QtWidgets.QMessageBox.critical(
                self, "Invalid JSON",
                f"Failed to parse JSON file:\n{str(e)}"
            )
            log.error(f"Suffix Appender: JSON parse error during import: {e}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Import Error",
                f"Failed to import templates:\n{str(e)}"
            )
            log.error(f"Suffix Appender: Error importing templates: {e}")


class PresetViewDialog(QtWidgets.QDialog):
    """Enhanced preset viewing and management dialog"""
    
    def __init__(self, presets, current_preset, parent=None):
        super().__init__(parent)
        self.presets = presets.copy()
        self.current_preset = current_preset
        self.result_action = None
        self.setWindowTitle("View and Manage Presets")
        self.setMinimumSize(800, 600)
        self.create_ui()
        self.load_preset(current_preset)
    
    def create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Info banner
        info_banner = QtWidgets.QLabel(
            "<b>Note:</b> Changes to presets require Picard restart to appear in right-click menu. "
            "The 'Active Preset' action always uses the currently selected preset without restart."
        )
        info_banner.setWordWrap(True)
        info_banner.setStyleSheet(
            "QLabel { "
            "background-color: palette(alternate-base); "
            "border: 1px solid palette(mid); "
            "border-radius: 4px; "
            "padding: 8px; "
            "margin-bottom: 10px; "
            "font-size: 10px; "
            "color: palette(text); "
            "}"
        )
        layout.addWidget(info_banner)

        # Preset selection
        preset_layout = QtWidgets.QHBoxLayout()
        preset_layout.addWidget(QtWidgets.QLabel("Select Preset:"))

        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.setMinimumWidth(200)
        for name in sorted(self.presets.keys()):
            self.preset_combo.addItem(name)
        preset_layout.addWidget(self.preset_combo)
        
        # Preset management buttons
        self.rename_button = QtWidgets.QPushButton("Rename")
        self.duplicate_button = QtWidgets.QPushButton("Duplicate")
        self.delete_button = QtWidgets.QPushButton("Delete")
        preset_layout.addWidget(self.rename_button)
        preset_layout.addWidget(self.duplicate_button)
        preset_layout.addWidget(self.delete_button)
        preset_layout.addStretch()
        
        layout.addLayout(preset_layout)
        
        # Preset details in tabs
        self.tab_widget = QtWidgets.QTabWidget()
        
        # Formula tab
        formula_tab = QtWidgets.QWidget()
        formula_layout = QtWidgets.QVBoxLayout(formula_tab)
        
        formula_layout.addWidget(QtWidgets.QLabel("Formula:"))
        self.formula_editor = QtWidgets.QPlainTextEdit()
        self.formula_editor.setMinimumHeight(50)
        self.formula_editor.setMaximumHeight(80)
        self.formula_editor.setStyleSheet("font-family: 'Courier New', monospace; font-size: 12px;")
        formula_layout.addWidget(self.formula_editor)
        
        # Add Formula Preview section
        preview_label = QtWidgets.QLabel("Formula Preview:")
        preview_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
        formula_layout.addWidget(preview_label)
        
        self.formula_preview = QtWidgets.QTextEdit()
        self.formula_preview.setReadOnly(True)
        self.formula_preview.setMinimumHeight(50)
        self.formula_preview.setMaximumHeight(80)
        self.formula_preview.setStyleSheet(
            "QTextEdit { font-family: 'Courier New', monospace; font-size: 11px; "
            "padding: 8px; }"
        )
        formula_layout.addWidget(self.formula_preview)
        
        # Variables help with MODIFIERS section in scroll area
        variables_group = QtWidgets.QGroupBox("Available Variables (click to copy)")
        variables_outer_layout = QtWidgets.QVBoxLayout(variables_group)
        
        # Create scroll area for the variables content
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(250)
        scroll_area.setMaximumHeight(300)
        
        # Create widget to hold the scrollable content
        scroll_content = QtWidgets.QWidget()
        variables_layout = QtWidgets.QVBoxLayout(scroll_content)
        
        # Add the detailed MODIFIERS explanation
        modifiers_text = QtWidgets.QLabel()
        modifiers_text.setText(
            "<b>VARIABLES:</b> Use angle brackets around variable names<br>"
            "• <b>&lt;releasecountry&gt;</b> → US, UK, Japan<br>"
            "• <b>&lt;format&gt;</b> → FLAC, MP3, CD<br>"
            "• <b>&lt;bits_per_sample&gt;</b> → 16, 24, 32<br>"
            "• <b>&lt;sample_rate&gt;</b> → 44100, 48000, 96000<br><br>"
            
            "<b>TRANSFORMS:</b> Modify variables with | (pipe) or : (colon)<br>"
            "• <b>&lt;var|upper&gt;</b> → UPPERCASE<br>"
            "• <b>&lt;var|lower&gt;</b> → lowercase<br>"
            "• <b>&lt;var|title&gt;</b> → Title Case<br>"
            "• <b>&lt;var|digits&gt;</b> → numbers only<br>"
            "• <b>&lt;var[:2]&gt;</b> → first 2 characters<br><br>"
            
            "<b>CONDITIONAL GROUPS:</b> Use square brackets [...]<br>"
            "• <b>[&lt;var1&gt; &lt;var2&gt;]</b> → only shows if at least one variable has a value<br>"
            "• <b>[&lt;country&gt; &lt;format&gt;] [&lt;bits&gt;-&lt;rate[:2]&gt;]</b> → [US FLAC] [24-96]<br><br>"
            
            "<b>SMART VARIABLES:</b> Automatic detection<br>"
            "• <b>&lt;formatsize&gt;</b> → 12\", 7\", 10\" (vinyl only)<br>"
            "• <b>&lt;mediatype&gt;</b> → Vinyl, CD, Digital<br>"
            "• <b>&lt;recordtype&gt;</b> → EP, LP, Single<br>"
            "• <b>&lt;specialtype&gt;</b> → Promo, WL, TP, Ltd"
        )
        
        modifiers_text.setStyleSheet(
            "QLabel { "
            "font-size: 10px; "
            "border-radius: 6px; "
            "padding: 12px; "
            "line-height: 1.4; "
            "background-color: palette(base); "
            "color: palette(text); "
            "}"
        )
        modifiers_text.setWordWrap(True)
        variables_layout.addWidget(modifiers_text)
        
        # Clickable variable buttons
        button_group = QtWidgets.QGroupBox("Copy Variables")
        button_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        button_layout = QtWidgets.QGridLayout(button_group)
        button_layout.setSpacing(6)
        
        self.variable_buttons = {}
        row, col = 0, 0
        for var_name, info in VARIABLES_INFO.items():
            btn = QtWidgets.QPushButton(f"<{var_name}>")
            btn.setToolTip(f"{info['desc']}\nExamples: {info['example']}\nClick to copy to clipboard")
            btn.clicked.connect(lambda checked, v=var_name: self.copy_variable(v))
            btn.setStyleSheet("""
                QPushButton {
                    text-align: center;
                    padding: 6px 8px;
                    font-size: 10px;
                    font-family: monospace;
                    border-radius: 4px;
                    min-width: 120px;
                }
            """)
            button_layout.addWidget(btn, row, col)
            self.variable_buttons[var_name] = btn
            
            col += 1
            if col > 3:
                col = 0
                row += 1
        
        variables_layout.addWidget(button_group)
        
        # Set the scroll content and add to scroll area
        scroll_area.setWidget(scroll_content)
        variables_outer_layout.addWidget(scroll_area)
        
        formula_layout.addWidget(variables_group)
        
        self.tab_widget.addTab(formula_tab, "Formula & Variables")
        
        # Preview tab
        preview_tab = QtWidgets.QWidget()
        preview_layout = QtWidgets.QVBoxLayout(preview_tab)
        
        preview_layout.addWidget(QtWidgets.QLabel("Live Preview with Sample Data:"))
        self.preview_text = QtWidgets.QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumHeight(150)
        self.preview_text.setStyleSheet("font-family: monospace;")
        preview_layout.addWidget(self.preview_text)
        
        self.tab_widget.addTab(preview_tab, "Preview")
        
        layout.addWidget(self.tab_widget)
        
        # Action buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        self.apply_button = QtWidgets.QPushButton("Apply to Options")
        self.apply_button.setStyleSheet("font-weight: bold; padding: 8px;")
        
        self.save_button = QtWidgets.QPushButton("Save Changes")
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        
        button_layout.addWidget(self.apply_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Connect signals
        self.preset_combo.currentTextChanged.connect(self.load_preset)
        self.formula_editor.textChanged.connect(self.update_preview)
        self.rename_button.clicked.connect(self.rename_preset)
        self.duplicate_button.clicked.connect(self.duplicate_preset)
        self.delete_button.clicked.connect(self.delete_preset)
        self.apply_button.clicked.connect(self.apply_preset)
        self.save_button.clicked.connect(self.save_changes)
        self.cancel_button.clicked.connect(self.reject)
    
    def copy_variable(self, var_name):
        """Copy variable to clipboard and optionally insert into formula"""
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(f"<{var_name}>")
        
        # Show temporary tooltip
        btn = self.variable_buttons[var_name]
        QtWidgets.QToolTip.showText(btn.mapToGlobal(btn.rect().center()), 
                                   f"Copied <{var_name}> to clipboard!", btn, btn.rect(), 2000)
    
    def load_preset(self, preset_name):
        """Load preset into editor"""
        if preset_name in self.presets:
            formula = self.presets[preset_name]
            self.formula_editor.setPlainText(formula)
            self.update_preview()
            
            # Set combo if different
            if self.preset_combo.currentText() != preset_name:
                self.preset_combo.setCurrentText(preset_name)
    
    def update_preview(self):
        """Update preview with current formula"""
        try:
            formula = self.formula_editor.toPlainText()
            if not formula:
                self.preview_text.setPlainText("Enter a formula to see preview...")
                if hasattr(self, 'formula_preview'):
                    self.formula_preview.setText("Enter a formula to see preview...")
                return

            try:
                key_aliases = json.loads(config.setting["suffix_appender_key_aliases"])
            except (json.JSONDecodeError, TypeError, KeyError):
                key_aliases = {}

            # Sample metadata for vinyl
            vinyl_metadata = {
                "releasecountry": "US", "media": "12\" Vinyl", "~format": "FLAC",
                "catalognumber": "ABC-123", "~bits_per_sample": "24", "~sample_rate": "192000",
                "~channels": "2", "date": "2023-05-15", "year": "2023", "label": "Blue Note Records",
                "~primaryreleasetype": "ep", "album": "Kind of Blue EP (Promo)",
                "title": "So What", "comment": "Promotional White Label Test Pressing"
            }

            # Sample metadata for CD
            cd_metadata = {
                "releasecountry": "Japan", "media": "CD", "~format": "FLAC",
                "catalognumber": "TOCP-50001", "~bits_per_sample": "16", "~sample_rate": "44100",
                "~channels": "2", "date": "1995-03-20", "year": "1995", "label": "Sony Music",
                "~primaryreleasetype": "album", "album": "Nevermind",
                "title": "Smells Like Teen Spirit", "comment": "SHM-CD Remaster"
            }

            # Sample metadata for digital
            digital_metadata = {
                "releasecountry": "XW", "media": "Digital Media", "~format": "FLAC",
                "catalognumber": "", "~bits_per_sample": "24", "~sample_rate": "96000",
                "~channels": "2", "date": "2020-06-15", "year": "2020", "label": "Def Jam",
                "~primaryreleasetype": "album", "album": "Random Access Memories",
                "title": "Get Lucky", "comment": ""
            }

            # Sample metadata for multichannel
            multichannel_metadata = {
                "releasecountry": "US", "media": "Blu-ray", "~format": "FLAC",
                "catalognumber": "BDA-96024", "~bits_per_sample": "24", "~sample_rate": "96000",
                "~channels": "5.1", "date": "2018-11-20", "year": "2018", "originalyear": "1973", "label": "Warner",
                "~primaryreleasetype": "album", "album": "The Dark Side of the Moon",
                "title": "Time", "comment": "Surround Sound Mix"
            }

            vinyl_result = FormulaRenderer(vinyl_metadata, key_aliases).render_formula(formula)
            cd_result = FormulaRenderer(cd_metadata, key_aliases).render_formula(formula)
            digital_result = FormulaRenderer(digital_metadata, key_aliases).render_formula(formula)
            multichannel_result = FormulaRenderer(multichannel_metadata, key_aliases).render_formula(formula)

            # Update the small formula preview (use vinyl for backward compatibility)
            if hasattr(self, 'formula_preview'):
                self.formula_preview.setText(f"• 'Kind of Blue' → 'Kind of Blue{vinyl_result}'\n• 'Nevermind' → 'Nevermind{cd_result}'")

            # Update the full preview text with all four examples
            preview_text = "Examples with different formats:\n\n"

            preview_text += "VINYL EP (24/192 stereo):\n"
            preview_text += f"• Album: 'Kind of Blue' → 'Kind of Blue{vinyl_result}'\n"
            preview_text += f"• Track: 'So What' → 'So What{vinyl_result}'\n\n"

            preview_text += "CD ALBUM (16/44 stereo):\n"
            preview_text += f"• Album: 'Nevermind' → 'Nevermind{cd_result}'\n"
            preview_text += f"• Track: 'Smells Like Teen Spirit' → 'Smells Like Teen Spirit{cd_result}'\n\n"

            preview_text += "DIGITAL ALBUM (24/96 stereo):\n"
            preview_text += f"• Album: 'Random Access Memories' → 'Random Access Memories{digital_result}'\n"
            preview_text += f"• Track: 'Get Lucky' → 'Get Lucky{digital_result}'\n\n"

            preview_text += "MULTICHANNEL (24/96 5.1ch):\n"
            preview_text += f"• Album: 'The Dark Side of the Moon' → 'The Dark Side of the Moon{multichannel_result}'\n"
            preview_text += f"• Track: 'Time' → 'Time{multichannel_result}'\n\n"

            preview_text += "Sample Metadata (Multichannel):\n"
            for key, value in multichannel_metadata.items():
                if value:  # Only show non-empty values
                    preview_text += f"• {key}: {value}\n"

            self.preview_text.setPlainText(preview_text)

        except Exception as e:
            if hasattr(self, 'formula_preview'):
                self.formula_preview.setText(f"Preview Error: {str(e)}")
            self.preview_text.setPlainText(f"Preview Error: {str(e)}")
    
    def rename_preset(self):
        """Rename current preset"""
        current_name = self.preset_combo.currentText()

        # Prevent renaming of built-in presets
        built_in_presets = {
            "None", "Simple Country", "Country + Format", "Country + Vinyl Size",
            "Vinyl Style", "With Special Types", "With Catalog", "Technical Details",
            "Release Info", "Complete", "Format Only", "Remaster Year",
            "SHM & SACD", "Hi-Res", "Country+Size & Resolution"
        }

        if current_name in built_in_presets:
            QtWidgets.QMessageBox.information(self, "Cannot Rename", "Cannot rename built-in presets.")
            return
        
        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "Rename Preset", "New name:", text=current_name
        )
        
        if ok and new_name.strip() and new_name != current_name:
            new_name = new_name.strip()
            if new_name not in self.presets:
                self.presets[new_name] = self.presets.pop(current_name)
                self.refresh_combo()
                self.preset_combo.setCurrentText(new_name)
            else:
                QtWidgets.QMessageBox.warning(self, "Name Exists", "A preset with this name already exists.")
    
    def duplicate_preset(self):
        """Duplicate current preset"""
        current_name = self.preset_combo.currentText()
        formula = self.formula_editor.toPlainText()

        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "Duplicate Preset", "Name for duplicate:", text=f"{current_name} Copy"
        )

        if ok and new_name.strip():
            new_name = new_name.strip()
            if new_name not in self.presets:
                self.presets[new_name] = formula
                self.refresh_combo()
                self.preset_combo.setCurrentText(new_name)

                # Show info about adding to menu
                QtWidgets.QMessageBox.information(
                    self, "Preset Duplicated",
                    f"Preset '{new_name}' created successfully!\n\n"
                    "Click 'Save Changes' to make it permanent.\n"
                    "Restart Picard to add it to the right-click menu."
                )
            else:
                QtWidgets.QMessageBox.warning(self, "Name Exists", "A preset with this name already exists.")
    
    def delete_preset(self):
        """Delete current preset"""
        current_name = self.preset_combo.currentText()

        # Prevent deletion of built-in presets
        built_in_presets = {
            "None", "Simple Country", "Country + Format", "Country + Vinyl Size",
            "Vinyl Style", "With Special Types", "With Catalog", "Technical Details",
            "Release Info", "Complete", "Format Only", "Remaster Year",
            "SHM & SACD", "Hi-Res", "Country+Size & Resolution"
        }

        if current_name in built_in_presets:
            QtWidgets.QMessageBox.information(self, "Cannot Delete", "Cannot delete built-in presets.")
            return

        reply = QtWidgets.QMessageBox.question(
            self, "Delete Preset",
            f"Are you sure you want to delete '{current_name}'?\n\n"
            "Note: You'll need to restart Picard for this change to appear in the right-click menu.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            self.presets.pop(current_name, None)
            self.refresh_combo()
            self.preset_combo.setCurrentIndex(0)

            # Show success message
            QtWidgets.QMessageBox.information(
                self, "Preset Deleted",
                f"Preset '{current_name}' has been deleted.\n\n"
                "Remember to restart Picard to remove it from the right-click menu."
            )
    
    def refresh_combo(self):
        """Refresh preset combo box"""
        current = self.preset_combo.currentText()
        self.preset_combo.clear()
        for name in sorted(self.presets.keys()):
            self.preset_combo.addItem(name)
        
        index = self.preset_combo.findText(current)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
    
    def apply_preset(self):
        """Apply current preset to options"""
        self.result_action = "apply"
        self.accept()
    
    def save_changes(self):
        """Save changes to current preset"""
        current_name = self.preset_combo.currentText()
        if current_name != "None":
            self.presets[current_name] = self.formula_editor.toPlainText()
        self.result_action = "save"

        # Show message about restart
        self._show_restart_message()
        self.accept()

    def _show_restart_message(self):
        """Show message about restarting Picard for menu changes"""
        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setWindowTitle("Restart Required")
        msg.setText("Preset changes saved successfully!")
        msg.setInformativeText(
            "To see your new/modified presets in the right-click menu:\n\n"
            "1. Click OK to close all dialogs\n"
            "2. Close Picard completely\n"
            "3. Restart Picard\n\n"
            "The 'Active Preset' action will work immediately without restart."
        )
        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msg.exec_()

    def get_current_preset_data(self):
        """Get current preset name and formula"""
        return self.preset_combo.currentText(), self.formula_editor.toPlainText()

    def get_presets(self):
        """Get all presets"""
        return self.presets

class DetectionMatrixDialog(QtWidgets.QDialog):
    """Dialog for managing auto-format detection settings"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auto-Format Detection Configuration")
        self.setMinimumSize(700, 500)
        self.create_ui()
        self.load_settings()

    def create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Description
        desc = QtWidgets.QLabel(
            "Configure automatic format detection rules. Enable/disable each rule and customize the wrapper format."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("margin-bottom: 10px;")
        layout.addWidget(desc)

        # Detection Matrix
        detection_group = QtWidgets.QGroupBox("Detection Matrix (Tag is placed right after Album Title)")
        detection_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        detection_layout = QtWidgets.QVBoxLayout(detection_group)

        # Grid for checkboxes, examples, and buttons
        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setColumnStretch(1, 1)

        # Headers
        header_enable = QtWidgets.QLabel("<b>Enable</b>")
        header_example = QtWidgets.QLabel("<b>Example Preview</b>")
        header_button = QtWidgets.QLabel("<b>Wrapper</b>")

        grid_layout.addWidget(header_enable, 0, 0)
        grid_layout.addWidget(header_example, 0, 1)
        grid_layout.addWidget(header_button, 0, 2)

        row = 1

        # EP detection
        self.ep_checkbox = QtWidgets.QCheckBox("EP")
        ep_example = QtWidgets.QLabel("\"Kind of Blue\" → \"Kind of Blue EP\"")
        ep_example.setStyleSheet("padding: 4px; border-radius: 3px; font-size: 10px;")
        self.ep_wrapper_button = QtWidgets.QPushButton("Change Wrapper...")
        self.ep_wrapper_button.setMinimumWidth(140)
        self.ep_wrapper_button.setMaximumWidth(160)
        self.ep_wrapper_button.clicked.connect(lambda: self.open_wrapper_dialog("EP"))

        grid_layout.addWidget(self.ep_checkbox, row, 0)
        grid_layout.addWidget(ep_example, row, 1)
        grid_layout.addWidget(self.ep_wrapper_button, row, 2)
        row += 1

        # Single detection
        self.single_checkbox = QtWidgets.QCheckBox("Single")
        single_example = QtWidgets.QLabel("\"Hey Jude\" → \"Hey Jude [Single]\"")
        single_example.setStyleSheet("padding: 4px; border-radius: 3px; font-size: 10px;")
        self.single_wrapper_button = QtWidgets.QPushButton("Change Wrapper...")
        self.single_wrapper_button.setMinimumWidth(140)
        self.single_wrapper_button.setMaximumWidth(160)
        self.single_wrapper_button.clicked.connect(lambda: self.open_wrapper_dialog("Single"))

        grid_layout.addWidget(self.single_checkbox, row, 0)
        grid_layout.addWidget(single_example, row, 1)
        grid_layout.addWidget(self.single_wrapper_button, row, 2)
        row += 1

        # CD detection
        self.cd_checkbox = QtWidgets.QCheckBox("CD")
        cd_example = QtWidgets.QLabel("\"Abbey Road\" → \"Abbey Road [CD]\"")
        cd_example.setStyleSheet("padding: 4px; border-radius: 3px; font-size: 10px;")
        self.cd_wrapper_button = QtWidgets.QPushButton("Change Wrapper...")
        self.cd_wrapper_button.setMinimumWidth(140)
        self.cd_wrapper_button.setMaximumWidth(160)
        self.cd_wrapper_button.clicked.connect(lambda: self.open_wrapper_dialog("CD"))

        grid_layout.addWidget(self.cd_checkbox, row, 0)
        grid_layout.addWidget(cd_example, row, 1)
        grid_layout.addWidget(self.cd_wrapper_button, row, 2)
        row += 1

        # Vinyl detection
        self.vinyl_checkbox = QtWidgets.QCheckBox("Vinyl")
        vinyl_example = QtWidgets.QLabel("\"Dark Side\" → \"Dark Side [Vinyl]\"")
        vinyl_example.setStyleSheet("padding: 4px; border-radius: 3px; font-size: 10px;")
        self.vinyl_wrapper_button = QtWidgets.QPushButton("Change Wrapper...")
        self.vinyl_wrapper_button.setMinimumWidth(140)
        self.vinyl_wrapper_button.setMaximumWidth(160)
        self.vinyl_wrapper_button.clicked.connect(lambda: self.open_wrapper_dialog("Vinyl"))

        grid_layout.addWidget(self.vinyl_checkbox, row, 0)
        grid_layout.addWidget(vinyl_example, row, 1)
        grid_layout.addWidget(self.vinyl_wrapper_button, row, 2)

        detection_layout.addLayout(grid_layout)
        layout.addWidget(detection_group)

        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def open_wrapper_dialog(self, detection_type):
        """Open wrapper selection dialog"""
        setting_key = f"suffix_appender_{detection_type.lower()}_wrapper"
        try:
            current_wrapper = config.setting[setting_key] if setting_key in config.setting else ""
        except KeyError:
            current_wrapper = ""

        dialog = WrapperSelectionDialog(current_wrapper, detection_type, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_wrapper = dialog.get_wrapper()
            config.setting[setting_key] = new_wrapper

    def load_settings(self):
        """Load settings from config"""
        try:
            self.ep_checkbox.setChecked(config.setting["suffix_appender_add_ep"])
            self.single_checkbox.setChecked(config.setting["suffix_appender_add_single"])
            self.cd_checkbox.setChecked(config.setting["suffix_appender_add_cd"])
            self.vinyl_checkbox.setChecked(config.setting["suffix_appender_add_vinyl"])
        except Exception as e:
            log.error(f"Suffix Appender: Error loading detection settings: {e}")

    def save_settings(self):
        """Save settings to config"""
        try:
            config.setting["suffix_appender_add_ep"] = self.ep_checkbox.isChecked()
            config.setting["suffix_appender_add_single"] = self.single_checkbox.isChecked()
            config.setting["suffix_appender_add_cd"] = self.cd_checkbox.isChecked()
            config.setting["suffix_appender_add_vinyl"] = self.vinyl_checkbox.isChecked()
        except Exception as e:
            log.error(f"Suffix Appender: Error saving detection settings: {e}")


class WrapperSelectionDialog(QtWidgets.QDialog):
    """Dialog for selecting wrapper format"""
    
    WRAPPER_OPTIONS = [
        ("Brackets", "[]"),
        ("Parentheses", "()"),
        ("Angle Brackets", "<>"),
        ("Braces", "{}"),
        ("Dash Space", "- "),
        ("Pipe Space", "| "),
        ("Space Only", " "),
        ("No Wrapper", "")
    ]
    
    def __init__(self, current_wrapper, detection_type, parent=None):
        super().__init__(parent)
        self.current_wrapper = current_wrapper
        self.detection_type = detection_type
        self.setWindowTitle(f"Select {detection_type} Wrapper")
        self.setMinimumSize(300, 400)
        self.create_ui()
    
    def create_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        
        layout.addWidget(QtWidgets.QLabel(f"Select wrapper format for {self.detection_type} detection:"))
        
        self.wrapper_group = QtWidgets.QButtonGroup()
        
        for name, wrapper in self.WRAPPER_OPTIONS:
            radio = QtWidgets.QRadioButton(f"{name}: '{wrapper}{self.detection_type}{wrapper}'" if wrapper else f"{name}: ' {self.detection_type}'")
            self.wrapper_group.addButton(radio)
            layout.addWidget(radio)
            
            if wrapper == self.current_wrapper or (not wrapper and not self.current_wrapper):
                radio.setChecked(True)
        
        # Custom wrapper
        layout.addWidget(QtWidgets.QLabel("Or enter custom wrapper:"))
        self.custom_wrapper = QtWidgets.QLineEdit()
        self.custom_wrapper.setPlaceholderText("e.g., --> <-- for -->EP<--")
        layout.addWidget(self.custom_wrapper)
        
        # Dialog buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_wrapper(self):
        """Get selected wrapper"""
        custom = self.custom_wrapper.text().strip()
        if custom:
            return custom
        
        checked_button = self.wrapper_group.checkedButton()
        if checked_button:
            text = checked_button.text()
            for name, wrapper in self.WRAPPER_OPTIONS:
                if text.startswith(name):
                    return wrapper

        return ""

# Template JSON file location
import os
# Store in a separate preferences/json folder to preserve templates across plugin updates
JSON_PREFERENCES_DIR = os.path.expanduser("~/Library/Preferences/MusicBrainz/Picard/json")
TEMPLATES_JSON_PATH = os.path.join(JSON_PREFERENCES_DIR, "suffix_appender_templates.json")

def load_templates_from_sources():
    """
    Load templates with priority: JSON file > Picard settings > DEFAULT_TEMPLATES

    Returns:
        list: List of template dictionaries with 'name' and 'formula' keys
    """
    templates = None
    source = "defaults"

    # Priority 1: Try loading from JSON file
    if os.path.exists(TEMPLATES_JSON_PATH):
        try:
            import codecs
            with codecs.open(TEMPLATES_JSON_PATH, 'r', encoding='utf-8') as f:
                templates = json.load(f)

            # Validate structure
            if isinstance(templates, list) and len(templates) > 0:
                # Validate each template has required fields
                valid = all(isinstance(t, dict) and "name" in t and "formula" in t for t in templates)
                if valid:
                    source = "JSON file"
                    log.info(f"Suffix Appender: Loaded {len(templates)} templates from JSON file: {TEMPLATES_JSON_PATH}")
                else:
                    templates = None
                    log.warning(f"Suffix Appender: JSON file has invalid template structure, falling back")
            else:
                templates = None
                log.warning(f"Suffix Appender: JSON file is empty or invalid, falling back")
        except Exception as e:
            templates = None
            log.warning(f"Suffix Appender: Failed to load JSON file: {e}, falling back")

    # Priority 2: Try loading from Picard settings
    if templates is None:
        try:
            templates_json = config.setting.get("suffix_appender_templates", "")
            if templates_json:
                templates = json.loads(templates_json)
                if isinstance(templates, list) and len(templates) > 0:
                    source = "Picard settings"
                    log.info(f"Suffix Appender: Loaded {len(templates)} templates from Picard settings")
                else:
                    templates = None
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            templates = None
            log.warning(f"Suffix Appender: Failed to parse templates from settings: {e}")

    # Priority 3: Use DEFAULT_TEMPLATES
    if templates is None or len(templates) == 0:
        templates = DEFAULT_TEMPLATES
        source = "defaults"
        log.info(f"Suffix Appender: Using default templates ({len(templates)} templates)")

    return templates

def save_templates_to_json(templates):
    """
    Save templates to the JSON file location

    Args:
        templates (list): List of template dictionaries

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        json_dir = os.path.dirname(TEMPLATES_JSON_PATH)
        if not os.path.exists(json_dir):
            os.makedirs(json_dir)

        # Write JSON file
        import codecs
        with codecs.open(TEMPLATES_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(templates, f, indent=2, ensure_ascii=False)

        log.info(f"Suffix Appender: Saved {len(templates)} templates to JSON file: {TEMPLATES_JSON_PATH}")
        return True
    except Exception as e:
        log.error(f"Suffix Appender: Failed to save templates to JSON file: {e}")
        return False

# Default templates (similar to PRESETS but in template format)
DEFAULT_TEMPLATES = [
    {"name": "Country", "formula": " [<releasecountry>]"},
    {"name": "Country+Size", "formula": " [<releasecountry> <formatsize>]"},
    {"name": "Year Country Cat Format | Hi Res", "formula": " [<year[:4]> <releasecountry> <catalognumber> <format>] [<bits_per_sample>-<sample_rate|khz>]"},
    {"name": "Multichannel", "formula": " [<format> <channels>ch]"},
    {"name": "Remaster Year", "formula": " [<year[:4]>]"},
    {"name": "SACD Hi Res", "formula": " [<format>] [<bits_per_sample>-<sample_rate|khz>]"},
    {"name": "Format Hi-Res (Non Vinyl)", "formula": " [<format>] [<bits_per_sample>-<sample_rate|khz>]"},
    {"name": "Country+Size & Resolution", "formula": " [<releasecountry> <formatsize>] [<bits_per_sample>-<sample_rate|khz>]"},
    {"name": "Year Country", "formula": " [<year[:4]> <releasecountry>]"},
    {"name": "Japanese CD", "formula": " [<releasecountry> JP CD]"},
    {"name": "Japanese Special Format", "formula": " [<releasecountry> JP <format>]"},
    {"name": "MFSL | AF", "formula": " [<label|mfsl_af>]"}
]

class SuffixOptionsPage(OptionsPage):
    NAME = "suffix_appender"
    TITLE = "Suffix Appender"
    PARENT = "plugins"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._preview_timer = None
        self.templates_changed = False  # Track if templates were modified
        try:
            self.create_ui()
        except Exception as e:
            log.error(f"Suffix Appender: UI creation failed: {e}")
            self.show_error("Failed to create options interface")
    
    def create_ui(self):
        """Create simplified UI"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        self._add_header(layout)

        # Template selection and management
        self._add_template_section(layout)

        # Preview section (read-only)
        self._add_preview_section(layout)

        # Target fields
        self._add_target_section(layout)

        # Options
        self._add_options_section(layout)

        # Connect signals
        self._connect_signals()
        
        layout.addStretch()
    
    def _add_header(self, layout):
        """Add header section"""
        title = QtWidgets.QLabel("Suffix Appender")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(title)
        
        description = QtWidgets.QLabel(
            "Add custom information to your music files using formula-based suffixes. "
            "Use the context menu 'Append Suffix' to apply to selected albums/tracks."
        )
        description.setStyleSheet("font-size: 11px; margin-bottom: 10px;")
        description.setWordWrap(True)
        layout.addWidget(description)
    
    def _add_template_section(self, layout):
        """Add template list and management section"""
        template_group = QtWidgets.QGroupBox("Templates")
        template_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        template_layout = QtWidgets.QVBoxLayout(template_group)

        # Template list
        self.template_list = QtWidgets.QListWidget()
        self.template_list.setMinimumHeight(150)
        self.template_list.setMaximumHeight(200)
        template_layout.addWidget(self.template_list)

        # Management buttons
        buttons_layout = QtWidgets.QHBoxLayout()

        self.add_template_btn = QtWidgets.QPushButton("Add Template")
        self.edit_template_btn = QtWidgets.QPushButton("Edit")
        self.delete_template_btn = QtWidgets.QPushButton("Delete")
        self.reset_templates_btn = QtWidgets.QPushButton("Reset to Defaults")
        self.export_json_btn = QtWidgets.QPushButton("Export JSON")
        self.import_json_btn = QtWidgets.QPushButton("Import JSON")

        buttons_layout.addWidget(self.add_template_btn)
        buttons_layout.addWidget(self.edit_template_btn)
        buttons_layout.addWidget(self.delete_template_btn)
        buttons_layout.addWidget(self.reset_templates_btn)
        buttons_layout.addWidget(self.export_json_btn)
        buttons_layout.addWidget(self.import_json_btn)
        buttons_layout.addStretch()

        template_layout.addLayout(buttons_layout)

        # Auto-detection button
        self.manage_detection_btn = QtWidgets.QPushButton("Configure Auto-Detection...")
        self.manage_detection_btn.setMinimumHeight(35)
        self.manage_detection_btn.setToolTip("Configure auto-format detection rules (EP, Single, CD, Vinyl)")
        template_layout.addWidget(self.manage_detection_btn)

        layout.addWidget(template_group)

        # Load templates into list
        self.load_templates_to_list()
    
    
    def _add_preview_section(self, layout):
        """Add unified Live Preview section"""
        preview_group = QtWidgets.QGroupBox("Live Preview")
        preview_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)
        
        self.preview_text = QtWidgets.QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMinimumHeight(120)
        self.preview_text.setMaximumHeight(180)
        self.preview_text.setStyleSheet(
            "QTextEdit { font-family: 'Courier New', monospace; font-size: 11px; "
            "padding: 12px; line-height: 1.4; }"
        )
        self.preview_text.setHtml("Select a preset to see preview...")
        
        preview_layout.addWidget(self.preview_text)
        layout.addWidget(preview_group)
    
    
    
    def _add_target_section(self, layout):
        """Add target fields section"""
        target_group = QtWidgets.QGroupBox("Target Fields")
        target_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        target_layout = QtWidgets.QHBoxLayout(target_group)
        
        self.target_album_checkbox = QtWidgets.QCheckBox("Album Title")
        self.target_title_checkbox = QtWidgets.QCheckBox("Track Title")
        self.target_comment_checkbox = QtWidgets.QCheckBox("Comment Field")
        self.target_discsubtitle_checkbox = QtWidgets.QCheckBox("Disc Subtitle")
        self.target_work_checkbox = QtWidgets.QCheckBox("Work")

        target_layout.addWidget(self.target_album_checkbox)
        target_layout.addWidget(self.target_title_checkbox)
        target_layout.addWidget(self.target_comment_checkbox)
        target_layout.addWidget(self.target_discsubtitle_checkbox)
        target_layout.addWidget(self.target_work_checkbox)
        target_layout.addStretch()
        
        layout.addWidget(target_group)
    
    def _add_detection_section(self, layout):
        """Add enhanced detection section"""
        detection_group = QtWidgets.QGroupBox("Auto Format Appender")
        detection_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        
        # Add subtitle
        subtitle = QtWidgets.QLabel("Tag is placed right after original Album Title automatically")
        subtitle.setStyleSheet("font-size: 10px; margin-bottom: 8px;")
        
        detection_layout = QtWidgets.QVBoxLayout(detection_group)
        detection_layout.addWidget(subtitle)
        
        # Grid for checkboxes, examples, and buttons (3 columns)
        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setColumnStretch(1, 1)  # Make example column expandable
        grid_layout.setColumnStretch(2, 0)  # Keep wrapper column fixed but wider
        
        # Headers
        header_checkbox = QtWidgets.QLabel("<b>Enable</b>")
        header_checkbox.setAlignment(Qt.AlignCenter)
        header_example = QtWidgets.QLabel("<b>Example Preview</b>")
        header_example.setAlignment(Qt.AlignCenter)
        header_button = QtWidgets.QLabel("<b>Wrapper</b>")
        header_button.setAlignment(Qt.AlignCenter)
        
        grid_layout.addWidget(header_checkbox, 0, 0)
        grid_layout.addWidget(header_example, 0, 1)
        grid_layout.addWidget(header_button, 0, 2)
        
        # EP Detection
        self.ep_checkbox = QtWidgets.QCheckBox("EP")
        ep_example = QtWidgets.QLabel("\"Kind of Blue\" → \"Kind of Blue EP\"")
        ep_example.setStyleSheet("padding: 4px; border-radius: 3px; font-size: 10px;")
        self.ep_wrapper_button = QtWidgets.QPushButton("Change Wrapper")
        self.ep_wrapper_button.setMinimumWidth(140)
        self.ep_wrapper_button.setMaximumWidth(160)
        
        grid_layout.addWidget(self.ep_checkbox, 1, 0)
        grid_layout.addWidget(ep_example, 1, 1)
        grid_layout.addWidget(self.ep_wrapper_button, 1, 2)
        
        # Single Detection
        self.single_checkbox = QtWidgets.QCheckBox("Single")
        single_example = QtWidgets.QLabel("\"Hey Jude\" → \"Hey Jude [Single]\"")
        single_example.setStyleSheet("padding: 4px; border-radius: 3px; font-size: 10px;")
        self.single_wrapper_button = QtWidgets.QPushButton("Change Wrapper")
        self.single_wrapper_button.setMinimumWidth(140)
        self.single_wrapper_button.setMaximumWidth(160)
        
        grid_layout.addWidget(self.single_checkbox, 2, 0)
        grid_layout.addWidget(single_example, 2, 1)
        grid_layout.addWidget(self.single_wrapper_button, 2, 2)
        
        # CD Detection
        self.cd_checkbox = QtWidgets.QCheckBox("CD")
        cd_example = QtWidgets.QLabel("\"Abbey Road\" → \"Abbey Road [CD]\"")
        cd_example.setStyleSheet("padding: 4px; border-radius: 3px; font-size: 10px;")
        self.cd_wrapper_button = QtWidgets.QPushButton("Change Wrapper")
        self.cd_wrapper_button.setMinimumWidth(140)
        self.cd_wrapper_button.setMaximumWidth(160)
        
        grid_layout.addWidget(self.cd_checkbox, 3, 0)
        grid_layout.addWidget(cd_example, 3, 1)
        grid_layout.addWidget(self.cd_wrapper_button, 3, 2)
        
        # Vinyl Detection
        self.vinyl_checkbox = QtWidgets.QCheckBox("Vinyl")
        vinyl_example = QtWidgets.QLabel("\"Dark Side\" → \"Dark Side [Vinyl]\"")
        vinyl_example.setStyleSheet("padding: 4px; border-radius: 3px; font-size: 10px;")
        self.vinyl_wrapper_button = QtWidgets.QPushButton("Change Wrapper")
        self.vinyl_wrapper_button.setMinimumWidth(140)
        self.vinyl_wrapper_button.setMaximumWidth(160)
        
        grid_layout.addWidget(self.vinyl_checkbox, 4, 0)
        grid_layout.addWidget(vinyl_example, 4, 1)
        grid_layout.addWidget(self.vinyl_wrapper_button, 4, 2)
        
        detection_layout.addLayout(grid_layout)
        layout.addWidget(detection_group)
    
    def _add_options_section(self, layout):
        """Add options section"""
        options_group = QtWidgets.QGroupBox("Options")
        options_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        options_layout = QtWidgets.QVBoxLayout(options_group)

        self.avoid_duplicates_checkbox = QtWidgets.QCheckBox("Only append if suffix not already present")
        options_layout.addWidget(self.avoid_duplicates_checkbox)

        layout.addWidget(options_group)

    def _add_variables_section(self, layout):
        """Add variables reference section with transforms"""
        variables_group = QtWidgets.QGroupBox("Available Variables (click to copy)")
        variables_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        variables_layout = QtWidgets.QVBoxLayout(variables_group)

        # Instructions
        instruction_label = QtWidgets.QLabel(
            "Click any variable below to copy it to clipboard, then paste into your formula.\n"
            "Use angle brackets <variable> for metadata. Use square brackets [group] for conditional groups."
        )
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("font-size: 10px; margin-bottom: 8px;")
        variables_layout.addWidget(instruction_label)

        # Variable buttons in a grid
        button_grid = QtWidgets.QGridLayout()
        button_grid.setSpacing(6)

        self.variable_buttons = {}
        row, col = 0, 0
        for var_name, info in VARIABLES_INFO.items():
            btn = QtWidgets.QPushButton(f"<{var_name}>")
            btn.setToolTip(f"{info['desc']}\nExamples: {info['example']}\nClick to copy to clipboard")
            btn.clicked.connect(lambda checked, v=var_name: self.copy_variable_to_clipboard(v))
            btn.setStyleSheet("""
                QPushButton {
                    text-align: center;
                    padding: 6px 8px;
                    font-size: 10px;
                    font-family: monospace;
                    border-radius: 4px;
                    min-width: 140px;
                }
            """)
            button_grid.addWidget(btn, row, col)
            self.variable_buttons[var_name] = btn

            col += 1
            if col > 3:
                col = 0
                row += 1

        variables_layout.addLayout(button_grid)

        # Transform/Modifier reference
        transforms_label = QtWidgets.QLabel(
            "<b>Variable Enhancers:</b><br>"
            "• Slice: <code>&lt;year[:4]&gt;</code> = first 4 characters (e.g., '2023')<br>"
            "• Upper: <code>&lt;format|upper&gt;</code> = FLAC<br>"
            "• Lower: <code>&lt;format|lower&gt;</code> = flac<br>"
            "• Title: <code>&lt;format|title&gt;</code> = Flac<br>"
            "• Digits: <code>&lt;sample_rate|digits&gt;</code> = extract numbers only<br>"
            "• kHz: <code>&lt;sample_rate|khz&gt;</code> = smart kHz (192000 → 192, 44100 → 44)"
        )
        transforms_label.setWordWrap(True)
        transforms_label.setTextFormat(Qt.RichText)
        transforms_label.setStyleSheet("font-size: 10px; margin-top: 8px; padding: 8px; background-color: palette(midlight); border-radius: 4px;")
        variables_layout.addWidget(transforms_label)

        layout.addWidget(variables_group)

    def load_templates_to_list(self):
        """Load templates into the list widget"""
        try:
            self.template_list.clear()

            # Load from JSON file, Picard settings, or defaults
            templates = load_templates_from_sources()

            # Sort templates alphabetically by name
            templates = sorted(templates, key=lambda t: t.get("name", "").lower())

            for template in templates:
                name = template.get("name", "Unnamed")
                self.template_list.addItem(name)
                item = self.template_list.item(self.template_list.count() - 1)
                item.setData(Qt.UserRole, template)

            # Select first template by default
            if self.template_list.count() > 0:
                self.template_list.setCurrentRow(0)
                self.on_template_selected()

        except Exception as e:
            log.error(f"Suffix Appender: Error loading templates: {e}")

    def on_template_selected(self):
        """Handle template selection change"""
        try:
            current_item = self.template_list.currentItem()
            if current_item:
                template_data = current_item.data(Qt.UserRole)
                if template_data:
                    formula = template_data.get("formula", "")
                    self.update_preview_with_formula(formula)
        except Exception as e:
            log.error(f"Suffix Appender: Error on template selection: {e}")

    def add_template_click(self):
        """Handle Add Template button click"""
        try:
            dialog = TemplateEditorDialog(parent=self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                template_data = dialog.get_template_data()

                if not template_data.get("name"):
                    QtWidgets.QMessageBox.warning(
                        self, "Invalid Template",
                        "Template name cannot be empty."
                    )
                    return

                # Add to list
                self.template_list.addItem(template_data["name"])
                item = self.template_list.item(self.template_list.count() - 1)
                item.setData(Qt.UserRole, template_data)

                # Save templates
                self.save_templates_from_list()

                log.info(f"Suffix Appender: Added template '{template_data['name']}'")
        except Exception as e:
            log.error(f"Suffix Appender: Error adding template: {e}")

    def edit_template_click(self):
        """Handle Edit button click"""
        try:
            current_item = self.template_list.currentItem()
            if not current_item:
                return

            template_data = current_item.data(Qt.UserRole)
            dialog = TemplateEditorDialog(template_data, parent=self)

            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                updated_data = dialog.get_template_data()

                if not updated_data.get("name"):
                    QtWidgets.QMessageBox.warning(
                        self, "Invalid Template",
                        "Template name cannot be empty."
                    )
                    return

                # Update list item
                current_item.setText(updated_data["name"])
                current_item.setData(Qt.UserRole, updated_data)

                # Save templates
                self.save_templates_from_list()

                log.info(f"Suffix Appender: Updated template '{updated_data['name']}'")
        except Exception as e:
            log.error(f"Suffix Appender: Error editing template: {e}")

    def delete_template_click(self):
        """Handle Delete button click"""
        try:
            current_row = self.template_list.currentRow()
            if current_row < 0:
                return

            current_item = self.template_list.currentItem()
            template_data = current_item.data(Qt.UserRole)
            template_name = template_data.get("name", "Unnamed")

            reply = QtWidgets.QMessageBox.question(
                self, "Delete Template",
                f"Are you sure you want to delete the template '{template_name}'?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                self.template_list.takeItem(current_row)
                self.save_templates_from_list()
                log.info(f"Suffix Appender: Deleted template '{template_name}'")
        except Exception as e:
            log.error(f"Suffix Appender: Error deleting template: {e}")

    def reset_templates_click(self):
        """Handle Reset to Defaults button click"""
        try:
            reply = QtWidgets.QMessageBox.question(
                self, "Reset Templates",
                "Are you sure you want to reset all templates to defaults? This will remove all custom templates.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )

            if reply == QtWidgets.QMessageBox.Yes:
                self.template_list.clear()

                for template in DEFAULT_TEMPLATES:
                    self.template_list.addItem(template["name"])
                    item = self.template_list.item(self.template_list.count() - 1)
                    item.setData(Qt.UserRole, template)

                self.save_templates_from_list()
                log.info("Suffix Appender: Reset templates to defaults")
        except Exception as e:
            log.error(f"Suffix Appender: Error resetting templates: {e}")

    def save_templates_from_list(self):
        """Save templates from list to settings and JSON file"""
        try:
            templates = []
            for i in range(self.template_list.count()):
                item = self.template_list.item(i)
                template_data = item.data(Qt.UserRole)
                if template_data:
                    templates.append(template_data)

            # Save to Picard settings (for backward compatibility)
            config.setting["suffix_appender_templates"] = json.dumps(templates)

            # Save to JSON file (primary storage)
            save_templates_to_json(templates)

            # Mark that templates have changed
            self.templates_changed = True

            log.info(f"Suffix Appender: Saved {len(templates)} templates to settings and JSON file")
        except Exception as e:
            log.error(f"Suffix Appender: Error saving templates: {e}")

    def export_to_json(self):
        """Export templates to a JSON file"""
        try:
            # Collect all templates
            templates = []
            for i in range(self.template_list.count()):
                item = self.template_list.item(i)
                template_data = item.data(Qt.UserRole)
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
                TEMPLATES_JSON_PATH,  # Default to standard location
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
                log.info(f"Suffix Appender: Exported {len(templates)} templates to {file_path}")

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Export Error",
                f"Failed to export templates:\n{str(e)}"
            )
            log.error(f"Suffix Appender: Error exporting templates: {e}")

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
                if "name" not in template or "formula" not in template:
                    continue
                valid_templates.append(template)

            if not valid_templates:
                QtWidgets.QMessageBox.warning(
                    self, "Invalid File",
                    "No valid templates found in the JSON file.\n\n"
                    "Each template must have 'name' and 'formula' fields."
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
                item.setData(Qt.UserRole, template)

            # Save to settings and JSON file
            self.save_templates_from_list()

            QtWidgets.QMessageBox.information(
                self, "Import Successful",
                f"Successfully imported {len(valid_templates)} templates from:\n{file_path}\n\n"
                f"Saved to: {TEMPLATES_JSON_PATH}\n\n"
                "Note: Restart Picard to see changes in the right-click menu."
            )
            log.info(f"Suffix Appender: Imported {len(valid_templates)} templates from {file_path}")

        except json.JSONDecodeError as e:
            QtWidgets.QMessageBox.critical(
                self, "Invalid JSON",
                f"Failed to parse JSON file:\n{str(e)}"
            )
            log.error(f"Suffix Appender: JSON parse error during import: {e}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Import Error",
                f"Failed to import templates:\n{str(e)}"
            )
            log.error(f"Suffix Appender: Error importing templates: {e}")

    def update_preview_with_formula(self, formula):
        """Update preview with given formula showing multiple format examples - uses shared examples"""
        try:
            if not formula:
                self.preview_text.setPlainText("Select a template to see preview...")
                return

            try:
                key_aliases = json.loads(config.setting["suffix_appender_key_aliases"])
            except:
                key_aliases = {}

            # Use shared preview examples function (single source of truth)
            examples = get_preview_examples()

            # Generate preview text for all examples
            preview_text = ""
            for i, example in enumerate(examples):
                result = FormulaRenderer(example["metadata"], key_aliases).render_formula(formula)
                full_result = example["title"] + result if result else example["title"]

                preview_text += f"{example['label']}:\n  '{example['title']}' → '{full_result}'"

                # Add newline between examples (but not after last one)
                if i < len(examples) - 1:
                    preview_text += "\n\n"

            if hasattr(self, 'preview_text'):
                self.preview_text.setPlainText(preview_text)

        except Exception as e:
            if hasattr(self, 'preview_text'):
                self.preview_text.setPlainText(f"Preview Error: {str(e)}")
            log.error(f"Suffix Appender: Preview error: {e}")

    def _connect_signals(self):
        """Connect UI signals"""
        # Template list selection
        self.template_list.currentItemChanged.connect(lambda: self.on_template_selected())

        # Template management buttons
        self.add_template_btn.clicked.connect(self.add_template_click)
        self.edit_template_btn.clicked.connect(self.edit_template_click)
        self.delete_template_btn.clicked.connect(self.delete_template_click)
        self.reset_templates_btn.clicked.connect(self.reset_templates_click)
        self.export_json_btn.clicked.connect(self.export_to_json)
        self.import_json_btn.clicked.connect(self.import_from_json)

        # Auto-detection button
        self.manage_detection_btn.clicked.connect(self.open_detection_matrix)

        # Legacy buttons (if they exist - for backward compatibility)
        if hasattr(self, 'view_preset_button'):
            self.view_preset_button.clicked.connect(self.open_preset_dialog)
        if hasattr(self, 'create_preset_button'):
            self.create_preset_button.clicked.connect(self.create_new_preset)

        # Wrapper buttons (if they exist)
        if hasattr(self, 'ep_wrapper_button'):
            self.ep_wrapper_button.clicked.connect(lambda: self.open_wrapper_dialog("EP"))
        if hasattr(self, 'single_wrapper_button'):
            self.single_wrapper_button.clicked.connect(lambda: self.open_wrapper_dialog("Single"))
        if hasattr(self, 'cd_wrapper_button'):
            self.cd_wrapper_button.clicked.connect(lambda: self.open_wrapper_dialog("CD"))
        if hasattr(self, 'vinyl_wrapper_button'):
            self.vinyl_wrapper_button.clicked.connect(lambda: self.open_wrapper_dialog("Vinyl"))

        # Detection checkboxes trigger preview updates (if they exist)
        if hasattr(self, 'ep_checkbox'):
            self.ep_checkbox.stateChanged.connect(self._schedule_preview_update)
        if hasattr(self, 'single_checkbox'):
            self.single_checkbox.stateChanged.connect(self._schedule_preview_update)
        if hasattr(self, 'cd_checkbox'):
            self.cd_checkbox.stateChanged.connect(self._schedule_preview_update)
        if hasattr(self, 'vinyl_checkbox'):
            self.vinyl_checkbox.stateChanged.connect(self._schedule_preview_update)
    
    def _schedule_preview_update(self):
        """Schedule preview update with debouncing"""
        if self._preview_timer:
            self._preview_timer.stop()
        
        self._preview_timer = QtCore.QTimer()
        self._preview_timer.timeout.connect(self.update_preview)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.start(500)
    
    def on_preset_changed(self, preset_name):
        """Handle preset selection change"""
        if preset_name in self.PRESETS and preset_name != "Custom":
            self.update_preview()

    def open_template_manager(self):
        """Open template manager dialog"""
        try:
            dialog = TemplateManagerDialog(self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                dialog.save_templates()
                log.info("Suffix Appender: Templates updated - restart Picard to see in menu")

                QtWidgets.QMessageBox.information(
                    self, "Templates Saved",
                    "Your templates have been saved!\n\n"
                    "Restart Picard to see them in the right-click menu."
                )
        except Exception as e:
            log.error(f"Suffix Appender: Error opening template manager: {e}")

    def open_detection_matrix(self):
        """Open detection matrix configuration dialog"""
        try:
            dialog = DetectionMatrixDialog(self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                dialog.save_settings()
                self.update_preview()
                log.info("Suffix Appender: Detection settings updated")
        except Exception as e:
            log.error(f"Suffix Appender: Error opening detection matrix: {e}")

    def open_preset_dialog(self):
        """Open preset view/management dialog"""
        current_preset = self.preset_combo.currentText()
        dialog = PresetViewDialog(self.PRESETS, current_preset, self)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            # Update presets
            self.PRESETS.update(dialog.get_presets())
            
            # Save custom presets when dialog changes are accepted
            self._save_custom_presets()
            
            if dialog.result_action in ["apply", "save"]:
                # Apply selected preset or save changes
                preset_name, formula = dialog.get_current_preset_data()
                self.preset_combo.setCurrentText(preset_name)
                self.update_preview()
            
            # Refresh combo
            current = self.preset_combo.currentText()
            self.preset_combo.clear()
            for name in sorted(self.PRESETS.keys()):
                self.preset_combo.addItem(name)
            
            index = self.preset_combo.findText(current)
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)
    
    def create_new_preset(self):
        """Create a new custom preset"""
        # Ask for preset name
        name, ok = QtWidgets.QInputDialog.getText(
            self, "Create New Preset", 
            "Enter name for new preset:",
            text="My Custom Preset"
        )
        
        if not ok or not name.strip():
            return
            
        name = name.strip()
        
        # Check if name already exists
        if name in self.PRESETS:
            reply = QtWidgets.QMessageBox.question(
                self, "Preset Exists", 
                f"A preset named '{name}' already exists. Do you want to replace it?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.No:
                return
        
        # Ask for formula
        formula, ok = QtWidgets.QInputDialog.getMultiLineText(
            self, "Create New Preset", 
            f"Enter formula for preset '{name}':\n\n"
            "Examples:\n"
            "• [<releasecountry> <format>] [<bits_per_sample>-<sample_rate[:2]>]\n"
            "• [<releasecountry> <catalognumber> <format>]\n"
            "• [<formatsize> <mediatype>] [<recordtype>]",
            text=" [<releasecountry> <format>]"
        )
        
        if ok:
            # Add to presets
            self.PRESETS[name] = formula
            
            # Save custom presets immediately
            self._save_custom_presets()
            
            # Refresh combo box
            current_text = self.preset_combo.currentText()
            self.preset_combo.clear()
            for preset_name in sorted(self.PRESETS.keys()):
                self.preset_combo.addItem(preset_name)
            
            # Select the new preset
            self.preset_combo.setCurrentText(name)
            self.update_preview()
            
            QtWidgets.QMessageBox.information(
                self, "Preset Created",
                f"Preset '{name}' has been created successfully!\n\n"
                "To add it to the right-click menu:\n"
                "1. Save your settings (OK button)\n"
                "2. Restart Picard\n\n"
                "The preset will work immediately via 'Active Preset' action."
            )
    
    def open_wrapper_dialog(self, detection_type):
        """Open wrapper selection dialog"""
        setting_key = f"suffix_appender_{detection_type.lower()}_wrapper"
        try:
            current_wrapper = config.setting[setting_key] if setting_key in config.setting else ""
        except KeyError:
            current_wrapper = ""
        
        dialog = WrapperSelectionDialog(current_wrapper, detection_type, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_wrapper = dialog.get_wrapper()
            config.setting[setting_key] = new_wrapper
            
            # Update button text to show current wrapper
            self._update_wrapper_button_text(detection_type, new_wrapper)
            # Update preview to show new wrapper
            self.update_preview()
    
    def _update_wrapper_button_text(self, detection_type, wrapper):
        """Keep wrapper button text as 'Change Wrapper' regardless of current setting"""
        button = getattr(self, f"{detection_type.lower()}_wrapper_button")
        button.setText("Change Wrapper")
    
    def update_preview(self):
        """Update preview with current formula and detection settings"""
        try:
            # Get current settings
            current_preset = self.preset_combo.currentText()
            formula = self.PRESETS.get(current_preset, "")
            
            # Get detection settings
            add_ep = self.ep_checkbox.isChecked() if hasattr(self, 'ep_checkbox') else False
            add_single = self.single_checkbox.isChecked() if hasattr(self, 'single_checkbox') else False
            add_cd = self.cd_checkbox.isChecked() if hasattr(self, 'cd_checkbox') else False
            add_vinyl = self.vinyl_checkbox.isChecked() if hasattr(self, 'vinyl_checkbox') else False
            
            # Sample metadata for examples
            ep_metadata = {
                "releasecountry": "US", "media": "12\" Vinyl", "~format": "FLAC",
                "~bits_per_sample": "24", "~sample_rate": "96000", "~channels": "2",
                "~primaryreleasetype": "ep", "year": "2023", "label": "Blue Note"
            }
            single_metadata = {
                "releasecountry": "UK", "media": "CD", "~format": "FLAC", 
                "~bits_per_sample": "16", "~sample_rate": "44100", "~channels": "2",
                "~primaryreleasetype": "single", "year": "1968", "label": "Apple"
            }
            
            # Build simple examples without Current Formula display
            examples = []
            
            if formula or any([add_ep, add_single, add_cd, add_vinyl]):
                try:
                    key_aliases = json.loads(config.setting["suffix_appender_key_aliases"])
                except:
                    key_aliases = {}
                
                # EP example
                ep_title = "Kind of Blue EP"
                ep_result = ep_title
                if formula:
                    renderer = FormulaRenderer(ep_metadata, key_aliases)
                    ep_result += renderer.render_formula(formula)
                # Only add EP if it's not already in the title and EP detection is enabled
                if add_ep and not _ep_already_present(ep_title):
                    ep_result += " EP"
                examples.append(f"'{ep_title}' → '{ep_result}'")
                
                # Single example  
                single_title = "Hey Jude"
                single_result = single_title
                if formula:
                    renderer = FormulaRenderer(single_metadata, key_aliases)
                    single_result += renderer.render_formula(formula)
                if add_single:
                    single_result += " [Single]"
                examples.append(f"'{single_title}' → '{single_result}'")
                
                # Detection summary
                active_detection = []
                if add_ep: active_detection.append("EP")
                if add_single: active_detection.append("Single")  
                if add_cd: active_detection.append("CD")
                if add_vinyl: active_detection.append("Vinyl")
                
                if active_detection:
                    examples.append(f"\nAuto Detection: {', '.join(active_detection)} enabled")
                else:
                    examples.append(f"\nAuto Detection: disabled")
            else:
                examples.append("Select a preset or enable auto-detection to see examples...")
            
            # Set the preview as plain text
            self.preview_text.setText("\n".join(examples))
            
        except Exception as e:
            self.preview_text.setText(f"Preview Error: {str(e)}")
    
    def _get_preview_detection_suffixes(self, metadata, add_ep, add_single, add_cd, add_vinyl,
                                       ep_wrapper, single_wrapper, cd_wrapper, vinyl_wrapper):
        """Get detection suffixes for preview (similar to action logic)"""
        suffixes = []
        
        release_type = _get_metadata_value(metadata, "~primaryreleasetype").lower()
        media_type = _get_metadata_value(metadata, "media").lower()
        
        if add_ep and release_type == "ep" and ep_wrapper:
            suffixes.append(self._format_wrapper_for_display("EP", ep_wrapper))
        
        if add_single and release_type == "single" and single_wrapper:
            suffixes.append(self._format_wrapper_for_display("Single", single_wrapper))
        
        if add_cd and "cd" in media_type and cd_wrapper:
            suffixes.append(self._format_wrapper_for_display("CD", cd_wrapper))
        
        if add_vinyl and "vinyl" in media_type and vinyl_wrapper:
            suffixes.append(self._format_wrapper_for_display("Vinyl", vinyl_wrapper))
        
        return suffixes
    
    def _format_wrapper_for_display(self, text, wrapper):
        """Format wrapper for display in preview"""
        if not wrapper:
            return f" {text}"
        elif wrapper == "[]":
            return f" [{text}]"
        elif wrapper == "()":
            return f" ({text})"
        elif wrapper == "<>":
            return f" <{text}>"
        elif wrapper == "{}":
            return f" {{{text}}}"
        elif wrapper == "- ":
            return f" - {text}"
        elif wrapper == "| ":
            return f" | {text}"
        elif wrapper == " ":
            return f" {text}"
        else:
            # Custom wrapper
            if text in wrapper:
                return f" {wrapper}"
            else:
                return f" {wrapper}{text}{wrapper}"
    
    def load(self):
        """Load settings"""
        try:
            self.avoid_duplicates_checkbox.setChecked(config.setting["suffix_appender_avoid_duplicates"])
            self.target_album_checkbox.setChecked(config.setting["suffix_appender_target_album"])
            self.target_title_checkbox.setChecked(config.setting["suffix_appender_target_title"])
            self.target_comment_checkbox.setChecked(config.setting["suffix_appender_target_comment"])
            self.target_discsubtitle_checkbox.setChecked(config.setting["suffix_appender_target_discsubtitle"])
            self.target_work_checkbox.setChecked(config.setting["suffix_appender_target_work"])
            
            # Detection checkboxes
            self.ep_checkbox.setChecked(config.setting["suffix_appender_add_ep"])
            self.single_checkbox.setChecked(config.setting["suffix_appender_add_single"])
            self.cd_checkbox.setChecked(config.setting["suffix_appender_add_cd"])
            self.vinyl_checkbox.setChecked(config.setting["suffix_appender_add_vinyl"])
            
            # Update wrapper button texts
            self._update_wrapper_button_text("EP", config.setting["suffix_appender_ep_wrapper"])
            self._update_wrapper_button_text("Single", config.setting["suffix_appender_single_wrapper"])
            self._update_wrapper_button_text("CD", config.setting["suffix_appender_cd_wrapper"])
            self._update_wrapper_button_text("Vinyl", config.setting["suffix_appender_vinyl_wrapper"])
            
            # Set preset combo
            preset_index = self.preset_combo.findText(config.setting["suffix_appender_active_preset"])
            if preset_index >= 0:
                self.preset_combo.setCurrentIndex(preset_index)
            
            self.update_preview()
            
        except Exception as e:
            log.error(f"Suffix Appender: Error loading settings: {e}")
    
    def save(self):
        """Save settings"""
        try:
            config.setting["suffix_appender_avoid_duplicates"] = self.avoid_duplicates_checkbox.isChecked()
            config.setting["suffix_appender_target_album"] = self.target_album_checkbox.isChecked()
            config.setting["suffix_appender_target_title"] = self.target_title_checkbox.isChecked()
            config.setting["suffix_appender_target_comment"] = self.target_comment_checkbox.isChecked()
            config.setting["suffix_appender_target_discsubtitle"] = self.target_discsubtitle_checkbox.isChecked()
            config.setting["suffix_appender_target_work"] = self.target_work_checkbox.isChecked()

            # Save custom presets (legacy)
            self._save_custom_presets()

            # Show notification if templates were modified
            if self.templates_changed:
                QtWidgets.QMessageBox.information(
                    self, "Templates Updated",
                    "Template changes have been saved and will take effect immediately!\n\n"
                    "Note: If you added or removed templates, those menu items will appear "
                    "after restarting Picard. Modified template formulas work right away."
                )

        except Exception as e:
            log.error(f"Suffix Appender: Error saving settings: {e}")
    
    def show_error(self, message):
        """Show error message to user"""
        try:
            QtWidgets.QMessageBox.warning(self, "Suffix Appender", message)
        except Exception:
            pass

def create_preset_action(preset_name, preset_formula):
    """Factory function to create preset action classes with proper NAME at class level"""

    class SuffixPresetAction(BaseAction):
        """Apply a specific preset formula - reads formula dynamically from settings"""
        NAME = preset_name  # Removed "Preset:" prefix in v2.2.0 for cleaner menu
        TITLE = preset_name
        MENU = ("Suffix",)

        def __init__(self):
            super().__init__()
            self.preset_name = preset_name
            # Don't store formula - read it dynamically from settings

        def _get_current_formula(self):
            """Get current formula for this template from settings"""
            try:
                templates_json = config.setting["suffix_appender_templates"]
                templates = json.loads(templates_json) if templates_json else []

                # Find this template by name
                for template in templates:
                    if template.get("name") == self.preset_name:
                        return template.get("formula", "")

                # Fallback to default templates if not found in settings
                for template in DEFAULT_TEMPLATES:
                    if template.get("name") == self.preset_name:
                        return template.get("formula", "")

                return ""
            except Exception as e:
                log.error(f"Suffix Appender: Error reading formula for '{self.preset_name}': {e}")
                return preset_formula  # Fallback to init-time formula

        def callback(self, objs):
            try:
                # Get settings
                target_album = config.setting["suffix_appender_target_album"]
                target_title = config.setting["suffix_appender_target_title"]
                target_comment = config.setting["suffix_appender_target_comment"]
                target_discsubtitle = config.setting["suffix_appender_target_discsubtitle"]
                target_work = config.setting["suffix_appender_target_work"]
                avoid_duplicates = config.setting["suffix_appender_avoid_duplicates"]

                # Detection settings
                add_ep = config.setting["suffix_appender_add_ep"]
                add_single = config.setting["suffix_appender_add_single"]
                add_cd = config.setting["suffix_appender_add_cd"]
                add_vinyl = config.setting["suffix_appender_add_vinyl"]

                # Wrapper settings
                ep_wrapper = config.setting["suffix_appender_ep_wrapper"]
                single_wrapper = config.setting["suffix_appender_single_wrapper"]
                cd_wrapper = config.setting["suffix_appender_cd_wrapper"]
                vinyl_wrapper = config.setting["suffix_appender_vinyl_wrapper"]

                # Read the current formula dynamically from settings
                active_formula = self._get_current_formula()

                # Allow detection without formula, but require at least something
                if not active_formula and not any([add_ep, add_single, add_cd, add_vinyl]):
                    log.warning(
                        f"Suffix Appender: Preset '{self.preset_name}' has no formula "
                        "and no detection configured"
                    )
                    return

                if not any([target_album, target_title, target_comment,
                            target_discsubtitle, target_work]):
                    log.warning("Suffix Appender: No target fields selected")
                    return

                try:
                    key_aliases = json.loads(config.setting["suffix_appender_key_aliases"])
                except (json.JSONDecodeError, TypeError):
                    key_aliases = {}

                target_fields = []
                if target_album:
                    target_fields.append("album")
                if target_title:
                    target_fields.append("title")
                if target_comment:
                    target_fields.append("comment")
                if target_discsubtitle:
                    target_fields.append("discsubtitle")
                if target_work:
                    target_fields.append("work")

                processed_objects = set()
                changed_objects = []
                checked = 0
                changed = 0

                # Create a suffix action instance to reuse its methods
                suffix_action = SuffixAction()

                # Process all metadata and keep track of changed objects
                for obj, metadata in suffix_action._iter_unique_metadata_with_objects(objs, processed_objects):
                    checked += 1
                    try:
                        if suffix_action._apply_suffix_to_metadata(
                            metadata, active_formula, target_fields, avoid_duplicates, key_aliases,
                            add_ep, add_single, add_cd, add_vinyl,
                            ep_wrapper, single_wrapper, cd_wrapper, vinyl_wrapper
                        ):
                            changed += 1
                            changed_objects.append(obj)
                    except Exception as e:
                        log.error(f"Suffix Appender: Error processing metadata: {e}")

                # Notify UI about changes
                if changed_objects:
                    suffix_action._notify_metadata_changes(changed_objects)

                if checked > 0:
                    log.info(f"Suffix Appender: Applied preset '{self.preset_name}' to {checked} items, changed {changed}")

            except Exception as e:
                log.error(f"Suffix Appender: Preset action '{self.preset_name}' callback failed: {e}")

    return SuffixPresetAction


class SuffixAction(BaseAction):
    NAME = "Active Preset"
    MENU = ("Suffix",)

    def callback(self, objs):
        try:
            # Get settings
            active_formula = config.setting["suffix_appender_active_formula"]
            target_album = config.setting["suffix_appender_target_album"]
            target_title = config.setting["suffix_appender_target_title"]
            target_comment = config.setting["suffix_appender_target_comment"]
            target_discsubtitle = config.setting["suffix_appender_target_discsubtitle"]
            target_work = config.setting["suffix_appender_target_work"]
            avoid_duplicates = config.setting["suffix_appender_avoid_duplicates"]

            # Detection settings
            add_ep = config.setting["suffix_appender_add_ep"]
            add_single = config.setting["suffix_appender_add_single"]
            add_cd = config.setting["suffix_appender_add_cd"]
            add_vinyl = config.setting["suffix_appender_add_vinyl"]

            # Wrapper settings
            ep_wrapper = config.setting["suffix_appender_ep_wrapper"]
            single_wrapper = config.setting["suffix_appender_single_wrapper"]
            cd_wrapper = config.setting["suffix_appender_cd_wrapper"]
            vinyl_wrapper = config.setting["suffix_appender_vinyl_wrapper"]

            # Allow detection without formula, but require at least something
            if not active_formula and not any([add_ep, add_single, add_cd, add_vinyl]):
                log.warning("Suffix Appender: No formula or detection configured")
                return

            if not any([target_album, target_title, target_comment,
                        target_discsubtitle, target_work]):
                log.warning("Suffix Appender: No target fields selected")
                return

            try:
                key_aliases = json.loads(config.setting["suffix_appender_key_aliases"])
            except (json.JSONDecodeError, TypeError):
                key_aliases = {}

            target_fields = []
            if target_album:
                target_fields.append("album")
            if target_title:
                target_fields.append("title")
            if target_comment:
                target_fields.append("comment")
            if target_discsubtitle:
                target_fields.append("discsubtitle")
            if target_work:
                target_fields.append("work")
            
            processed_objects = set()
            changed_objects = []
            checked = 0
            changed = 0
            
            # Process all metadata and keep track of changed objects
            for obj, metadata in self._iter_unique_metadata_with_objects(objs, processed_objects):
                checked += 1
                try:
                    # Debug: log what fields are available in this metadata
                    available_fields = [key for key in metadata.keys() if key in ["album", "title", "comment"]]
                    log.debug(f"Suffix Appender: Processing metadata with fields: {available_fields}")
                    
                    if self._apply_suffix_to_metadata(
                        metadata, active_formula, target_fields, avoid_duplicates, key_aliases,
                        add_ep, add_single, add_cd, add_vinyl,
                        ep_wrapper, single_wrapper, cd_wrapper, vinyl_wrapper
                    ):
                        changed += 1
                        changed_objects.append(obj)
                except Exception as e:
                    log.error(f"Suffix Appender: Error processing metadata: {e}")
            
            # Notify UI about changes
            if changed_objects:
                self._notify_metadata_changes(changed_objects)
            
            if checked > 0:
                log.info(f"Suffix Appender: Processed {checked} items, changed {changed}")
        
        except Exception as e:
            log.error(f"Suffix Appender: Action callback failed: {e}")
    
    def _iter_unique_metadata_with_objects(self, objs, processed_objects):
        """
        Yield all metadata dict-like objects with their parent objects from a mixed selection
        (file/track/album/cluster) - enhanced version for UI updates
        """
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
                # For albums, include album metadata AND track/file metadata (original logic)
                if hasattr(obj, 'metadata'):
                    log.debug(f"Suffix Appender: Processing Album metadata")
                    yield (obj, obj.metadata)  # Album metadata for album title
                for track in getattr(obj, "tracks", []):
                    track_id = id(track)
                    if track_id not in processed_objects and hasattr(track, 'metadata'):
                        processed_objects.add(track_id)
                        log.debug(f"Suffix Appender: Processing Track metadata")
                        yield (track, track.metadata)  # Track metadata for track titles
                        for file_obj in getattr(track, "linked_files", []):
                            file_id = id(file_obj)
                            if file_id not in processed_objects and hasattr(file_obj, 'metadata'):
                                processed_objects.add(file_id)
                                log.debug(f"Suffix Appender: Processing File metadata")
                                yield (file_obj, file_obj.metadata)  # File metadata for file tags
            elif class_name in ("Cluster",):
                for file_obj in getattr(obj, "files", []):
                    file_id = id(file_obj)
                    if file_id not in processed_objects and hasattr(file_obj, 'metadata'):
                        processed_objects.add(file_id)
                        yield (file_obj, file_obj.metadata)
            else:
                # Generic fallback
                if hasattr(obj, 'metadata'):
                    yield (obj, obj.metadata)
    
    def _notify_metadata_changes(self, changed_objects):
        """Notify the UI about metadata changes to refresh display"""
        try:
            albums_to_update = set()
            tracks_to_update = set()
            files_to_update = set()
            
            for obj in changed_objects:
                class_name = obj.__class__.__name__
                
                if class_name == "Album":
                    albums_to_update.add(obj)
                elif class_name == "Track":
                    tracks_to_update.add(obj)
                    # Find parent album
                    if hasattr(obj, 'album') and obj.album:
                        albums_to_update.add(obj.album)
                elif class_name == "File":
                    files_to_update.add(obj)
                    # Find parent track and album
                    if hasattr(obj, 'parent') and obj.parent:
                        track = obj.parent
                        tracks_to_update.add(track)
                        if hasattr(track, 'album') and track.album:
                            albums_to_update.add(track.album)
            
            # Update files first (most specific)
            for file_obj in files_to_update:
                try:
                    if hasattr(file_obj, 'update') and callable(getattr(file_obj, 'update')):
                        file_obj.update()
                    # Also try metadata_changed signal if available
                    if hasattr(file_obj, 'metadata_changed'):
                        file_obj.metadata_changed.emit()
                except Exception as e:
                    log.debug(f"Suffix Appender: File update notification failed: {e}")
            
            # Update tracks  
            for track in tracks_to_update:
                try:
                    if hasattr(track, 'update') and callable(getattr(track, 'update')):
                        track.update()
                    if hasattr(track, 'metadata_changed'):
                        track.metadata_changed.emit()
                except Exception as e:
                    log.debug(f"Suffix Appender: Track update notification failed: {e}")
                    
            # Update albums (most general)
            for album in albums_to_update:
                try:
                    # Multiple approaches to ensure UI updates
                    if hasattr(album, 'update') and callable(getattr(album, 'update')):
                        album.update()
                    
                    # Try metadata changed signals
                    if hasattr(album, 'metadata_changed'):
                        album.metadata_changed.emit()
                    
                    # Try to update the album's item view directly
                    if hasattr(album, 'item') and hasattr(album.item, 'update'):
                        album.item.update()
                    
                    # Force refresh by setting dirty flags if available
                    if hasattr(album, '_changed') and hasattr(album, 'update_metadata'):
                        album._changed = True
                        album.update_metadata()
                    
                    # Try updating through the tagger main window
                    try:
                        from picard import tagger
                        if hasattr(tagger, 'tagger') and hasattr(tagger.tagger, 'album_view'):
                            tagger.tagger.album_view.update()
                    except ImportError:
                        pass
                        
                    log.debug(f"Suffix Appender: Notified album update for: {album}")
                except Exception as e:
                    log.debug(f"Suffix Appender: Album update notification failed: {e}")
                        
        except Exception as e:
            log.error(f"Suffix Appender: Failed to notify metadata changes: {e}")
    
    def _iter_unique_metadata(self, objs, processed_objects):
        """
        Yield all metadata dict-like objects from a mixed selection
        (file/track/album/cluster) - based on original working logic
        """
        for obj in objs:
            obj_id = id(obj)
            if obj_id in processed_objects:
                continue
            
            processed_objects.add(obj_id)
            
            class_name = obj.__class__.__name__
            
            if class_name in ("File",):
                if hasattr(obj, 'metadata'):
                    yield obj.metadata
            elif class_name in ("Track",):
                if hasattr(obj, 'metadata'):
                    yield obj.metadata
            elif class_name in ("Album",):
                # For albums, include album metadata AND track/file metadata (original logic)
                if hasattr(obj, 'metadata'):
                    log.debug(f"Suffix Appender: Processing Album metadata")
                    yield obj.metadata  # Album metadata for album title
                for track in getattr(obj, "tracks", []):
                    track_id = id(track)
                    if track_id not in processed_objects and hasattr(track, 'metadata'):
                        processed_objects.add(track_id)
                        log.debug(f"Suffix Appender: Processing Track metadata")
                        yield track.metadata  # Track metadata for track titles
                        for file_obj in getattr(track, "linked_files", []):
                            file_id = id(file_obj)
                            if file_id not in processed_objects and hasattr(file_obj, 'metadata'):
                                processed_objects.add(file_id)
                                log.debug(f"Suffix Appender: Processing File metadata")
                                yield file_obj.metadata  # File metadata for file tags
            elif class_name in ("Cluster",):
                for file_obj in getattr(obj, "files", []):
                    file_id = id(file_obj)
                    if file_id not in processed_objects and hasattr(file_obj, 'metadata'):
                        processed_objects.add(file_id)
                        yield file_obj.metadata
            else:
                # Generic fallback
                if hasattr(obj, 'metadata'):
                    yield obj.metadata
    
    def _apply_suffix_to_metadata(self, metadata, formula, target_fields, avoid_duplicates, key_aliases,
                                 add_ep, add_single, add_cd, add_vinyl,
                                 ep_wrapper, single_wrapper, cd_wrapper, vinyl_wrapper):
        """Apply suffix to metadata with enhanced detection"""
        try:
            # Render formula if present
            suffix = ""
            if formula:
                renderer = FormulaRenderer(metadata, key_aliases)
                suffix = renderer.render_formula(formula)
            
            changed = False
            
            for target_field in target_fields:
                original_value = _get_metadata_value(metadata, target_field)
                if not original_value:
                    continue
                
                working_value = original_value
                
                # Apply detection-based suffixes first
                try:
                    detection_suffixes = self._get_detection_suffixes(
                        metadata, original_value, add_ep, add_single, add_cd, add_vinyl,
                        ep_wrapper, single_wrapper, cd_wrapper, vinyl_wrapper
                    )
                    
                    for det_suffix in detection_suffixes:
                        if det_suffix and not self._suffix_already_present(working_value, det_suffix):
                            working_value = f"{working_value}{det_suffix}"
                            log.debug(f"Suffix Appender: Added detection suffix '{det_suffix}' to {target_field}")
                except Exception as e:
                    log.error(f"Suffix Appender: Error applying detection suffixes: {e}")
                
                # Add formula suffix
                if suffix:
                    try:
                        if not (avoid_duplicates and self._suffix_already_present(working_value, suffix)):
                            working_value = f"{working_value}{suffix}"
                            log.debug(f"Suffix Appender: Added formula suffix '{suffix}' to {target_field}")
                        else:
                            log.debug(f"Suffix Appender: Formula suffix '{suffix}' already present in {target_field}")
                    except Exception as e:
                        log.error(f"Suffix Appender: Error applying formula suffix: {e}")
                
                if working_value != original_value:
                    # Force complete replacement: clear all values first, then set single new value
                    # This prevents Picard from appending to multi-valued tags
                    try:
                        # For multi-valued tags, we need to clear and set as single value
                        metadata.delete(target_field)
                    except (AttributeError, TypeError):
                        # Fallback for metadata objects without delete method
                        try:
                            del metadata[target_field]
                        except (KeyError, AttributeError):
                            pass

                    # Set as single value (not list) to prevent multi-value behavior
                    metadata[target_field] = working_value
                    changed = True
                    log.info(f"Suffix Appender: Replaced {target_field}: '{original_value}' → '{working_value}'")
            
            return changed
            
        except Exception as e:
            log.error(f"Suffix Appender: Error applying suffix: {e}")
            return False
    
    def _get_detection_suffixes(self, metadata, original_value, add_ep, add_single, add_cd, add_vinyl,
                               ep_wrapper, single_wrapper, cd_wrapper, vinyl_wrapper):
        """Get detection-based suffixes"""
        suffixes = []

        # Release type detection
        release_type = _get_metadata_value(metadata, "~primaryreleasetype").lower()
        media_type = _get_metadata_value(metadata, "media").lower()

        # Debug logging
        log.debug(f"Suffix Appender Detection: release_type='{release_type}', media_type='{media_type}'")
        log.debug(f"Suffix Appender Detection: add_ep={add_ep}, add_single={add_single}, add_cd={add_cd}, add_vinyl={add_vinyl}")
        log.debug(f"Suffix Appender Detection: ep_wrapper='{ep_wrapper}', single_wrapper='{single_wrapper}'")

        # For EP detection, only add if EP is not already present in the original title
        if add_ep and release_type == "ep" and ep_wrapper:
            if not _ep_already_present(original_value):
                suffixes.append(self._wrap_text("EP", ep_wrapper))
                log.debug(f"Suffix Appender Detection: Added EP suffix")

        if add_single and release_type == "single" and single_wrapper:
            suffixes.append(self._wrap_text("Single", single_wrapper))
            log.debug(f"Suffix Appender Detection: Added Single suffix")

        if add_cd and "cd" in media_type and cd_wrapper:
            suffixes.append(self._wrap_text("CD", cd_wrapper))
            log.debug(f"Suffix Appender Detection: Added CD suffix")

        if add_vinyl and "vinyl" in media_type and vinyl_wrapper:
            suffixes.append(self._wrap_text("Vinyl", vinyl_wrapper))
            log.debug(f"Suffix Appender Detection: Added Vinyl suffix")

        log.debug(f"Suffix Appender Detection: Total detection suffixes: {suffixes}")
        return suffixes
    
    def _wrap_text(self, text, wrapper):
        """Wrap text with specified wrapper format"""
        if not wrapper:
            return f" {text}"
        
        # Handle predefined wrapper patterns
        if wrapper == "[]":
            return f" [{text}]"
        elif wrapper == "()":
            return f" ({text})"
        elif wrapper == "<>":
            return f" <{text}>"
        elif wrapper == "{}":
            return f" {{{text}}}"
        elif wrapper == "- ":
            return f" - {text}"
        elif wrapper == "| ":
            return f" | {text}"
        elif wrapper == " ":
            return f" {text}"
        else:
            # Custom wrapper - check if it already contains the text completely
            if wrapper.strip() == text or wrapper == f" {text}":
                # Wrapper is exactly " EP" and text is "EP", return as-is
                return wrapper
            elif text in wrapper:
                # Wrapper like " [EP]" contains "EP", return as-is
                return wrapper
            elif wrapper.startswith(" "):
                # Wrapper starts with space but doesn't contain text - this is for cases like " [{}]"
                return wrapper.replace("{}", text) if "{}" in wrapper else f"{wrapper}{text}"
            else:
                # Custom wrapper without space - add space and wrap
                if text in wrapper:
                    return f" {wrapper}"
                else:
                    return f" {wrapper}{text}{wrapper}"
    
    def _suffix_already_present(self, original_value, suffix):
        """Check if the suffix is already present at the end of the value"""
        try:
            # Check for exact suffix match at the end (this catches " EP", " [Single]", etc.)
            if suffix and original_value.endswith(suffix):
                return True
            
            # Also check for bracketed versions (legacy support)
            trailing_brackets = []
            temp_value = original_value
            
            while True:
                match = _RE_TRAILING_BRACKET.search(temp_value)
                if not match:
                    break
                trailing_brackets.insert(0, match.group(0).strip())
                temp_value = temp_value[:match.start()].strip()
            
            # Check if our suffix matches any trailing bracket or the combination
            suffix_clean = suffix.strip()
            trailing_clean = ' '.join(trailing_brackets).strip()
            
            return suffix_clean == trailing_clean
        except Exception:
            return False

def enable(api):
    use_v3 = hasattr(api, 'register_cluster_action')
    templates = load_templates_from_sources()
    templates = sorted(templates, key=lambda t: t.get("name", "").lower())
    for template in templates:
        template_name = template.get("name", "Unnamed")
        template_formula = template.get("formula", "")
        if template_formula:
            ActionClass = create_preset_action(template_name, template_formula)
            if use_v3:
                for fn_name in ('register_album_action', 'register_track_action',
                                'register_file_action', 'register_cluster_action'):
                    fn = getattr(api, fn_name, None)
                    if fn:
                        fn(ActionClass)
            else:
                action = ActionClass()
                register_album_action(action)
                register_track_action(action)
                register_file_action(action)
                register_cluster_action(action)
    log.info(f"Suffix Appender: Registered {len(templates)} template actions")

    register_options_page(SuffixOptionsPage)
    log.info("Suffix Appender: Plugin loaded")