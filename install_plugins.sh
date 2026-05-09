#!/usr/bin/env bash
# Installs all plugins directly into Picard 3.0's plugins3 directory.
# Bypasses the "install from directory" UI (which requires a git repo).
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
PLUGINS3=~/Library/Application\ Support/MusicBrainz/Picard/plugins3

install_plugin() {
    local name="$1"
    local uuid="$2"
    local src="$REPO/$name"
    local dest="$PLUGINS3/${name}_${uuid}"

    echo "Installing $name -> $dest"
    mkdir -p "$dest"

    cp "$src/__init__.py"   "$dest/__init__.py"
    cp "$src/_compat.py"    "$dest/_compat.py"
    cp "$src/MANIFEST.toml" "$dest/MANIFEST.toml"

    # tag_filter_joiner has extra files
    for extra in options_tag_filter_joiner.py options_tag_filter_joiner.ui; do
        [[ -f "$src/$extra" ]] && cp "$src/$extra" "$dest/$extra"
    done

    # Remove stale bytecode
    rm -rf "$dest/__pycache__"
}

install_plugin album_subfolder  b398e4bf-24f5-4ab5-a149-0ceacfb3cd32
install_plugin artwork_searcher  49b1d74a-c011-4b4a-914e-8c14a26c3d54
install_plugin audio_file_info   365e1999-1db7-4abc-b572-f325c7b15ffb
install_plugin cluster_refresh   3ac9035d-541b-4c6f-923f-4704b4c478b3
install_plugin grouping_tagger   54096269-4321-4772-8b12-ec6d25e1e376
install_plugin multidisc_tagger  35162d2f-3604-46cc-958a-376c21ecf82e
install_plugin suffix_appender   723edd81-2dcf-473a-be28-4fd7fa004ce8
install_plugin tag_filter_joiner 86bdc092-6097-4ead-8d37-3e9128b6a7c1

echo ""
echo "Done. Restart Picard and enable each plugin in Plugins > Installed Plugins."
