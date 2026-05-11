# -*- coding: utf-8 -*-
PLUGIN_NAME = "Cluster Refresh"
PLUGIN_AUTHOR = "rpmzine"
PLUGIN_DESCRIPTION = "Refreshes cluster files from disk without re-dragging. Right-click a cluster or file and choose 'Refresh from Disk' to re-read updated metadata."
PLUGIN_VERSION = "1.0.0"
PLUGIN_API_VERSIONS = ["2.10", "2.11", "2.12", "2.13", "3.0"]
PLUGIN_LICENSE = "MIT"
PLUGIN_LICENSE_URL = "https://opensource.org/licenses/MIT"

from picard import log
from ._compat import BaseAction, register_cluster_action, register_file_action


class RefreshFromDiskAction(BaseAction):
    NAME = "Refresh from Disk"
    TITLE = "Refresh from Disk"

    def callback(self, objs):
        try:
            tagger = getattr(getattr(self, 'api', None), 'tagger', None) or getattr(self, 'tagger', None)

            # Picard 3.0 V3: objects expose .files directly (Cluster/Album)
            # Picard 2.x V2: use tagger.get_files_from_objects
            files = []
            for obj in objs:
                if hasattr(obj, 'files'):
                    files.extend(obj.files)
                elif hasattr(obj, 'filename'):
                    files.append(obj)
            if not files and tagger and hasattr(tagger, 'get_files_from_objects'):
                files = list(tagger.get_files_from_objects(objs))

            if not files:
                log.debug("Cluster Refresh: No files found in selection")
                return

            filenames = [f.filename for f in files]
            tagger.remove_files(files, from_parent=True)
            tagger.add_files(filenames)
            log.info(
                f"Cluster Refresh: Refreshed {len(filenames)} file(s) from disk"
            )
        except Exception as e:
            log.error(f"Cluster Refresh: Error refreshing files: {e}")


def enable(api):
    if hasattr(api, 'register_cluster_action'):
        api.register_cluster_action(RefreshFromDiskAction)
        api.register_file_action(RefreshFromDiskAction)
    else:
        _action = RefreshFromDiskAction()
        register_cluster_action(_action)
        register_file_action(_action)
    log.info("Cluster Refresh: Plugin loaded, actions registered")
