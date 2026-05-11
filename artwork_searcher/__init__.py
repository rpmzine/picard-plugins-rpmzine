# -*- coding: utf-8 -*-
PLUGIN_NAME = "Artwork Searcher"
PLUGIN_AUTHOR = "rpmzine"
PLUGIN_DESCRIPTION = "Opens a browser image search for album artwork using artist and album title (or folder name)."
PLUGIN_VERSION = "1.0.0"
PLUGIN_API_VERSIONS = ["2.10", "2.11", "2.12", "2.13", "3.0"]
PLUGIN_LICENSE = "GPL-2.0"
PLUGIN_LICENSE_URL = "https://www.gnu.org/licenses/gpl-2.0.html"

import os
import webbrowser
from urllib.parse import quote_plus
from picard import log
from ._compat import (
    BaseAction,
    register_album_action,
    register_cluster_action,
    register_file_action,
    register_track_action,
)


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def _get_query(obj):
    """
    Build a search query string from an object's metadata.

    Priority:
      1. albumartist (or artist) + album tag
      2. albumartist (or artist) + folder name (fallback when no album tag)

    Returns None if neither artist nor album/folder can be determined.
    """
    meta = obj.metadata
    artist = meta.get("albumartist") or meta.get("artist", "")
    album = meta.get("album", "")

    if not album:
        # Try to resolve a filename — directly on the object or via its files
        filename = getattr(obj, "filename", None)
        if not filename:
            files = getattr(obj, "files", [])
            if files:
                filename = getattr(files[0], "filename", None)
        if filename:
            album = os.path.basename(os.path.dirname(filename))

    parts = [p.strip() for p in [artist, album] if p and p.strip()]
    if not parts:
        return None
    return " ".join(parts) + " album cover"


def _collect_queries(objs):
    """Return a deduplicated list of search queries from the selected objects."""
    seen = set()
    queries = []
    for obj in objs:
        q = _get_query(obj)
        if q and q not in seen:
            seen.add(q)
            queries.append(q)
    return queries


# ---------------------------------------------------------------------------
# Context menu actions
# ---------------------------------------------------------------------------

class SearchArtworkGoogle(BaseAction):
    NAME = "Search Artwork → Google Images"
    TITLE = "Search Artwork → Google Images"

    def callback(self, objs):
        for q in _collect_queries(objs):
            # tbm=isch  : image search
            # tbs=isz:l : filter to large images
            url = (
                "https://www.google.com/search"
                f"?q={quote_plus(q)}&tbm=isch&tbs=isz:l"
            )
            log.debug("Artwork Searcher: opening Google search for %r", q)
            webbrowser.open(url)


class SearchArtworkBing(BaseAction):
    NAME = "Search Artwork → Bing Images"
    TITLE = "Search Artwork → Bing Images"

    def callback(self, objs):
        for q in _collect_queries(objs):
            # qft=+filterui:imagesize-large : filter to large images
            url = (
                "https://www.bing.com/images/search"
                f"?q={quote_plus(q)}&qft=+filterui:imagesize-large"
            )
            log.debug("Artwork Searcher: opening Bing search for %r", q)
            webbrowser.open(url)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def enable(api):
    if hasattr(api, 'register_cluster_action'):
        for cls in (SearchArtworkGoogle, SearchArtworkBing):
            for fn_name in ('register_file_action', 'register_track_action',
                            'register_cluster_action', 'register_album_action'):
                fn = getattr(api, fn_name, None)
                if fn:
                    fn(cls)
    else:
        for _action in (SearchArtworkGoogle(), SearchArtworkBing()):
            register_file_action(_action)
            register_track_action(_action)
            register_cluster_action(_action)
            register_album_action(_action)
    log.debug("Artwork Searcher: actions registered")
