# Suffix Appender Plugin - Development Session Summary

## Version 2.3.0 Development Notes

### Overview
Complete removal of legacy preset system - plugin now exclusively uses JSON-based template system.

---

## Changes Made in This Session

### Version 2.2.2 → 2.3.0: Legacy Preset System Removal

**Issue**: User reported that deleted templates ("Vinyl Promo" and "CD Promo") were still appearing in the context menu days after deletion, despite not being in the JSON file or Options page list.

**Root Cause**:
The plugin maintained two parallel systems for managing templates:
1. **New JSON-based template system** - Stored in external JSON file at `~/Library/Preferences/MusicBrainz/Picard/json/suffix_appender_templates.json`
2. **Legacy preset system** - Stored in Picard's internal QSettings via `suffix_appender_custom_presets` config option

The legacy preset system was loading deleted templates from Picard's internal settings, causing them to persist even after deletion from the JSON file.

**Solution**: Complete removal of legacy preset system

#### Changes:

1. **Removed Legacy Configuration Option** (`__init__.py:25`)
   - Deleted: `TextOption("setting", "suffix_appender_custom_presets", json.dumps({}))`
   - Plugin now only uses `suffix_appender_templates` for template storage

2. **Removed PRESETS Dictionary** (`__init__.py:1790-1807`)
   - Deleted entire `PRESETS` dictionary from `SuffixOptionsPage` class
   - Contained 15 hardcoded preset formulas for backward compatibility
   - No longer needed with JSON-based system

3. **Removed Preset Loading Method** (`__init__.py:1820-1826`)
   - Deleted `_load_custom_presets()` method
   - Previously merged custom presets from config into PRESETS dict
   - Unnecessary with single template system

4. **Removed Preset Saving Method** (`__init__.py:1828-1842`)
   - Deleted `_save_custom_presets()` method
   - Previously saved non-built-in presets back to config
   - No longer needed

5. **Removed Method Call in __init__** (`__init__.py:1813`)
   - Removed `self._load_custom_presets()` call from constructor
   - Simplified initialization

6. **Removed Legacy Registration Code** (`__init__.py:3365-3393`)
   - Deleted entire legacy preset registration block
   - Previously conditionally loaded presets if JSON file didn't exist
   - Replaced with single comment explaining removal

7. **Updated Plugin Version** (`__init__.py:5`)
   - Changed from "3.0.0" to "2.3.0"
   - Matches README changelog

#### Key Files Modified:
- `__init__.py`: Removed ~80 lines of legacy preset code
- `README.md`: Updated version to 2.3.0, replaced "Preset" terminology with "Template", added changelog entry
- `DEVELOPMENT_NOTES.md`: This section

#### Benefits:
- **Single Source of Truth**: Only JSON file for template storage
- **Cleaner Architecture**: Removed redundant configuration system
- **No More Ghost Templates**: Deleted templates stay deleted permanently
- **Better Maintainability**: Simpler codebase without dual systems
- **Reduced Confusion**: One clear way to manage templates

#### Template System Now:
- **DEFAULT_TEMPLATES** (12 templates) → Used only for first-run initialization
- **JSON File** → Persistent storage for all user templates
- **suffix_appender_templates_initialized** → Tracks if defaults have been loaded
- **No fallback to legacy system** → Clean template management

#### Testing Notes:
- Deleted templates should never reappear (fixed!)
- First run: Initializes with 12 DEFAULT_TEMPLATES
- Subsequent runs: Uses whatever is in JSON file
- Template modifications work immediately
- No Picard internal settings used for templates anymore

---

## Version 2.2.2 Development Notes

### Overview
Critical bug fix for template deletion persistence - templates deleted in UI were reappearing after restart.

---

## Previous Session Changes

### Version 2.2.1 → 2.2.2: Template Persistence Bug Fix

**Issue**: User reported that deleted templates were still appearing in the context menu after restart, even though they were removed from the Options page template list.

**Root Cause**:
The template registration code at startup (lines 2980-3011) was falling back to `DEFAULT_TEMPLATES` whenever the `suffix_appender_templates` setting was empty or couldn't be parsed. This meant:
- On first run → used DEFAULT_TEMPLATES (correct)
- After user deleted templates → setting might be empty → fell back to DEFAULT_TEMPLATES (incorrect!)
- User's deletions were not respected

**Solution**: Added proper first-run initialization tracking

#### Changes:

1. **New Configuration Setting** (`__init__.py:27`)
   - Added `BoolOption("setting", "suffix_appender_templates_initialized", False)`
   - Tracks whether templates have been initialized from defaults
   - Distinguishes "never initialized" from "user deleted everything"

2. **Updated Template Registration** (`__init__.py:2981-2994`)
   - Check if `suffix_appender_templates_initialized` is False
   - If False → initialize with DEFAULT_TEMPLATES and set flag to True
   - If True → use whatever is in settings (even if empty)
   - Removed fallback to DEFAULT_TEMPLATES after initialization

3. **Updated Options Page Loading** (`__init__.py:1892-1904`)
   - Same initialization check in `load_templates_to_list()`
   - Ensures Options page and context menu use same logic
   - Only falls back to defaults on true first run

#### Key Files Modified:
- `__init__.py`: Lines 27 (new setting), 1892-1904 (options page), 2981-2994 (registration)
- `README.md`: Updated version to 2.2.2, added changelog entry
- `DEVELOPMENT_NOTES.md`: This section

#### Benefits:
- **User Control**: Deleted templates stay deleted
- **Persistence**: User modifications respected across restarts
- **Clear Initialization**: Explicit tracking of first-run vs subsequent runs
- **No More Ghost Templates**: Context menu matches Options page exactly

#### Testing Notes:
- First run: Should initialize with all 14 DEFAULT_TEMPLATES
- Delete templates → Save → Restart: Deleted templates should NOT reappear
- Edit formulas: Should work immediately (already working from v2.2.0)
- Reset to Defaults button: Should restore all 14 templates

---

## Version 2.2.1 Development Notes

### Overview
Code consolidation and preview enhancement session to improve maintainability and add comprehensive format examples.

---

## Changes Made in This Session

### Version 2.2.0 → 2.2.1: Preview Consolidation & Format Expansion

**Goal**: Create single source of truth for preview examples and add DSF/SACD Classical formats

#### Changes:

1. **Created Shared Preview Function** (`__init__.py:239-308`)
   - New function `get_preview_examples()` returns standardized example set
   - Eliminates duplicate metadata definitions across codebase
   - Returns 6 comprehensive format examples:
     - Vinyl EP (24/192 stereo) - "Kind of Blue" by Miles Davis
     - CD Album (16/44 stereo) - "Nevermind" by Nirvana
     - Digital Album (24/96 stereo) - "Random Access Memories" by Daft Punk
     - **DSF Hi-Res (DSD64 stereo)** - "Time Out" by Dave Brubeck (NEW)
     - **SACD Classical (24/88 4.0ch)** - "Symphony No. 9" by Beethoven (NEW)
     - Multichannel (24/96 5.1ch) - "The Dark Side of the Moon" by Pink Floyd

2. **Updated TemplateEditorDialog.update_preview()** (`__init__.py:615-644`)
   - Now uses `get_preview_examples()` function
   - Renders all 6 examples in HTML format
   - Eliminates hardcoded metadata duplication

3. **Updated Main Page Live Preview** (`__init__.py:2048-2081`)
   - Function `update_preview_with_formula()` now uses shared examples
   - Shows all 6 formats in plain text format
   - Replaced ~70 lines of duplicate metadata with 15 lines calling shared function

4. **Added DSF Format Example**
   - Direct Stream Digital (DSD64) at 2.8MHz
   - Shows taggeable DSD file format
   - 24-bit/88.2kHz specs in metadata

5. **Added SACD Classical 4.0ch Example**
   - Multichannel classical music (4.0 surround)
   - Beethoven's Symphony No. 9
   - Deutsche Grammophon label
   - Shows orchestral/classical metadata patterns

#### Key Files Modified:
- `__init__.py`: Lines 239-308 (new shared function), 615-644 (template editor), 2048-2081 (main page preview)
- `README.md`: Updated version to 2.2.1, added changelog entry
- `DEVELOPMENT_NOTES.md`: This file (updated)

#### Benefits:
- **DRY Principle**: Single source of truth - update once, applies everywhere
- **Maintainability**: Changes to examples only need to be made in one place
- **Consistency**: All preview displays show identical format coverage
- **Comprehensive Coverage**: DSF and SACD Classical fill important format gaps
- **Code Reduction**: Eliminated ~140 lines of duplicate metadata definitions

---

## Previous Session Changes

### Version 2.1.2 → 2.1.3: Enhanced Preview Examples
**Goal**: Show CD, Digital, and Multichannel examples in template previews (not just vinyl)

#### Changes:
1. **Updated TemplateEditorDialog preview** (`__init__.py:487-556`)
   - Added 4 format examples: Vinyl EP, CD Album, Digital Album, Multichannel
   - Each shows different technical specs and metadata

2. **Updated PresetViewDialog preview** (`__init__.py:1053-1096`)
   - Same 4 format examples
   - Shows all formats in full preview text

3. **New Variables Added**:
   - `<originalyear>` - Separate from `<year>` for remaster tracking
   - `<channelconfig>` - Smart channel format detection

4. **Channel Configuration Detection** (`__init__.py:179-217`)
   - New function `_detect_channel_config()`
   - Maps channel counts to friendly names:
     - 1 → "Mono"
     - 2 → "Stereo"
     - 6 → "5.1"
     - 8 → "7.1"
     - 10 → "7.1.2"
     - 12 → "7.1.4"

#### Key Files Modified:
- `__init__.py`: Lines 179-217 (channel detection), 487-556 (template preview), 1053-1096 (preset preview)
- `README.md`: Added `<channelconfig>` to variables table, updated changelog

---

### Version 2.1.3 → 2.1.4: Bug Fix
**Issue**: Template formulas were being `.strip()`'d on save, removing intentional leading spaces

#### Fix:
- `__init__.py:603` - Removed `.strip()` from formula field
- Leading spaces now preserved (critical for proper spacing like " [US 12"]")

---

### Version 2.1.4 → 2.2.0: Major UI Redesign

#### Part 1: Main Options Page Redesign

**OLD Structure**:
```
- Header
- "Manage Templates..." button
- "Configure Auto-Detection..." button
- Live Preview (empty)
- Target Fields
- Options
- Variables section (click-to-copy)
```

**NEW Structure**:
```
- Header
- Templates (list widget with Add/Edit/Delete/Reset buttons)
  - Configure Auto-Detection button here
- Live Preview (updates when template selected)
- Target Fields
- Options
```

**Key Changes**:
1. **Template List Widget** (`__init__.py:1607-1644`)
   - Shows all templates directly
   - Inline management buttons
   - Selection triggers preview update

2. **Removed**:
   - "Manage Templates..." button (functionality integrated)
   - Variables section from main page (moved to editor)

3. **New Methods**:
   - `load_templates_to_list()` - Populates list from settings
   - `on_template_selected()` - Updates preview on selection
   - `add_template_click()` - Opens editor for new template
   - `edit_template_click()` - Opens editor for existing template
   - `delete_template_click()` - Removes template with confirmation
   - `reset_templates_click()` - Restores defaults
   - `save_templates_from_list()` - Persists to settings
   - `update_preview_with_formula()` - Shows preview for selected template

#### Part 2: Template Editor Dialog Enhancement

**Added to TemplateEditorDialog**:
1. **Variable Enhancers Guide** (`__init__.py:483-496`)
   - Shows all transform options
   - Slice: `<year[:4]>`
   - Upper/Lower/Title: `<format|upper>`
   - Digits: `<sample_rate|digits>`
   - kHz: `<sample_rate|khz>`

**Already Had**:
- Available Variables with click-to-copy buttons
- Multi-format preview examples

#### Part 3: Context Menu Improvements

1. **Removed "Active Preset"** (`__init__.py:2930-2931`)
   - Commented out registration
   - No longer needed with new UI

2. **Removed "Preset:" Prefix** (`__init__.py:2439`)
   - Changed from `NAME = f"Preset: {preset_name}"`
   - To `NAME = preset_name`
   - Cleaner menu appearance

3. **Dynamic Template Reloading** (`__init__.py:2451-2470`)
   - New method `_get_current_formula()`
   - Reads formula from settings each time action is called
   - **Modified formulas work immediately without restart!**
   - Only new/deleted templates require restart

#### Part 4: Settings & Persistence

1. **Track Template Changes** (`__init__.py:1553`)
   - Added `self.templates_changed = False` flag
   - Set to `True` when templates modified

2. **Save Notification** (`__init__.py:2420-2427`)
   - Informs users that formula changes work immediately
   - Notes that add/delete requires restart

---

## Technical Implementation Details

### Template Storage
- Templates stored in `config.setting["suffix_appender_templates"]` as JSON
- Format: `[{"name": "...", "formula": "..."}, ...]`
- Falls back to `DEFAULT_TEMPLATES` if empty

### Dynamic Formula Loading
```python
def _get_current_formula(self):
    """Get current formula for this template from settings"""
    templates_json = config.setting["suffix_appender_templates"]
    templates = json.loads(templates_json) if templates_json else []

    for template in templates:
        if template.get("name") == self.preset_name:
            return template.get("formula", "")

    # Fallback to DEFAULT_TEMPLATES
    for template in DEFAULT_TEMPLATES:
        if template.get("name") == self.preset_name:
            return template.get("formula", "")

    return ""
```

### Preview System
- Main page preview uses `update_preview_with_formula(formula)`
- Shows 2 examples: EP (vinyl) and Single (CD)
- Template editor shows 4 examples: Vinyl, CD, Digital, Multichannel

---

## Variables Reference

### All Available Variables

**Metadata Variables**:
- `<releasecountry>` - Country/region (US, UK, Japan)
- `<format>` - Format/media type (FLAC, MP3, CD)
- `<file_format>` - File format (FLAC, MP3, AAC)
- `<catalognumber>` - Catalog number
- `<bits_per_sample>` - Bit depth (16, 24, 32)
- `<sample_rate>` - Sample rate (44100, 96000)
- `<channels>` - Raw channel count (1, 2, 6, 8)
- `<channelconfig>` - Friendly channel format (Mono, Stereo, 5.1, 7.1)
- `<releasedate>` - Release date
- `<year>` - Release year
- `<originalyear>` - Original recording year
- `<label>` - Record label

**Smart Detection Variables** (computed):
- `<formatsize>` - Vinyl size only (12", 7", 10")
- `<mediatype>` - Media type (Vinyl, CD, Digital)
- `<recordtype>` - Release type (EP, LP, Single)
- `<specialtype>` - Special editions (Promo, WL, TP, Ltd)
- `<channelconfig>` - Channel configuration (NEW in 2.1.3)

**Variable Enhancers**:
- Slice: `<year[:4]>` - First 4 characters
- Upper: `<format|upper>` - FLAC
- Lower: `<format|lower>` - flac
- Title: `<format|title>` - Flac
- Digits: `<sample_rate|digits>` - Extract numbers only
- kHz: `<sample_rate|khz>` - Smart kHz (192000 → 192)

---

## Key User Benefits

### Version 2.2.0 Benefits:
1. **Faster Workflow** - Template list visible without opening dialog
2. **Live Preview** - See results immediately when selecting template
3. **Instant Formula Updates** - Edit and test without restart
4. **Cleaner Menus** - No "Preset:" prefix, no "Active Preset" clutter
5. **Better Organization** - Variables only in editor where needed
6. **Comprehensive Examples** - See Vinyl, CD, Digital, Multichannel previews

### What Works Without Restart:
✅ Editing template formulas
✅ Modifying existing templates
✅ Using updated formulas in context menu

### What Requires Restart:
⚠️ Adding new templates (new menu items)
⚠️ Deleting templates (remove menu items)
⚠️ Renaming templates (update menu names)

---

## Testing Checklist

### Main Options Page:
- [ ] Template list shows all templates
- [ ] Selecting template updates live preview
- [ ] Add Template opens editor dialog
- [ ] Edit Template opens with template data
- [ ] Delete Template removes with confirmation
- [ ] Reset to Defaults restores DEFAULT_TEMPLATES
- [ ] Live preview shows 6 format examples (Vinyl, CD, Digital, DSF, SACD, Multichannel)

### Template Editor Dialog:
- [ ] Variables section shows all variables
- [ ] Click-to-copy works for variables
- [ ] Variable Enhancers guide displays
- [ ] Preview shows 6 format examples (Vinyl, CD, Digital, DSF, SACD, Multichannel)
- [ ] Leading spaces preserved in formula
- [ ] OK saves template to list

### Context Menu:
- [ ] No "Active Preset" item appears
- [ ] Template names appear without "Preset:" prefix
- [ ] Selecting template applies correct formula
- [ ] Modified formulas work immediately
- [ ] New templates appear after restart

### Dynamic Reloading:
- [ ] Edit template formula → OK → Use context menu → New formula applied
- [ ] No restart needed for formula changes
- [ ] Message shows explaining immediate effect

---

## Files Modified

### Main Code:
- `__init__.py` - All core functionality (~2600 lines)

### Documentation:
- `README.md` - Updated variables table, changelog
- `DEVELOPMENT_NOTES.md` - This file (NEW)

---

## Future Enhancements (Not Implemented)

### Ideas Discussed:
1. **Mono Detection** - Detect dual-mono (2 identical channels) from mono source
   - Decision: Manual tagging better (track-by-track scenario)
   - Users can use custom tags or comments

2. **Full Dynamic Menu** - Register/unregister actions dynamically
   - Picard API limitation: No clean unregister mechanism
   - Current solution (read formula dynamically) is sufficient

---

## Version History Summary

- **2.1.2** - Enhanced preview examples (Vinyl, CD, Digital)
- **2.1.3** - Added `<originalyear>` and `<channelconfig>`, multichannel examples
- **2.1.4** - Fixed formula trimming bug (preserve leading spaces)
- **2.2.0** - Major UI redesign, dynamic template reloading, context menu cleanup
- **2.2.1** - Code consolidation with shared preview function, added DSF and SACD Classical examples
- **2.2.2** - Critical bug fix: template deletion persistence (templates no longer reappear after restart)
- **2.3.0** - Complete removal of legacy preset system, single source of truth for templates via JSON
- **2.3.1** - Alphabetical template sorting in list/menu; fixed multi-value FLAC tag duplication (now uses `metadata.delete()` before setting); enhanced EP/Single detection logging
- **2.4.0** - Added `_notify_metadata_changes()` and enhanced `_iter_unique_metadata_with_objects()`: plugin now triggers proper Picard UI refresh (file, track, album `.update()` calls + `metadata_changed` signals) after applying suffixes, so changes are visible in Picard without reloading

---

## Known Issues / Limitations

1. **Adding/Deleting Templates** - Still requires Picard restart for menu items
   - Reason: Picard plugin API doesn't allow dynamic action (un)registration
   - Mitigation: Formula changes work immediately

2. **Mono Detection** - Cannot auto-detect dual-mono files
   - Reason: Would need audio waveform analysis
   - Mitigation: Users can manually tag or use comments

---

## Development Notes

### Code Organization:
- Helper functions (detection, metadata): Lines 84-217
- FormulaRenderer class: Lines 239-405
- TemplateEditorDialog: Lines 398-604
- TemplateManagerDialog: Lines 607-801
- PresetViewDialog: Lines 804-1248
- DetectionMatrixDialog: Lines 1251-1485
- SuffixOptionsPage: Lines 1526-2437
- Action classes: Lines 2438-2527
- Registration: Lines 2930-2987

### Best Practices Used:
- Error handling with try/except blocks
- Logging for debugging
- User confirmations for destructive actions
- Settings persistence to config
- Graceful fallbacks (defaults)
- Comments explaining key decisions

---

## Contact / Continuation

When resuming development:
1. Review this document
2. Check `README.md` changelog for latest version
3. Test checklist above for regression testing
4. Check Git history for recent commits

Current stable version: **2.4.0**
Last modified: 2026-04-25
