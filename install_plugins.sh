#!/usr/bin/env bash
# Pulls each plugin from GitHub into Picard 3.0's plugins3 directory.
# Requires changes to be pushed first (via publish_plugins.sh).
#
# Usage:
#   bash install_plugins.sh                  # pull all plugins
#   bash install_plugins.sh suffix_appender  # pull one plugin only

set -euo pipefail

PLUGINS3=~/Library/Application\ Support/MusicBrainz/Picard/plugins3

PLUGINS=(
    "album_subfolder:b398e4bf-24f5-4ab5-a149-0ceacfb3cd32:picard-plugin-album-subfolder"
    "artwork_searcher:49b1d74a-c011-4b4a-914e-8c14a26c3d54:picard-plugin-artwork-searcher"
    "audio_file_info:365e1999-1db7-4abc-b572-f325c7b15ffb:picard-plugin-audio-file-info"
    "cluster_refresh:3ac9035d-541b-4c6f-923f-4704b4c478b3:picard-plugin-cluster-refresh"
    "grouping_tagger:54096269-4321-4772-8b12-ec6d25e1e376:picard-plugin-grouping-tagger"
    "multidisc_tagger:35162d2f-3604-46cc-958a-376c21ecf82e:picard-plugin-multidisc-tagger"
    "suffix_appender:723edd81-2dcf-473a-be28-4fd7fa004ce8:picard-plugin-suffix-appender"
    "tag_filter_joiner:86bdc092-6097-4ead-8d37-3e9128b6a7c1:picard-plugin-tag-filter-joiner"
)

FILTER="${1:-}"

for entry in "${PLUGINS[@]}"; do
    name="${entry%%:*}"
    rest="${entry#*:}"
    uuid="${rest%%:*}"
    repo="${rest##*:}"

    if [[ -n "$FILTER" && "$FILTER" != "$name" ]]; then
        continue
    fi

    dest="$PLUGINS3/${name}_${uuid}"

    if [[ -d "$dest/.git" ]]; then
        echo "Pulling $name"
        git -C "$dest" pull
    else
        echo "Cloning $name"
        git clone "https://github.com/rpmzine/${repo}.git" "$dest"
    fi
done

echo ""
echo "Done. Restart Picard."
