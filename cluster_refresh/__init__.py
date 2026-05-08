# -*- coding: utf-8 -*-
PLUGIN_NAME = "Cluster Refresh"
PLUGIN_AUTHOR = "rpmzine"
PLUGIN_DESCRIPTION = "Refreshes cluster files from disk without re-dragging. Right-click a cluster or file and choose 'Refresh from Disk' to re-read updated metadata."
PLUGIN_VERSION = "1.0.0"
PLUGIN_API_VERSIONS = ["2.10", "2.11", "2.12", "2.13"]
PLUGIN_LICENSE = "MIT"
PLUGIN_LICENSE_URL = "https://opensource.org/licenses/MIT"

from picard import log
from picard.ui.itemviews import BaseAction
from .._compat import register_cluster_action, register_file_action


class RefreshFromDiskAction(BaseAction):
    NAME = "Refresh from Disk"

    def callback(self, objs):
        try:
            files = list(self.tagger.get_files_from_objects(objs))
            if not files:
                log.debug("Cluster Refresh: No files found in selection")
                return

            filenames = [f.filename for f in files]
            self.tagger.remove_files(files, from_parent=True)
            self.tagger.add_files(filenames)
            log.info(
                f"Cluster Refresh: Refreshed {len(filenames)} file(s) from disk"
            )
        except Exception as e:
            log.error(f"Cluster Refresh: Error refreshing files: {e}")


try:
    _refresh_action = RefreshFromDiskAction()
    register_cluster_action(_refresh_action)
    register_file_action(_refresh_action)
    log.info("Cluster Refresh: Plugin loaded, actions registered")
except Exception as e:
    log.error(f"Cluster Refresh: Failed to register actions: {e}")
