#!/usr/bin/env bash
# Copies updated plugin files from this monorepo into each plugin's individual
# GitHub repo and pushes. Run after making changes in the monorepo.
#
# Usage:
#   bash publish_plugins.sh                  # publish all plugins
#   bash publish_plugins.sh suffix_appender  # publish one plugin only

set -euo pipefail

MONOREPO="$(cd "$(dirname "$0")" && pwd)"
GITPROJECTS=~/GitProjects

PLUGINS=(
  "album_subfolder:picard-plugin-album-subfolder"
  "artwork_searcher:picard-plugin-artwork-searcher"
  "audio_file_info:picard-plugin-audio-file-info"
  "cluster_refresh:picard-plugin-cluster-refresh"
  "grouping_tagger:picard-plugin-grouping-tagger"
  "multidisc_tagger:picard-plugin-multidisc-tagger"
  "suffix_appender:picard-plugin-suffix-appender"
  "tag_filter_joiner:picard-plugin-tag-filter-joiner"
)

publish_one() {
    local plugin="$1"
    local repo="$2"
    local src="$MONOREPO/$plugin"
    local dest="$GITPROJECTS/$repo"

    if [[ ! -d "$dest/.git" ]]; then
        echo "ERROR: $dest is not a git repo. Run the initial setup first." >&2
        return 1
    fi

    echo "Publishing $plugin → $repo"

    cp "$src/__init__.py"   "$dest/"
    cp "$src/_compat.py"    "$dest/"
    cp "$src/MANIFEST.toml" "$dest/"
    cp "$src/README.md"     "$dest/"
    [[ -f "$src/DEVELOPMENT_NOTES.md" ]] && cp "$src/DEVELOPMENT_NOTES.md" "$dest/"
    for extra in options_tag_filter_joiner.py options_tag_filter_joiner.ui; do
        [[ -f "$src/$extra" ]] && cp "$src/$extra" "$dest/"
    done

    # Detect version from __init__.py
    local version
    version=$(grep 'PLUGIN_VERSION' "$dest/__init__.py" | head -1 | sed 's/.*= *"\(.*\)".*/\1/')

    git -C "$dest" add .
    if git -C "$dest" diff --cached --quiet; then
        echo "  No changes in $plugin, skipping commit."
        return 0
    fi

    git -C "$dest" commit -m "v${version}"
    git -C "$dest" tag -f "v${version}"
    git -C "$dest" push origin main
    git -C "$dest" push origin "v${version}" --force
    echo "  Pushed v${version}"
}

FILTER="${1:-}"

for entry in "${PLUGINS[@]}"; do
    plugin="${entry%%:*}"
    repo="${entry##*:}"
    if [[ -z "$FILTER" || "$FILTER" == "$plugin" ]]; then
        publish_one "$plugin" "$repo"
    fi
done

echo ""
echo "Done."
