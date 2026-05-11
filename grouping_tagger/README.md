# Grouping Tagger

**Version:** 3.1.2
**Author:** rpmzine
**API Versions:** 2.10, 2.11, 2.12, 2.13, 3.0
**License:** MIT

A MusicBrainz Picard plugin that automatically tags the GROUPING field with source and format information.

**NEW in 3.1.0**: Export and Import now handle BOTH templates AND fixed tags in a single combined JSON file. No more separate exports - one file backs up your entire configuration! Buttons moved to main options page for easier access.

## Features

- **Vinyl Detection**: Automatically adds "Vinyl" tag when media field contains "vinyl"
- **CD Detection**: Automatically adds "CD" tag when media field contains "cd"
- **Cassette Detection**: Automatically adds "Cassette" tag when media field contains "cassette" or "tape"
- **Bootleg Detection**: Adds "Bootleg" tag based on release status or metadata keywords
- **Digital Detection**: Adds "Digital" tag for digital/download/web releases
- **Remaster Detection**: Detects remastered releases from metadata
- **Quality Tier Detection**: Automatically categorizes audio files by quality:
  - **Lossy**: MP3, AAC, OGG, WMA, Opus, etc.
  - **Lossless**: FLAC, ALAC, APE, WAV, AIFF (16-bit or 44.1/48kHz)
  - **Hi-Def**: FLAC, WAV, etc. with 24-bit depth or ≥88.2kHz sample rate
- **Template System**: Create custom templates with variables for flexible tagging patterns
- **Manual Tags**: Add custom tags that will always be included
- **Append Mode**: Choose to append tags to existing GROUPING or replace
- **Customizable Separator**: Configure how tags are separated (default: ", ")
- **Matrix System**: Enable/disable any combination of detection rules independently
- **Fixed Tag Menu**: Apply specific tags directly via right-click menu

## Installation

1. Copy the `grouping_tagger` folder to your Picard plugins directory:
   - Windows: `%APPDATA%\MusicBrainz\Picard\plugins`
   - macOS: `~/.config/MusicBrainz/Picard/plugins`
   - Linux: `~/.config/MusicBrainz/Picard/plugins`

2. Restart Picard

3. Enable the plugin in Options → Plugins

## JSON Configuration Storage (v3.0.0+)

### Configuration File Location

Starting with version 3.0.0, your configuration is stored in a separate JSON file outside the plugin folder. **Version 3.1.0** now stores BOTH templates and fixed tags in a single combined file:

```
~/Library/Preferences/MusicBrainz/Picard/json/grouping_tagger_config.json
```

### Why This Matters

**Preserve Your Configuration**: When you update the plugin by replacing the `grouping_tagger` folder, your custom templates AND fixed tags remain safe in the separate `json` folder. You never lose your configuration!

**Easy Backup**: Simply copy one JSON file to backup your entire configuration.

**Version Control**: Keep your configuration in git or any version control system.

**Share Configuration**: Send your JSON file to others or import configurations from the community.

### Import/Export Features (v3.1.0)

**Located in Main Options Page** (Options → Plugins → Grouping Tagger):

- **Export Configuration (JSON)** button - Save BOTH templates and fixed tags to a single JSON file
  - Backs up your complete plugin configuration
  - Choose any location for your backup file
  - Default location: Standard JSON preferences folder

- **Import Configuration (JSON)** button - Load templates and fixed tags from a file
  - **Merge Mode**: Add imported items to your existing configuration
  - **Replace Mode**: Completely replace your current configuration with imported items
  - Supports both new combined format and legacy template-only files
  - Shows what will be imported before you confirm

### Configuration Loading Priority

The plugin loads configuration in this order:

1. **JSON file** (if exists): `~/Library/Preferences/MusicBrainz/Picard/json/grouping_tagger_config.json`
2. **Legacy JSON file** (if exists): `~/Library/Preferences/MusicBrainz/Picard/json/grouping_tagger_templates.json` (template-only)
3. **Picard settings** (fallback): Internal Picard configuration database
4. **Default configuration** (last resort): Built-in templates and fixed tags

This means you can edit the JSON file directly if you prefer, and Picard will load it on next startup!

### Migrating from Older Versions

**From version 2.x:**
- Your existing templates and fixed tags will be automatically loaded from Picard settings
- On first save, they'll be written to the new JSON file location
- Future updates will use the JSON file as the primary source

**From version 3.0.0:**
- The old `grouping_tagger_templates.json` file (template-only) will be automatically migrated
- Export your configuration using the new button to create the combined format file
- The new `grouping_tagger_config.json` includes both templates AND fixed tags

### JSON File Format (v3.1.0)

```json
{
  "templates": [
    {
      "name": "Source + Format",
      "template": "{SOURCE} | {FORMAT}",
      "divider": " | "
    },
    {
      "name": "Simple Source",
      "template": "{SOURCE}",
      "divider": ", "
    }
  ],
  "fixed_tags": {
    "vinyl": "Vinyl",
    "cd": "CD",
    "digital": "Digital",
    "mp3": "MP3",
    "flac": "FLAC",
    "lossy": "Lossy",
    "lossless": "Lossless",
    "hidef": "Hi-Def",
    "bootleg": "Bootleg",
    "remastered": "Remastered",
    "limited": "Limited Edition",
    "japanese": "Japanese Import",
    "deluxe": "Deluxe Edition"
  }
}
```

**Legacy Format (v3.0.0 - still supported):**
```json
[
  {
    "name": "Source + Format",
    "template": "{SOURCE} | {FORMAT}",
    "divider": " | "
  }
]
```

## Usage

### Configuration

Go to Options → Plugins → Grouping Tagger to configure:

1. **Detection Matrix**: Enable/disable any combination of detection rules:
   - Vinyl Source
   - CD Source
   - Cassette Source
   - Digital Source
   - Bootleg Release
   - Remastered
   - File Format (Quality Tier)

2. **Customize Tag Text**: Click "Change Tag..." buttons to select or enter custom text for each detection type

3. **Behavior Options**:
   - Toggle append mode (add to existing GROUPING vs. replace)
   - Configure tag separator (default: ", ")

4. **Additional Tags**: Add custom tags that will always be included (comma-separated)

5. **Preview**: See live examples of how your tags will look

### Tagging Files

**Auto-Detect Method:**
1. Select albums, tracks, or files in Picard
2. Right-click and select "Tag GROUPING (Auto-Detect)"
3. The GROUPING field will be populated based on your configured detection rules

**Fixed Tag Method:**
1. Select albums, tracks, or files in Picard
2. Right-click and navigate to the fixed tag submenu
3. Select a specific tag to apply (e.g., "Add 'Lossy (MP3)' to GROUPING")

**Template Method:**
1. Select albums, tracks, or files in Picard
2. Right-click and navigate to the template submenu
3. Select a template to apply (e.g., "Apply Template: Source + Format")
4. The template will automatically populate the GROUPING field based on detected metadata

### Working with Templates

Templates allow you to create custom tagging patterns using variables that are automatically replaced with detected values.

**Available Template Variables:**
- `{SOURCE}` - Detected source (Vinyl, CD, Cassette, Digital)
- `{FORMAT}` - File format (MP3, FLAC, WAV, etc.)
- `{QUALITY}` - Quality tier (Lossy, Lossless, Hi-Def)
- `{BOOTLEG}` - Bootleg tag if detected
- `{REMASTER}` - Remaster tag if detected
- `{MANUAL}` - Manual/additional tags from settings

**Creating a Template:**
1. Go to Options → Plugins → Grouping Tagger
2. In the Templates section, click "Add Template"
3. Enter a template name (e.g., "Source + Format")
4. Click the variable buttons to copy them to clipboard (e.g., click `{SOURCE}`, click `{FORMAT}`)
5. Paste the variables into the template pattern field to build your pattern (e.g., `{SOURCE} | {FORMAT}`)
6. Set the divider character(s) (e.g., " | ")
7. Watch the live preview update as you build your template
8. Click OK to save

**Default Templates:**
- **Source + Format**: `{SOURCE} | {FORMAT}` (divider: " | ")
- **Source + Quality**: `{SOURCE} - {QUALITY}` (divider: " - ")
- **Full Info**: `{SOURCE}, {FORMAT}, {QUALITY}` (divider: ", ")
- **Simple Source**: `{SOURCE}` (divider: ", ")

**Managing Templates:**
- **Edit**: Select a template and click "Edit" to modify it
- **Delete**: Select a template and click "Delete" to remove it
- **Reset to Defaults**: Click "Reset to Defaults" to restore the default templates
- **Export JSON**: Save your templates to a JSON file for backup or sharing
- **Import JSON**: Load templates from a JSON file (merge or replace existing)

Templates are saved automatically to the JSON file and will appear in the right-click context menu for quick application (requires Picard restart for new/deleted templates).

### Managing Fixed Tags

Fixed tags are predefined tags that appear in the right-click menu for quick application.

**Default Fixed Tags:**
- Vinyl, CD, Digital, Bootleg
- MP3, FLAC, WAV, APE, AAC
- Lossy, Lossless, Hi-Def
- Remastered, Limited Edition, Japanese Import, Deluxe Edition

**Customizing Fixed Tags:**
1. Go to Options → Plugins → Grouping Tagger
2. Scroll to the "Fixed Tags (Right-Click Menu)" section
3. Select a tag and click "Edit" to change its value (e.g., change "Japanese Import" to "日本盤")
4. Click "Add Tag" to create new tags for your collection
5. Click "Delete" to remove tags you don't use
6. Click "Reset to Defaults" to restore original tags

Fixed tags are saved immediately and will appear in the right-click menu under "Add: [Tag Name]".

## Examples

### Auto-Detect Examples

With all detection enabled and separator ", ":

- Vinyl FLAC release (16-bit): `GROUPING = "Vinyl, Lossless (FLAC)"`
- Digital MP3 release: `GROUPING = "Digital, Lossy (MP3)"`
- Bootleg WAV release: `GROUPING = "Bootleg, Lossless (WAV)"`
- CD Remaster (24-bit): `GROUPING = "CD, Remastered, Hi-Def (FLAC)"`
- With additional tag "Limited Edition": `GROUPING = "Vinyl, Lossless (FLAC), Limited Edition"`

### Template Examples

Using the "Source + Format" template (`{SOURCE} | {FORMAT}` with divider " | "):
- Vinyl FLAC release: `GROUPING = "Vinyl | FLAC"`
- Digital MP3 release: `GROUPING = "Digital | MP3"`

Using the "Source + Quality" template (`{SOURCE} - {QUALITY}` with divider " - "):
- Vinyl FLAC 16-bit: `GROUPING = "Vinyl - Lossless"`
- Digital FLAC 24-bit: `GROUPING = "Digital - Hi-Def"`

Using the "Full Info" template (`{SOURCE}, {FORMAT}, {QUALITY}` with divider ", "):
- CD FLAC 24-bit Remaster: `GROUPING = "CD, FLAC, Hi-Def, Remastered"`

Custom template example (`{QUALITY} {FORMAT} [{SOURCE}]` with divider " "):
- Vinyl FLAC 16-bit: `GROUPING = "Lossless FLAC [Vinyl]"`

## Detection Logic

### Vinyl
Checks if the `media` field contains "vinyl"

### CD
Checks if the `media` field contains "cd" (excludes SACD)

### Cassette
Checks if the `media` field contains "cassette" or "tape"

### Bootleg
- Checks `releasestatus` field for "bootleg"
- Searches album and comment fields for keywords: "bootleg", "unofficial", "pirate"

### Digital
- Checks `media` field for: "digital", "download", "web", "streaming"
- If media is empty but format is digital (FLAC, MP3, etc.), marks as Digital

### Remaster
Searches album, comment, and version fields for keywords: "remaster", "remastered", "reissue"

### Quality Tier (Format)
Categorizes audio files based on format and technical specifications:

**Lossy Formats:**
- MP3, AAC, OGG Vorbis, WMA, Opus, MP2, AC3
- Tagged as: "Lossy (FORMAT)"

**Lossless Formats:**
- FLAC, ALAC, APE, WAV, AIFF, WavPack, TTA
- 16-bit depth or standard sample rates (44.1/48 kHz)
- Tagged as: "Lossless (FORMAT)"

**Hi-Def Formats:**
- FLAC, WAV, AIFF, or other lossless formats
- 24-bit depth OR sample rate ≥88.2kHz
- Tagged as: "Hi-Def (FORMAT)"

Format detection uses the `~format`, `~bits_per_sample`, and `~sample_rate` metadata fields

## Version History

### 3.1.0

- **Combined Export/Import**: Export and Import buttons now handle BOTH templates AND fixed tags in a single JSON file
- **New JSON Format**: Configuration file renamed to `grouping_tagger_config.json` with structure: `{"templates": [...], "fixed_tags": {...}}`
- **Main Page Integration**: Export/Import buttons moved from Template Manager dialog to main options page for easier access
- **One-Click Backup**: Export your complete plugin configuration (templates + fixed tags) with one button click
- **Smart Import**: Import dialog shows what will be imported and offers Merge or Replace options
- **Backward Compatible**: Automatically migrates legacy `grouping_tagger_templates.json` (template-only) files
- **Legacy Support**: Still supports importing old template-only JSON files from v3.0.0
- **Complete Configuration Storage**: Both templates and customized fixed tags are now preserved across plugin updates

### 3.0.0

- **JSON Storage**: Templates now stored in separate JSON file (`~/Library/Preferences/MusicBrainz/Picard/json/grouping_tagger_templates.json`)
- **Update-Safe**: Your templates are preserved when updating the plugin - no more lost configurations!
- **Import/Export**: Added "Import JSON" and "Export JSON" buttons to Template Manager for easy backup and sharing
- **Template Priority System**: Loads from JSON file first, falls back to Picard settings, then defaults
- **Easy Backup**: Simply copy the JSON file to backup all your custom templates
- **Version Control Friendly**: Keep your templates in git alongside your music library configuration
- **Manual Editing**: Advanced users can edit the JSON file directly and Picard will load it on startup
- **Migration Support**: Automatically migrates templates from older versions to new JSON format
- **Default Export Location**: Export dialog defaults to the standard JSON preferences folder
- **Merge or Replace**: Import dialog lets you choose to merge with existing templates or replace them entirely

### 2.1.0

- **Editable Fixed Tags**: Add, edit, and delete fixed tags from the options page
- **Custom Tag Management**: Create your own tags for the right-click "Add:" menu
- **Japanese Import Customization**: Edit any tag value (e.g., change "Japanese Import" to your preferred text)
- **Persistent Custom Tags**: All customizations saved and restored across Picard sessions
- **Reset to Defaults**: Easy option to restore original fixed tags if needed

### 2.0.0

- **Fixed Menu Names**: Template and fixed tag actions now display proper names instead of "Unknown"
- **Factory Function Architecture**: Implemented factory functions for dynamic action creation
- **Improved Code Organization**: Class-level NAME attributes for proper Picard recognition
- **Single-Word Submenu**: Simplified submenu to "Grouping" for cleaner menu structure
- **Better Picard Compatibility**: Follows Picard plugin best practices for action registration

### 1.9.0

- **Proper Submenu Implementation**: All actions now grouped under "Grouping Tagger" submenu
- **Cleaner Context Menu**: Right-click → Grouping Tagger (hover) → reveals all options
- **No More Clutter**: Eliminates scattered menu items and "Unknown" entries
- **Menu Structure**:
  - Grouping
    - Auto-Detect
    - Template: [Template Name]
    - Add: [Tag Name]

### 1.8.0

- **CHANNELS Variable Added**: New `{CHANNELS}` variable for audio channel detection (2.0, 5.1, 7.1, etc.)
- **Comprehensive Preview Examples**: Template editor now shows 4 different scenarios:
  - Vinyl rip (FLAC 24/96 stereo)
  - CD Bootleg (FLAC 16/44 stereo)
  - Lossy web file (MP3 stereo)
  - Digital multichannel (FLAC 24/192 5.1)
- **Simplified Template Editor**: Removed redundant divider field (templates now use automatic comma separation)
- **Better Context Menu Organization**: All actions now prefixed with `[Grouping]` for easy identification
- **Action Names Improved**:
  - Auto-Detect: `[Grouping] Auto-Detect`
  - Templates: `[Grouping] Template: [Name]`
  - Fixed Tags: `[Grouping] Add: [Tag]`

### 1.7.0

- **Enhanced Template Editor**: Completely redesigned template creation dialog
- **Click-to-Copy Variables**: Click any variable button to copy it to clipboard, then paste into your template
- **Live Preview with Real Detection**: Preview shows actual detection results using sample metadata
- **Multiple Preview Examples**: See how your template works with different scenarios (Vinyl, CD, Remaster, etc.)
- **Better Variable Descriptions**: Clear tooltips explain what each variable does
- **Improved UI**: Larger, more intuitive dialog with better layout and styling
- **Bug Fix**: Fixed template preview not working in previous version

### 1.6.0

- **Template System**: Create and manage custom templates with variable substitution
- **Template Variables**: Support for {SOURCE}, {FORMAT}, {QUALITY}, {BOOTLEG}, {REMASTER}, {MANUAL}
- **Template Editor**: Visual dialog for creating/editing templates with live preview
- **Template Actions**: Templates appear in context menu for quick application
- **Default Templates**: Four built-in templates (Source + Format, Source + Quality, Full Info, Simple Source)
- **Template Management**: Add, edit, delete, and reset templates to defaults

### 1.5.0

- Improved plugin stability and error handling
- Enhanced options page layout
- Better logging for debugging

### 1.3.0

- **Quality Tier Detection**: Format detection now categorizes by Lossy/Lossless/Hi-Def based on bit depth and sample rate
- **Enhanced Format Support**: Added detection for AAC, OGG, Opus, WavPack, AIFF, TTA, and more
- **Fixed Crash**: Resolved issue when clicking "Change Tag..." button in options page
- **Updated Fixed Tags**: Right-click menu now includes quality tier options

### 1.2.0

- Added CD, Cassette, and Remaster detection
- Matrix system: All detection rules independently toggleable
- Tag customization: Select or enter custom text for each detection type
- Fixed tag actions: Apply specific tags directly from right-click menu
- Live preview of tag combinations

### 3.1.2

- Picard 3.0 compatibility: `enable(api)` V3 API; actions registered via `api.register_*` with classes
- Fixed "name 'Qt' is not defined" error when importing the plugin on first run
- `TITLE` attribute added to all action classes for correct menu label display in Picard 3.0

### 1.0.0

- Initial release
- Vinyl, Bootleg, Digital, and Format detection
- Manual tags support
- Append mode
- Customizable separator

## License

MIT License

## Author

rpmzine
