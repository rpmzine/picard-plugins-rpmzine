# Suffix Appender Plugin

**Version:** 2.3.1
**Author:** rpmzine + contributors
**API Versions:** 2.10, 2.11, 2.12, 2.13
**License:** MIT

## Description

The Suffix Appender plugin allows you to append custom, formula-based suffixes to Album titles, Track titles, or Comment fields in MusicBrainz Picard. It provides a powerful yet user-friendly way to add technical information, regional details, and other metadata to your music files using a simple formula language with context menu activation.

**NEW in 2.1.0**: Completely redesigned interface inspired by the Grouping Tagger plugin, featuring a powerful Template Manager for unlimited customization, an intuitive Detection Matrix for auto-format rules, and streamlined configuration dialogs.

## Key Features

### 🎯 Template System (NEW!)
- **Template Manager**: Create, edit, and delete unlimited custom formula templates via an intuitive dialog
- **Click-to-Copy Variables**: Build formulas easily with clickable variable buttons that copy to clipboard
- **Live Preview**: See template results in real-time with sample metadata before saving
- **Flexible Formulas**: Use variables like `<releasecountry>`, `<format>`, `<bits_per_sample>`, `<channels>`, `<year>`, `<label>` with intelligent conditional rendering
- **Smart Physical Detection**: Use `<formatsize>` (vinyl size), `<mediatype>` (Vinyl/CD/Digital), `<recordtype>` (EP/LP/Single), and `<specialtype>` (Promo/WL/TP/Ltd) variables
- **Smart Transforms**: Apply transforms like `<var[:2]>` (slice), `<var|upper>`, `<var|lower>`, `<var|title>`, `<var|digits>`
- **Conditional Groups**: Use `[<var1> <var2>]` to only render groups when variables have values
- **Dynamic Menu**: All templates appear in the right-click menu for instant access

### ⚙️ Detection Matrix (NEW!)
- **Visual Configuration**: Configure auto-format detection rules (EP, Single, CD, Vinyl) via an intuitive grid interface
- **Custom Wrappers**: Customize how each format is wrapped (brackets, parentheses, etc.)
- **Enable/Disable**: Toggle individual detection rules on/off with checkboxes
- **Preview Examples**: See exactly how each rule will affect your album titles

### 🎨 Streamlined Interface
- **Large Action Buttons**: Two prominent buttons for "Manage Templates..." and "Configure Auto-Detection..."
- **Clean Layout**: Simplified options page inspired by Grouping Tagger's design
- **Separate Dialogs**: Each configuration aspect has its own dedicated dialog for clarity
- **Dark Mode Support**: Proper palette colors for readable text in all themes

### 🎵 Flexible Application
- **Multiple Target Fields**: Apply to Album titles, Track titles, and/or Comment fields simultaneously
- **Context Menu**: Apply templates directly from the right-click menu on albums, tracks, files, or clusters
- **Multi-Selection Support**: Batch processing for multiple items
- **Duplicate Prevention**: Smart detection to avoid re-applying the same suffix

## Installation

1. Copy the `suffix_appender` folder to your Picard plugins directory
2. Restart MusicBrainz Picard
3. Enable the plugin in Options → Plugins
4. Configure your preferences in Options → Plugins → Suffix Appender

## Usage

### Quick Start

1. **Open Options**: Go to Options → Plugins → Suffix Appender
2. **Select a Template**: Choose from the template list or create a new one
3. **Select Target**: Choose whether to append to Album or Track titles
4. **Apply**: Use the context menu to apply your selected template directly from right-click menu

### Formula Language

#### Variables
Variables are enclosed in angle brackets and map to metadata fields:

**Basic Metadata:**
| Variable | Maps To | Example Value |
|----------|---------|---------------|
| `<releasecountry>` | Country/region | "US", "UK", "Japan" |
| `<format>` | Format/media type | "FLAC", "MP3", "CD" |
| `<file_format>` | File format | "FLAC", "MP3", "AAC" |
| `<catalognumber>` | Catalog number | "ABC-123", "TOCP-12345" |
| `<bits_per_sample>` | Bit depth | "16", "24", "32" |
| `<sample_rate>` | Sample rate | "44100", "48000", "96000" |
| `<channels>` | Audio channels (raw count) | "1", "2", "6", "8" |
| `<channelconfig>` | Channel configuration | "Mono", "Stereo", "5.1", "7.1" |
| `<releasedate>` | Release date | "2023-01-15", "2023" |
| `<year>` | Release year | "2023", "1995" |
| `<originalyear>` | Original release year | "1967", "2001" |
| `<label>` | Record label | "Warner", "Sony Music" |

**Smart Detection Variables:**
| Variable | Description | Example Values |
|----------|-------------|----------------|
| `<formatsize>` | Vinyl size only | "12\"", "7\"", "10\"" |
| `<mediatype>` | Media type | "Vinyl", "CD", "Digital" |
| `<recordtype>` | Release type classification | "EP", "LP", "Single" |
| `<specialtype>` | Special edition indicators | "Promo", "WL", "TP", "Ltd" |
| `<channelconfig>` | Smart channel format | "Mono", "Stereo", "5.1", "7.1", "7.1.2" |

#### Transforms
Apply transforms using the pipe `|` operator or slice notation:

| Transform | Description | Example |
|-----------|-------------|---------|
| `<var\|upper>` | Convert to uppercase | `<format\|upper>` → "FLAC" |
| `<var\|lower>` | Convert to lowercase | `<format\|lower>` → "flac" |
| `<var\|title>` | Convert to title case | `<format\|title>` → "Flac" |
| `<var\|digits>` | Extract only digits | `<sample_rate\|digits>` → "96000" |
| `<var\|khz>` | Smart kHz formatting | `<sample_rate\|khz>` → "192" (from 192000), "44" (from 44100) |
| `<var[:2]>` | Take first N characters | `<sample_rate[:2]>` → "19" (not recommended for sample rates) |

#### Conditional Groups
Use square brackets `[...]` to create groups that only render when at least one variable has a value:

```
[<releasecountry> <format>]  # Only renders if country OR format exists
[<bits_per_sample>-<sample_rate[:2]>]  # Only renders if bits OR sample rate exists
```

### Formula Examples

| Formula | Input Metadata | Result |
|---------|---------------|--------|
| `[<releasecountry> <format>] [<bits_per_sample>-<sample_rate\|khz>]` | US, FLAC, 24-bit, 192kHz | `[US FLAC] [24-192]` |
| `[<releasecountry> <catalognumber> <format>]` | Japan, TOCP-12345, FLAC | `[Japan TOCP-12345 FLAC]` |
| `[<releasecountry> <formatsize> <recordtype>] [<specialtype>]` | US, 12" Vinyl, EP, Promo | `[US 12\" EP] [Promo]` |
| `[<format\|upper>] [<sample_rate\|khz>Hz]` | FLAC, 192000 | `[FLAC] [192Hz]` |
| `[<releasecountry>]` | United States | `[United States]` |

### Default Templates

The plugin includes 12 built-in default templates:

- **Country**: ` [<releasecountry>]`
- **Country+Size**: ` [<releasecountry> <formatsize>]`
- **Year Country Cat Format | Hi Res**: ` [<year[:4]> <releasecountry> <catalognumber> <format>] [<bits_per_sample>-<sample_rate|khz>]`
- **Multichannel**: ` [<format> <channels>ch]`
- **Remaster Year**: ` [<year[:4]>]`
- **SACD Hi Res**: ` [<format>] [<bits_per_sample>-<sample_rate|khz>]`
- **Format Hi-Res (Non Vinyl)**: ` [<format>] [<bits_per_sample>-<sample_rate|khz>]`
- **Country+Size & Resolution**: ` [<releasecountry> <formatsize>] [<bits_per_sample>-<sample_rate|khz>]`
- **Year Country**: ` [<year[:4]> <releasecountry>]`
- **Japanese CD**: ` [<releasecountry> JP CD]`
- **Japanese Special Format**: ` [<releasecountry> JP <format>]`
- **MFSL | AF**: ` [<label|mfsl_af>]`

These templates appear on first run and can be customized, deleted, or supplemented with your own templates using the **"Add Template"** button.

## Configuration Options

### Target Fields
- **Album Title**: Append suffix to album metadata
- **Track Title**: Append suffix to individual track titles  
- **Comment Field**: Append suffix to comment metadata
- **Multiple Selection**: Can target multiple fields simultaneously

### Behavior Options
- **Only append if suffix not already present**: Prevents duplicate suffixes (recommended)
- **EP/Single Detection**: Automatically detect and add " EP" or " [Single]" before formula suffixes
- **Context Menu Only**: Manual activation via right-click menu for precise control

### User Interface Features
- **Live Preview**: See how your formula renders with sample metadata in real-time
- **Template Selection**: Choose from the template list to see preview automatically update
- **Custom Formula Editor**: Larger, scrollable text area in the template editor dialog
- **Template Management**: Create, edit, and delete unlimited templates

### Advanced
- **Key Aliases**: Customize which metadata fields map to each variable (stored in JSON format)

## Context Menu Usage

### Applying Templates

1. Select albums, tracks, files, or clusters in Picard
2. Right-click → "Suffix Appender" → "[Template Name]"
3. The plugin will apply the selected template's formula to the items

**Menu Structure:**
- Suffix Appender (submenu)
  - Country
  - Country+Size
  - Year Country Cat Format | Hi Res
  - Multichannel
  - Remaster Year
  - SACD Hi Res
  - Format Hi-Res (Non Vinyl)
  - Country+Size & Resolution
  - Year Country
  - Japanese CD
  - Japanese Special Format
  - MFSL | AF
  - [Any Custom Templates You've Created]

## Examples in Action

### High-Resolution Album
- **Original**: "Kind of Blue"
- **Metadata**: Country=US, Format=FLAC, 24-bit, 96kHz
- **Formula**: `[<releasecountry> <format>] [<bits_per_sample>-<sample_rate[:2]>]`
- **Result**: "Kind of Blue [US FLAC] [24-96]"

### Japanese Import with Catalog Number
- **Original**: "Thriller"
- **Metadata**: Country=Japan, Catalog=32XD-123, Format=FLAC, 16-bit, 44.1kHz
- **Formula**: `[<releasecountry> <catalognumber> <format>] [<bits_per_sample>-<sample_rate[:2]>]`
- **Result**: "Thriller [Japan 32XD-123 FLAC] [16-44]"

### Missing Metadata Handling
- **Original**: "Abbey Road"
- **Metadata**: Country=UK, Sample Rate=44100 (no format or bit depth)
- **Formula**: `[<releasecountry> <format>] [<bits_per_sample>-<sample_rate[:2]>]`
- **Result**: "Abbey Road [UK] [44]"

### Vinyl Detection Examples
- **Original**: "The Dark Side of the Moon"
- **Metadata**: Country=US, Media="12\" Vinyl", Type=LP, no special indicators
- **Formula**: `[<releasecountry> <formatsize> <recordtype>] [<specialtype>]`
- **Result**: "The Dark Side of the Moon [US 12\" LP]"

- **Original**: "Love Me Do"
- **Metadata**: Country=UK, Media="7\" Vinyl", Type=Single, Comments="White Label Promo"
- **Formula**: `[<releasecountry> <formatsize> <recordtype>] [<specialtype>]`
- **Result**: "Love Me Do [UK 7\" Single] [White Label]"

### CD Format Examples
- **Original**: "Nevermind"
- **Metadata**: Country=US, Media=CD, Type=Album, Format=FLAC, 16-bit, 44.1kHz
- **Formula**: `[<releasecountry> <mediatype>] [<bits_per_sample>-<sample_rate|khz>]`
- **Result**: "Nevermind [US CD] [16-44]"

- **Original**: "Blue Train"
- **Metadata**: Country=Japan, Media=CD, Catalog=TOCJ-50001, Format=FLAC, Comments="SHM-CD"
- **Formula**: `[<releasecountry> <catalognumber> <format>] [<specialtype>]`
- **Result**: "Blue Train [Japan TOCJ-50001 FLAC] [SHM]"

### Digital Media Examples
- **Original**: "Random Access Memories"
- **Metadata**: Country=XW, Media=Digital, Format=FLAC, 24-bit, 96kHz
- **Formula**: `[<mediatype>] [<format>] [<bits_per_sample>-<sample_rate|khz>]`
- **Result**: "Random Access Memories [Digital] [FLAC] [24-96]"

- **Original**: "In Rainbows"
- **Metadata**: Country=XW, Media=Digital Media, Format=MP3, Type=Album, Year=2007
- **Formula**: `[<releasecountry> <mediatype> <year>]`
- **Result**: "In Rainbows [XW Digital 2007]"

## Technical Implementation

### Smart Rendering
- Empty variables don't render, preventing ugly gaps like "[ -44]"
- Whitespace is automatically normalized and cleaned up
- Conditional groups only appear if they contain actual content
- Orphaned spaces and punctuation are removed when variables are empty

### Metadata Resolution
The plugin uses configurable key aliases to find metadata values:
```json
{
  "releasecountry": ["releasecountry", "country"],
  "format": ["format", "releaseformat", "media"],
  "catalognumber": ["catalognumber", "catalognum"],
  "bits_per_sample": ["~bits_per_sample", "bit_depth"],
  "sample_rate": ["~sample_rate", "sample_rate"]
}
```

### Smart Detection Logic
**Vinyl Format Size Detection (`<formatsize>`):**
- Analyzes media field for patterns like "7\"", "12\"", "10\""
- Maps common formats: "7\" vinyl", "12-inch", "LP" → "12\""
- Only applies to vinyl releases, returns empty for CD/digital

**Record Type Detection (`<recordtype>`):**
- Uses `~primaryreleasetype` and `~secondaryreleasetype` fields
- Detects EP, LP, Single, Album classifications
- Independent of physical format

**Special Type Detection (`<specialtype>`):**
- Scans album title, comments, and description fields
- Detects: Promo, White Label, Test Pressing, Limited Edition
- Uses keyword matching with common abbreviations (WL, TP, etc.)

### Duplicate Prevention
- Uses regex pattern matching to detect existing trailing brackets
- Compares rendered formula with existing suffixes to prevent duplicates
- Maintains clean formatting even with multiple applications

## Troubleshooting

### Plugin Not Appearing
1. Ensure the plugin folder is in the correct location
2. Restart Picard after installation
3. Check that the plugin is enabled in Options → Plugins

### Formula Not Working
1. Check the syntax in the Options page
2. Verify that the required metadata fields exist in your files
3. Use the examples as templates for your own formulas
4. Check Picard's log for error messages

### Suffix Not Applied
1. Verify the target field setting (Album vs Track Title)
2. Check if duplicate prevention is blocking re-application
3. Ensure the formula renders to non-empty content
4. Try using the context menu manually first

## Advanced Usage

### Custom Key Aliases
You can modify the JSON configuration to map variables to different metadata fields. This is useful if your files use non-standard tag names.

### Customizing Detection Rules
The smart detection variables can be customized by modifying the plugin code:

**Special Type Abbreviations (`<specialtype>`):**
- Located in `_detect_special_type()` function around line 147
- Current abbreviations: "WL" (White Label), "TP" (Test Pressing), "Ltd" (Limited Edition)
- To change: modify the return statements (e.g., `return "WL"` → `return "White Label"`)

**Media Type Detection (`<mediatype>`):**
- Located in `_detect_media_type()` function around line 107
- Maps media field values to clean types (Vinyl, CD, Digital)
- To add new types: add conditions like `elif "cassette" in media: return "Cassette"`

**Vinyl Size Detection (`<formatsize>`):**
- Located in `MEDIA_SIZE_MAPPING` dictionary around line 44
- Maps vinyl format strings to size numbers
- To add formats: add entries like `"45rpm": "7"` to the mapping

**Record Type Classification (`<recordtype>`):**
- Located in `_detect_record_type()` function around line 122
- Maps MusicBrainz release types to user-friendly names
- To customize: modify the return statements (e.g., `return "LP"` → `return "Album"`)

### Multiple Formulas
Create unlimited templates for different scenarios and apply them directly from the context menu without changing any settings.

### Integration with Other Plugins
This plugin works well with:
- Audio File Info plugin (provides technical metadata)
- Persistent Variables plugin (for cross-session data)
- Other metadata enhancement plugins

## Changelog

### Version 2.3.1

- **Alphabetical Template Sorting**: Templates now appear in alphabetical order in the template list, context menu, and all dialogs
- **Multi-Value Tag Fix**: Fixed issue where FLAC tags could have duplicate values after saving - now properly replaces instead of appending
- **Better Tag Handling**: Uses `metadata.delete()` method to ensure complete tag replacement before setting new value
- **Debug Logging**: Enhanced logging for EP/Single detection to help diagnose detection issues

### Version 2.3.0

- **Legacy Code Removal**: Completely removed all legacy preset system code and configuration
- **Template System Only**: Plugin now exclusively uses the JSON-based template system
- **Simplified Architecture**: Removed `suffix_appender_custom_presets` setting and all preset-related methods
- **Default Templates**: The 12 default templates from DEFAULT_TEMPLATES are now the official starting point
- **Cleaner Codebase**: Eliminated redundant PRESETS dictionary and preset loading/saving logic
- **Better Maintainability**: Single source of truth for templates via JSON file and DEFAULT_TEMPLATES constant

### Version 2.2.2

- **Critical Bug Fix**: Fixed template deletion not persisting properly - deleted templates no longer reappear in context menu after restart
- **First-Run Initialization**: Templates are now properly initialized with defaults only on first run, using new `suffix_appender_templates_initialized` setting
- **Persistent User Changes**: Template deletions and modifications are now permanently saved and respected across restarts
- **Improved Logic**: Changed template loading to distinguish between "never initialized" vs "user deleted templates" states

### Version 2.2.1

- **Code Consolidation**: Unified preview examples into a single source of truth via `get_preview_examples()` function
- **Enhanced Preview Formats**: Added DSF (DSD64) Hi-Res example showing Direct Stream Digital taggeable files
- **Classical Music Example**: Added SACD Classical 4.0ch multichannel example (Beethoven's Symphony No. 9 at 24/88.2)
- **Main Page Live Preview**: Now shows all 6 comprehensive format examples (Vinyl, CD, Digital, DSF, SACD Classical, Multichannel 5.1)
- **Consistency Improvement**: Template Editor and Main Page previews now use identical example sets
- **Maintainability**: Single shared function ensures all preview displays stay synchronized

### Version 2.2.0

- **Major UI Redesign**: Complete restructuring of the options page for better usability
- **Template List on Main Page**: Templates now visible directly on main page with inline Add/Edit/Delete/Reset buttons
- **Removed Separate Dialog**: No more "Manage Templates" button - all template management is now on the main page
- **Variables Moved to Editor**: Available Variables and Variable Enhancers guide moved to the Add/Edit Template dialog where they're most useful
- **Live Preview Integration**: Preview automatically updates when selecting a template from the list
- **Cleaner Main Interface**: Main page now focused on template selection, preview, target fields, and options
- **Context Menu Cleanup**: Removed "Active Preset" menu item and "Preset:" prefix from template names for cleaner menus
- **Dynamic Template Reloading**: Modified template formulas take effect immediately without restarting Picard (only new/deleted templates require restart)
- **Instant Updates**: Template actions now read formulas dynamically from settings, allowing real-time formula changes

### Version 2.1.4

- **Bug Fix**: Fixed template formulas being trimmed on save, which removed intentional leading spaces needed to separate suffix from album title

### Version 2.1.3

- **New Variable**: Added `<originalyear>` variable separate from `<year>` for better control over release year vs original year
- **New Variable**: Added `<channelconfig>` smart variable that converts channel counts to friendly names (1→Mono, 2→Stereo, 6→5.1, 8→7.1, etc.)
- **UI Improvement**: Removed duplicate Auto Format Detection section from main options page (now only accessible via "Configure Auto-Detection..." button)
- **Variables Reference**: Restored comprehensive variables section on main options page with clickable buttons to copy variables
- **Variable Enhancers Guide**: Added visual reference for transforms (slice, upper, lower, title, digits, khz) directly on options page
- **Cleaner Interface**: Streamlined main options page by consolidating detection settings into dedicated dialog
- **Removed Legacy UI**: Removed "Quick select preset" dropdown from main page (use Template Manager for template management)
- **Enhanced Preview Examples**: Added multichannel surround sound example (5.1ch) to template previews alongside Vinyl, CD, and Digital
- **Better Channel Handling**: Raw `<channels>` variable returns numeric count, while `<channelconfig>` provides user-friendly format names

### Version 2.1.2

- **Enhanced Previews**: Template editor now shows examples for Vinyl, CD, and Digital formats simultaneously
- **Better Format Coverage**: Live preview demonstrates how formulas render across all major media types (Vinyl EP 24/192, CD Album 16/44, Digital Album 24/96)
- **Improved User Experience**: Users can now see comprehensive format examples when creating or editing templates instead of only vinyl-based examples
- **Fixed Preview Examples**: Both TemplateEditorDialog and legacy preset dialog now display multi-format previews

### Version 2.1.1

- **Documentation**: Added CD format examples showing standard CD rips and Japanese SHM-CD releases
- **Documentation**: Added Digital Media format examples demonstrating high-resolution and standard digital releases
- **Enhanced Examples**: Better coverage of different media formats beyond vinyl in README

### Version 2.1.0

- **Template Manager**: NEW! Complete template management system for creating, editing, and deleting unlimited formula templates
- **Detection Matrix**: NEW! Visual configuration dialog for auto-format detection rules with wrapper customization
- **Click-to-Copy Variables**: Build formulas easily with clickable variable buttons in template editor
- **Live Template Preview**: See template results with sample metadata before saving
- **Streamlined Interface**: Redesigned options page with large action buttons inspired by Grouping Tagger plugin
- **Separate Dialogs**: Dedicated dialogs for template management and detection configuration
- **Dynamic Menu Registration**: Templates automatically appear in right-click menu (requires restart)
- **Backward Compatibility**: Legacy preset system still supported alongside new template system
- **Dark Mode Support**: Proper palette colors in all dialogs for readability in dark themes

### Version 2.0.1

- **Dark Mode Fix**: Fixed readability issue in Variables section where text was unreadable in dark mode
- **UI Consistency**: Updated info banner styling to use palette colors for proper dark mode support
- **Preset Management**: Removed obsolete "Custom" preset from built-in presets protection list
- **Code Quality**: Ensured consistent built-in preset list across rename, delete, and save functions
- **Better User Experience**: Custom presets can now be properly renamed and deleted without restrictions

### Version 2.0.0

- **Fixed Menu Names**: Preset actions now display proper names instead of "Unknown"
- **Factory Function Architecture**: Implemented factory functions for dynamic action creation
- **Improved Code Organization**: Class-level NAME attributes for proper Picard recognition
- **Single-Word Submenu**: Simplified submenu to "Suffix" for cleaner menu structure
- **Better Picard Compatibility**: Follows Picard plugin best practices for action registration

### Version 1.5.0

- **Proper Submenu Implementation**: All actions now grouped under "Suffix Appender" submenu
- **Cleaner Context Menu**: Right-click → Suffix Appender (hover) → reveals all preset options
- **No More Clutter**: Eliminates scattered menu items and "Unknown" entries
- **Menu Structure**:
  - Suffix
    - Active Preset
    - Preset: [Preset Name]

### Version 1.4.0

- **Better Context Menu Organization**: All actions now prefixed with `[Suffix]` for easy identification
- **Action Names Improved**:
  - Active Preset: `[Suffix] Active Preset`
  - Preset Actions: `[Suffix] Preset: [Name]`
- **Groups all plugin actions together** in alphabetical sorting instead of scattered "Unknown" entries

### Version 1.3.0

- **Preset Context Menu**: Each saved preset now appears as a separate action in the right-click context menu
- **Quick Preset Switching**: Apply any preset directly from the context menu without changing your active preset in settings
- **Custom Preset Support**: All custom presets you create automatically appear in the context menu
- **Renamed Active Action**: The main action is now called "Append Suffix (Active)" to distinguish it from preset-specific actions
- **Enhanced Workflow**: Choose between using your configured active preset or quickly applying a specific preset for one-time use

### Version 1.2.0

- **Bug Fix**: Fixed preset persistence issue where newly created and edited presets were not saved when quitting Picard
- **Bug Fix**: Fixed preset deletion functionality - custom presets can now be properly deleted (built-in presets remain protected)
- **Bug Fix**: Fixed preset renaming issue where changes would be lost after restart
- **Bug Fix**: Fixed year variable behavior - `<year>` now returns just the year instead of full date (use `<year[:4]>` for explicit truncation)
- **Code Quality**: Removed dead code (`_add_modifiers_section` method that was never called)
- **Code Quality**: Fixed comment typos and simplified wrapper text logic
- **Persistence**: Added automatic saving of custom presets to Picard configuration
- **Enhanced Protection**: Built-in presets are now properly protected from deletion
- **Improved UX**: Custom presets are immediately saved when created or modified

### Version 1.1.0

- **Bug Fix**: Fixed EP duplication issue where EP was being added twice when already present in title
- **New Presets**: Added 4 new presets:
  - **Remaster Year**: `[<year[:4]>]` - For remaster information
  - **SHM & SACD**: `[<releasecountry> <catalognumber> <format>] [<bits_per_sample>-<sample_rate[:2]>]` - For high-quality Japanese releases
  - **Hi-Res**: `[<format>] [<bits_per_sample>-<sample_rate[:2]>]` - For high-resolution audio
  - **Country+Size & Resolution**: `[<releasecountry> <formatsize>] [<bits_per_sample>-<sample_rate[:2]>]` - For vinyl with audio specs
- **Preset Cleanup**: Removed redundant "Vinyl + Record Type" and "Default" presets
- **UI Improvement**: Added dedicated "Create New Preset..." button for better user experience
- **Enhanced EP Detection**: Improved logic to prevent duplicate EP markers in titles like "Kind of Blue EP"
- **Smart Sample Rate Formatting**: Added `|khz` transform for intelligent sample rate display (192000 → 192, 44100 → 44 instead of truncated "19")

### Version 1.0.0

- **Initial Release**: Complete MusicBrainz Picard plugin for appending custom suffixes to music metadata
- **Formula-Based Suffixes**: Powerful formula system with variables, transforms, and conditional groups
- **Smart Detection**: Automatic detection of vinyl sizes, media types, record types, and special editions
- **Multiple Target Fields**: Apply to Album titles, Track titles, and Comment fields simultaneously
- **Preset System**: Built-in presets for common use cases with live preview functionality
- **Context Menu Integration**: Manual activation via right-click for precise control
- **Dark Mode Support**: Full theme compatibility with proper styling
- **EP/Single Detection**: Automatic detection and prevention of duplicate markers
- **Live Preview**: Real-time formula preview with sample metadata
- **Duplicate Prevention**: Smart detection to avoid re-applying existing suffixes

## Contributing

This plugin is part of a larger collection of MusicBrainz Picard plugins. Contributions, bug reports, and feature requests are welcome.

## License

This plugin is released under the MIT License. See LICENSE file for details.

---

**Need Help?** Check the Options page for examples and syntax help, or refer to this README for detailed usage instructions.