# Multidisc Tagger Plugin

**Version:** 2.6.0
**Author:** rpmzine  
**API Versions:** 2.10, 2.11, 2.12, 2.13  
**License:** Not specified

## Description

The Multidisc Tagger plugin enhances multidisc releases by applying classical music-style tagging conventions. It works in two ways:

1. **Automatic Detection**: When MusicBrainz has disc subtitles, it automatically applies Work/Movement tagging
2. **Manual Creation**: NEW! Use the context menu "Make it a Multidisc" to manually create disc subtitles and organization even when MusicBrainz doesn't have them

## Key Features

### 🎵 Classical Music-Style Tagging + M4A Atom Tags
- **Work Tag**: Populated with disc subtitle (automatic or manual)
- **Movement Tag**: Uses the original track title as the movement
- **Show Movement**: Enables movement display in compatible players
- **M4A Atom Tags**: Direct @wrk, @mvn, @shwm atoms added to FLAC for perfect M4A conversion
- **Perfect Organization**: Groups tracks by disc in classical music players like Roon

### 🆕 Manual Multidisc Creation
- **Context Menu Action**: "Make it a Multidisc" option for albums with multiple discs
- **Interactive Dialog**: Easy-to-use interface for entering disc subtitles
- **Quick Presets**: "CD 1, CD 2..." and "Disc 1, Disc 2..." preset buttons
- **Flexible Input**: Leave subtitles empty for discs that don't need them
- **Intelligent Detection**: Automatically detects disc count from metadata

### 🎯 Smart Multidisc Handling
- **Conditional Processing**: Only processes tracks that are part of multidisc releases
- **Preserves Original Data**: Maintains existing track titles while adding organizational structure
- **Universal Player Compatibility**: Works with ALL music players through multiple tagging strategies
- **Format Independence**: Maintains disc organization when converting between FLAC, M4A, MP3, etc.
- **Dual Mode**: Works automatically OR manually via context menu

### ⚙️ Seamless Integration
- **Background Processing**: Automatic processing requires no intervention
- **Manual Control**: Context menu for manual creation when needed
- **Metadata Processor**: Integrates directly with Picard's metadata processing pipeline
- **UI Updates**: Real-time updates to track display after manual creation

## How It Works

The plugin uses MusicBrainz's disc subtitle information to create a hierarchical structure:

```
Original Release Structure:
├── Disc 1: "The Hits"
│   ├── Track 1: "Song A"
│   └── Track 2: "Song B"
└── Disc 2: "Rarities"
    ├── Track 1: "Demo C"
    └── Track 2: "B-Side D"

After Plugin Processing:
├── Work: "The Hits"
│   ├── Movement: "Song A" (showmovement: 1)
│   └── Movement: "Song B" (showmovement: 1)
└── Work: "Rarities"
    ├── Movement: "Demo C" (showmovement: 1)
    └── Movement: "B-Side D" (showmovement: 1)
```

## Installation

1. Copy the `multidisc_tagger` folder to your Picard plugins directory
2. Restart MusicBrainz Picard
3. The plugin will be automatically active (no configuration required)

## Usage

The plugin works in two modes: **Automatic** and **Manual**.

### Automatic Mode
Works in the background when MusicBrainz has disc subtitle information.

#### When It Activates
- The release has multiple discs with disc subtitles
- MusicBrainz provides `discsubtitle` metadata
- The track is being processed by Picard's metadata pipeline

### Manual Mode (NEW!)
Use the context menu when MusicBrainz lacks disc subtitle information.

#### How to Use Manual Mode
1. **Select Album or Cluster**: Right-click on an album (post-processing) or cluster (pre-processing) in Picard
2. **Choose Action**: Select "Make it a Multidisc" from the context menu
3. **Check Requirements**: Plugin verifies the album has multiple discs
4. **Enter Subtitles**: A dialog opens showing one input field per disc
5. **Use Presets** (optional): Click "CD 1, CD 2..." or "Disc 1, Disc 2..." for quick setup
6. **Confirm**: Click OK to apply the disc subtitles
7. **Automatic Processing**: Work/Movement tags are immediately applied

#### Manual Mode Requirements
- Album or cluster must have `discnumber > 1` or `totaldiscs > 1`
- Plugin only shows the option for genuine multidisc releases
- **Works in both contexts**: Pre-processing (clusters) and post-processing (albums)

### What Both Modes Do
For each eligible track:
1. **Sets Work**: `work = discsubtitle` (from MusicBrainz or user input)
2. **Sets Movement**: `movement = original track title`
3. **Enables Movement Display**: `showmovement = "1"`
4. **Sets Total Discs**: `totaldiscs = maximum disc number` (ensures proper multidisc identification)

## Example Transformations

### Automatic Mode Example

#### Before Plugin
```
Album: "Greatest Hits Collection"
Disc: 1
Disc Subtitle: "The Early Years" (from MusicBrainz)
Title: "First Hit Song"
```

#### After Plugin (v2.5.0+)
```
Album: "Greatest Hits Collection"
Work: "The Early Years"
Movement: "First Hit Song"
Show Movement: 1
@wrk: "The Early Years"     <- M4A Work atom
@mvn: "First Hit Song"      <- M4A Movement atom  
@shwm: 1                    <- M4A Show Movement atom
Title: "First Hit Song" (unchanged)
```

### Manual Mode Example

#### Before Manual Action
```
Album: "Complete Studio Albums"
Disc: 1, Title: "Thriller"
Disc: 2, Title: "Bad" 
Disc: 3, Title: "Dangerous"
(No disc subtitles in MusicBrainz)
```

#### User Action
1. Right-click album → "Make it a Multidisc"
2. Dialog shows:
   - Disc 1: [Enter subtitle] → User types "Thriller (1982)"
   - Disc 2: [Enter subtitle] → User types "Bad (1987)"  
   - Disc 3: [Enter subtitle] → User types "Dangerous (1991)"
3. Click OK

#### After Manual Action
```
Disc 1 tracks:
- Work: "Thriller (1982)"
- Movement: "Billie Jean", "Beat It", etc.

Disc 2 tracks:  
- Work: "Bad (1987)"
- Movement: "Bad", "Smooth Criminal", etc.

Disc 3 tracks:
- Work: "Dangerous (1991)" 
- Movement: "Black or White", "Remember the Time", etc.
```

## Benefits

### For Music Organization
- **Logical Grouping**: Disc subtitles become meaningful organizational units
- **Enhanced Navigation**: Players can display multidisc releases hierarchically
- **Better Browsing**: Easier to navigate large box sets and compilations

### For Music Players
- **iTunes/Music.app**: Shows Work > Movement hierarchy in library views
- **Classical Music Apps**: Proper handling of multidisc classical releases
- **Advanced Players**: Better organization in players that support Work/Movement tags

### For Different Release Types
- **Box Sets**: Each disc becomes a distinct "work" with track "movements"
- **Compilations**: Thematic discs (e.g., "Ballads", "Rock Hits") become organized units
- **Classical Releases**: Proper structure for multi-disc classical works
- **Soundtracks**: Disc-based organization for multi-disc soundtracks

## Technical Implementation

### Track Metadata Processor
```python
def set_multidisc_tags_track(tagger, metadata, track, release):
    discsubtitle = metadata.get("discsubtitle")
    if not discsubtitle:
        return
    
    metadata["work"] = discsubtitle
    metadata["showmovement"] = "1"
    title = metadata.get("title")
    if title:
        metadata["movement"] = title
```

### Key Technical Details
- **Conditional Processing**: Only runs when `discsubtitle` exists
- **Non-Destructive**: Preserves original `title` field
- **Automatic Registration**: Self-registers with Picard's metadata processing system
- **Error Handling**: Gracefully handles missing or empty fields

## Compatibility

### MusicBrainz Picard
- **API Version**: 2.10
- **Metadata Pipeline**: Integrates with track metadata processors
- **Release Processing**: Works with standard Picard release processing

### Music Players
- **iTunes/Music.app**: Full Work/Movement support
- **Classical Music Players**: Enhanced organization for multidisc releases
- **Generic Players**: May display Work and Movement as additional metadata fields

### Release Types
- **Multi-disc Albums**: Primary use case
- **Box Sets**: Excellent for organizing large collections
- **Classical Music**: Proper handling of multi-disc classical works
- **Compilations**: Thematic organization by disc subtitle

## Troubleshooting

### Plugin Not Working (Automatic Mode)
1. **Check Disc Subtitles**: The plugin only works when MusicBrainz has disc subtitle information
2. **Try Manual Mode**: Use "Make it a Multidisc" from the context menu
3. **Verify Installation**: Ensure the plugin folder is in the correct Picard plugins directory
4. **Restart Picard**: Plugin changes require a restart to take effect

### Context Menu Not Showing
1. **Select Album**: Make sure you're right-clicking on an album, not individual tracks
2. **Multiple Discs**: The option only appears for albums with multiple discs
3. **Check Disc Numbers**: Verify tracks have `discnumber > 1` or `totaldiscs > 1`

### Manual Mode Issues
1. **Dialog Not Opening**: Ensure the album actually has multiple discs
2. **No Changes Applied**: Check that you entered at least one disc subtitle
3. **Subtitles Not Saving**: Make sure to click OK, not Cancel
4. **UI Not Updating**: Try refreshing the track list or reloading the album

### Missing Work/Movement Tags
1. **Single Disc Releases**: Plugin doesn't activate for single-disc releases
2. **No Disc Subtitles**: For automatic mode, MusicBrainz must have disc subtitle metadata
3. **Player Support**: Ensure your music player supports Work/Movement tags
4. **Try Manual Mode**: Create disc subtitles manually if MusicBrainz lacks them

### Unexpected Behavior
1. **Check Metadata**: Use Picard's metadata view to verify Work/Movement tags are set
2. **Player Settings**: Some players may need settings enabled to show Work/Movement
3. **File Format**: Ensure your audio format supports the additional metadata fields
4. **Mixed Modes**: Manual subtitles override automatic ones from MusicBrainz

## Use Cases

### Classical Music Collections
Perfect for multi-disc classical releases where each disc represents a different work or collection of pieces.

### Box Sets and Compilations
Organizes themed discs within large compilation releases, making navigation much easier.

### Soundtrack Collections
Multi-disc soundtracks benefit from disc-based organization (e.g., "Score", "Songs", "Bonus Material").

### Genre Collections
Compilation albums organized by genre or era benefit from the hierarchical structure.

## Advanced Usage

### Custom Workflows
The plugin works automatically, but you can combine it with:
- **Other Plugins**: Works alongside other metadata enhancement plugins
- **Custom Scripts**: Can be part of larger automated tagging workflows
- **Batch Processing**: Processes all multidisc releases in batch operations

### Player Configuration
Different players may display Work/Movement tags differently:
- **iTunes**: Shows in Album view as Work > Movement
- **Foobar2000**: Can be configured to display in custom column layouts
- **MediaMonkey**: Shows in detailed metadata views

## Contributing

This plugin is part of a larger collection of MusicBrainz Picard plugins. Contributions, bug reports, and feature requests are welcome.

### Potential Enhancements
- **Configuration Options**: Allow users to customize tag mapping
- **Alternative Tag Schemes**: Support for different organizational approaches
- **Extended Compatibility**: Support for additional MusicBrainz API versions
- **Custom Formatting**: User-definable Work/Movement formatting

## Direct M4A Atom Tag Support

The plugin now writes both standard tags AND direct M4A atom tags to FLAC files:

**Standard Tags** (for FLAC/classical players):
- `work` → Work
- `movement` → Movement  
- `showmovement` → Show Movement

**M4A Atom Tags** (for perfect conversion):
- `@wrk` → Work atom (preserved in FLAC → M4A conversion)
- `@mvn` → Movement atom (preserved in FLAC → M4A conversion)
- `@shwm` → Show Movement atom (preserved in FLAC → M4A conversion)

This ensures that conversion tools can properly transfer the M4A atoms during format conversion, maintaining Work/Movement functionality in Apple Music.

## Changelog

### Version 2.6.0
- **Bug Fix**: Removed invalid `@wrk`/`@mvn`/`@shwm` tag names — these are not recognised by Picard and were preventing Work/Movement from being written correctly to M4A/AAC files
- **Correct behaviour**: Picard now translates the standard `work`/`movement`/`showmovement` keys to the proper format-native tags automatically: `WORK`/`MOVEMENTNAME`/`SHOWMOVEMENT` for FLAC (Vorbis), `©wrk`/`©mvn`/`shwm` for M4A/AAC
- **Music.app**: Work/Movement hierarchy now correctly visible in Apple Music for M4A files
- **Metadatics**: FLAC files no longer contain spurious atom-style tags
- **Yate**: "Work Title" (`©wrk`) and "Movement Name" (`©mvn`) now correctly populated in M4A files

### Version 2.5.1
- **Partial Fix**: Added `~format` check to skip `@wrk` atoms for FLAC (incomplete — see 2.6.0)

### Version 2.5.0
- **Reverted in 2.6.0**: Attempted to add `@wrk`/`@mvn`/`@shwm` atoms to FLAC files for conversion compatibility — caused Metadatics breakage and M4A Work/Movement failure

### Version 2.4.0
- **Bug Fix**: Fixed grammar in error messages - "disc" vs "discs" based on count
- **Bug Fix**: Improved disc number handling to avoid defaulting to 1 when disc number is missing
- **Code Quality**: Better null checking for disc number metadata to prevent incorrect multidisc detection
- **Robustness**: Enhanced error handling for missing or invalid disc number values

### Version 2.3.0
- **NEW: Total Discs Metadata**: Automatically sets `totaldiscs` field when applying disc subtitles
- **Improved Compatibility**: Ensures proper multidisc identification even when `totaldiscs` is missing
- **Complete Metadata**: Now sets all required fields: `work`, `movement`, `showmovement`, and `totaldiscs`

### Version 2.2.1
- **UI Fix**: Fixed button layout wrapping issue in Create Multidisc Subtitles dialog
- **Improved Layout**: Reorganized dialog buttons into two rows to prevent cutoff at narrow widths
- **Better UX**: Preset buttons and OK/Cancel buttons now properly positioned and always visible

### Version 2.2.0
- **UI Enhancement**: Input fields now expand horizontally with dialog window
- **Non-Modal Dialog**: Dialog can stay open while navigating Picard to reference disc information
- **Smart Dialog Management**: Prevents duplicate dialogs and brings existing ones to front
- **Better Workflow**: Can browse albums/tracks while dialog is open to get disc names

### Version 2.1.0
- **NEW: Cluster Support**: Context menu now works in both pre-processing (clusters) and post-processing (albums)
- **Enhanced Error Handling**: Improved plugin loading with better error reporting and logging
- **Bug Fixes**: Fixed context menu registration issues that prevented the action from appearing
- **Debugging Improvements**: Added comprehensive logging for troubleshooting
- **Code Refactoring**: Improved object type handling for better reliability

### Version 2.0.0
- **NEW: Manual Multidisc Creation**: Added "Make it a Multidisc" context menu option
- **Interactive Dialog**: User-friendly interface for entering disc subtitles
- **Quick Presets**: "CD 1, CD 2..." and "Disc 1, Disc 2..." preset buttons
- **Smart Detection**: Automatically detects disc count from album metadata
- **Dual Mode Operation**: Works automatically (when MusicBrainz has data) OR manually (user-created)
- **Enhanced API Support**: Now supports Picard API versions 2.10-2.13
- **Improved Error Handling**: Better user feedback and error messages
- **Real-time Updates**: Immediate UI refresh after manual subtitle creation

### Version 1.4 
- Support for MusicBrainz Picard API 2.10
- Automatic Work/Movement tagging for multidisc releases
- Classical music-style organization
- Background processing with no user interaction required

## License

License information not specified in the current version.

---

**Need Help?** This plugin works automatically with no configuration required. If you're not seeing Work/Movement tags, ensure your releases have disc subtitles in MusicBrainz and that your music player supports these tags.