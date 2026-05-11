# Tag Filter & Joiner Plugin

A MusicBrainz Picard plugin that allows you to ignore selected tags and/or join multi-value tags with custom separators.

## Features

- **Tag Filtering**: Completely remove unwanted tags from your music files
- **Multi-value Tag Joining**: Convert tags with multiple values into single-value tags using custom separators
- **Comprehensive Coverage**: Supports all 69 standard MusicBrainz tags
- **Customizable Separators**: Define your own separators for joining (default: " / ")
- **User-friendly Interface**: Easy-to-use options page in Picard's preferences

## Installation

1. Copy the `tag_filter_joiner` folder to your Picard plugins directory
2. Restart MusicBrainz Picard
3. Enable the plugin in Options > Plugins

## Usage

1. Go to **Options > Plugins > Tag Filter and Joiner**
2. For each tag, choose one of the following options:
   - **Ignore**: Check this to completely remove the tag from your files
   - **Join Multi-values**: Check this to combine multiple values into one using a separator
   - **Separator**: Specify the text to use when joining (only active when "Join Multi-values" is checked)

### Example Use Cases

**Multi-artist tracks**: If a song has multiple artists like ["Artist A", "Artist B"], enabling "Join Multi-values" for the "artist" tag with separator " feat. " would result in "Artist A feat. Artist B".

**Genre cleanup**: Join multiple genres like ["Rock", "Alternative", "Indie"] into "Rock / Alternative / Indie" using the default " / " separator.

**Tag removal**: Remove unwanted tags like "comment" or "website" by checking "Ignore" for those tags.

## Supported Tags

The plugin supports all standard MusicBrainz tags including:

- Basic tags: artist, album, title, date, genre
- Sorting tags: artistsort, albumsort, titlesort
- MusicBrainz IDs: musicbrainz_artistid, musicbrainz_albumid, etc.
- Technical tags: catalognumber, barcode, isrc, media
- Personnel tags: composer, conductor, performer, producer
- And many more...

## Configuration

Settings are automatically saved to Picard's configuration. Each tag has three associated settings:
- `tag_filter_ignore_{tagname}`: Boolean to ignore the tag
- `tag_filter_join_{tagname}`: Boolean to join multi-values
- `tag_filter_sep_{tagname}`: String separator for joining

## Technical Details

- **Version**: 0.9.5
- **API Compatibility**: Picard 2.10, 2.11, 2.12, 2.13, 3.0
- **License**: MIT
- **Processing**: Uses Picard's track metadata processor for real-time tag modification

## Troubleshooting

If the plugin doesn't appear in the options:
1. Ensure the plugin is properly installed in the plugins directory
2. Check that Picard has been restarted after installation
3. Verify the plugin is enabled in Options > Plugins

If you encounter errors, check Picard's log for diagnostic information.

## Author

Created by rpmzine

## License

This plugin is released under the MIT License.