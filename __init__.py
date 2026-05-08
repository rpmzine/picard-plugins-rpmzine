from . import album_subfolder
from . import artwork_searcher
from . import audio_file_info
from . import cluster_refresh
from . import grouping_tagger
from . import multidisc_tagger
from . import suffix_appender
from . import tag_filter_joiner


def enable(api):
    for _plugin in (album_subfolder, artwork_searcher, audio_file_info,
                    cluster_refresh, grouping_tagger, multidisc_tagger,
                    suffix_appender, tag_filter_joiner):
        _plugin.enable(api)
