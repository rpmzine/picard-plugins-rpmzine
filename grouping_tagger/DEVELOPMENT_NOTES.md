# Grouping Tagger Plugin - Development Session Summary

## Version 3.1.0 Development Notes

### Overview
Unified export/import system - single JSON file now handles both templates AND fixed tags together.

---

## Changes Made in This Session

### Version 3.0.0 → 3.1.0: Combined Export/Import System

**Goal**: Simplify backup/restore workflow by combining templates and fixed tags into a single JSON export file.

**Issue**: Users had to export templates and fixed tags separately, making configuration backup cumbersome.

**Solution**: Unified export/import that handles both in one file

#### Changes

1. **Unified Export Format**
   - Single JSON file structure:
     ```json
     {
       "templates": [...],
       "fixed_tags": [...]
     }
     ```
   - Export button now saves both templates AND fixed tags
   - Import button now restores both from single file

2. **Moved Export/Import to Main Page**
   - Relocated from Template Manager dialog to main options page
   - Easier access for users
   - More prominent placement for configuration backup

3. **Updated Documentation**
   - README updated to reflect combined export/import
   - Version bumped to 3.1.0

#### Key Files Modified
- `__init__.py`: Export/import logic, button placement
- `README.md`: Updated version to 3.1.0, changelog entry

#### Benefits
- **Single Backup File**: One file contains entire configuration
- **Easier Workflow**: No need to remember to export both separately
- **Better UX**: Export/Import buttons on main page (more accessible)
- **Complete Restore**: Import restores everything at once

---

## Version 3.0.0 Development Notes

### Overview
Major architecture change - moved from Picard internal settings to external JSON file storage.

---

## Changes Made in Previous Session

### Version 2.x → 3.0.0: JSON File Storage Migration

**Goal**: Store configuration in external JSON file for portability and better version control.

**Issue**: Configuration stored in Picard's internal QSettings was:
- Not easily portable between machines
- Difficult to back up
- Hard to inspect or edit manually

**Solution**: External JSON file at `~/Library/Preferences/MusicBrainz/Picard/json/grouping_tagger_config.json`

#### Changes

1. **JSON File Storage**
   - Templates stored in external JSON file
   - Fixed tags stored in same file
   - Detection matrix settings remain in Picard config

2. **Migration Logic**
   - Automatic migration from old settings to JSON file on first run
   - Preserves existing user configurations

3. **Export/Import Functionality**
   - Export templates to JSON file
   - Import templates from JSON file
   - Fixed tags export/import (initially separate)

#### Benefits
- **Portability**: Easy to copy configuration between machines
- **Version Control**: JSON file can be tracked in Git
- **Inspectability**: Easy to view/edit configuration manually
- **Backup**: Simple file-based backup

---

## Technical Implementation Details

### Configuration Storage

**JSON File Structure (v3.1.0+)**:
```json
{
  "templates": [
    {
      "name": "Template Name",
      "formula": "Formula String"
    }
  ],
  "fixed_tags": [
    "Tag 1",
    "Tag 2"
  ]
}
```

**File Location**:
- macOS: `~/Library/Preferences/MusicBrainz/Picard/json/grouping_tagger_config.json`
- Windows: `%APPDATA%\MusicBrainz\Picard\json\grouping_tagger_config.json`
- Linux: `~/.config/MusicBrainz/Picard/json/grouping_tagger_config.json`

### Detection System

The plugin uses a matrix-based detection system with the following variables:

**Source Detection Variables**:
- `<vinyl>` - Detects vinyl releases
- `<cd>` - Detects CD releases
- `<cassette>` - Detects cassette/tape releases
- `<digital>` - Detects digital/download releases
- `<bootleg>` - Detects bootleg releases

**Format Detection Variables**:
- `<format>` - General format (from media field)
- `<quality>` - Quality tier (Lossy/Lossless/Hi-Def)
- `<channels>` - Channel configuration (Mono/Stereo/5.1/etc.)

**Metadata Variables**:
- `<remaster>` - Detects remastered releases
- `<year>` - Release year
- `<country>` - Release country

### Quality Tier Detection

**Lossy**:
- MP3, AAC, OGG Vorbis, WMA, Opus, M4A
- Any lossy codec regardless of bitrate

**Lossless**:
- FLAC, ALAC, APE, WAV, AIFF
- Conditions: 16-bit depth OR 44.1/48kHz sample rate
- Standard CD quality or equivalent

**Hi-Def**:
- FLAC, WAV, AIFF, DSD
- Conditions: 24-bit depth OR ≥88.2kHz sample rate
- High-resolution audio

---

## Variables Reference

### All Available Variables

**Source Detection** (computed):
- `<vinyl>` - "Vinyl" if media contains vinyl
- `<cd>` - "CD" if media contains CD
- `<cassette>` - "Cassette" if media contains cassette/tape
- `<digital>` - "Digital" if media indicates digital source
- `<bootleg>` - "Bootleg" based on release status/keywords

**Format Information**:
- `<format>` - Media format from metadata
- `<quality>` - Quality tier (Lossy/Lossless/Hi-Def)
- `<channels>` - Channel config (Mono/Stereo/5.1/7.1/etc.)

**Metadata**:
- `<remaster>` - "Remaster" if detected
- `<year>` - Release year
- `<country>` - Release country
- `<label>` - Record label

---

## Key User Benefits

### Version 3.1.0 Benefits
1. **Unified Backup**: Single file contains entire configuration
2. **Easier Access**: Export/Import on main page (not hidden in dialog)
3. **Complete Restore**: Import restores templates + fixed tags together
4. **Simpler Workflow**: One export, one import - no separate steps

### Version 3.0.0 Benefits
1. **Portable Configuration**: JSON file easily copied between machines
2. **Version Control Friendly**: Can track config changes in Git
3. **Manual Editing**: JSON format easy to inspect and modify
4. **Better Backup**: Simple file-based backup strategy

---

## Testing Checklist

### Main Options Page
- [ ] Template list displays all templates
- [ ] Add Template button opens editor
- [ ] Edit Template button opens with template data
- [ ] Delete Template removes template
- [ ] Export Templates & Tags saves combined JSON file
- [ ] Import Templates & Tags loads both from file
- [ ] Fixed Tags section shows current tags
- [ ] Add/Remove Fixed Tag buttons work

### Template System
- [ ] Variables render correctly in formulas
- [ ] Detection rules work as expected
- [ ] Context menu shows all templates
- [ ] Applying template updates GROUPING field

### Detection Matrix
- [ ] Enable/disable checkboxes toggle detection
- [ ] Preview shows correct results
- [ ] Detection works for Vinyl/CD/Digital/etc.
- [ ] Quality tier detection accurate

### Export/Import
- [ ] Export creates valid JSON file
- [ ] Exported file contains both templates and fixed tags
- [ ] Import loads templates correctly
- [ ] Import loads fixed tags correctly
- [ ] Import validates JSON structure

---

## Files Modified

### Main Code
- `__init__.py` - Core plugin logic (~2700 lines)

### Documentation
- `README.md` - User documentation
- `DEVELOPMENT_NOTES.md` - This file (NEW)

---

## Version History Summary

- **3.0.0** - External JSON file storage, export/import functionality
- **3.1.0** - Combined export/import for templates and fixed tags, moved buttons to main page
- **3.1.1** - Minor patch (README not updated; check `__init__.py` diff for specifics)

---

## Known Issues / Limitations

1. **Template Menu Requires Restart**
   - Adding/deleting templates requires Picard restart
   - Picard API doesn't support dynamic menu item (un)registration
   - Formula changes work immediately

2. **Detection Accuracy**
   - Bootleg detection relies on keywords and release status
   - May have false positives/negatives
   - Users can override with manual tags

---

## Development Notes

### Code Organization
- Detection functions: Lines 50-200
- FormulaRenderer class: Lines 210-350
- TemplateEditorDialog: Lines 360-550
- Main Options Page: Lines 600-1200
- Action classes: Lines 1400-1600
- Export/Import: Lines 1250-1400
- Registration: Lines 2600-2700

### Best Practices Used
- Error handling with try/except
- User confirmations for destructive actions
- Settings persistence via JSON file
- Graceful fallbacks to defaults
- Comprehensive logging

---

## Contact / Continuation

When resuming development:
1. Review this document
2. Check `README.md` changelog for latest version
3. Test checklist above for regression testing
4. Check Git history for recent commits

Current stable version: **3.1.0**
Last modified: 2025-11-18
