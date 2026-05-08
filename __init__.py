from . import album_subfolder
from . import artwork_searcher
from . import audio_file_info
from . import cluster_refresh
from . import grouping_tagger
from . import multidisc_tagger
from . import suffix_appender
from . import tag_filter_joiner


def enable(api):
    # Sub-packages register themselves at import time via _compat.py helpers.
    # This function satisfies the Picard 3.0 plugin V3 entry-point requirement.
    pass
