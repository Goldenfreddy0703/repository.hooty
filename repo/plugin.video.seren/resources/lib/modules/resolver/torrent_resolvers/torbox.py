"""
TorBox torrent resolver for Seren.
"""

from resources.lib.common import source_utils
from resources.lib.debrid.torbox import TorBox
from resources.lib.modules.globals import g
from resources.lib.modules.resolver.torrent_resolvers.base_resolver import (
    TorrentResolverBase,
)


class TorBoxResolver(TorrentResolverBase):
    """
    Resolver for TorBox
    """

    def __init__(self):
        super().__init__()
        self.debrid_module = TorBox()
        self.torrent_id = None
        self._source_normalization = (
            ("name", "path", None),
            ("short_name", "release_title", None),
            ("size", "size", lambda k: k / 1024 / 1024 if k > 1024 * 1024 else k),
            ("id", "id", None),
        )

    def _fetch_source_files(self, torrent, item_information):
        """
        Fetch source files from TorBox for the given torrent.
        """
        try:
            # Use the original magnet if available, otherwise construct from hash
            magnet = torrent.get("magnet")
            if not magnet:
                magnet = f"magnet:?xt=urn:btih:{torrent['hash']}"
            
            torrent_data = self.debrid_module.get_torrent_files(magnet=magnet)

            if not torrent_data:
                g.log("TorBox: get_torrent_files returned empty", "warning")
                return []

            self.torrent_id = torrent_data.get("torrent_id")
            files = torrent_data.get("files", [])
            
            g.log(f"TorBox: Got {len(files)} files for torrent_id {self.torrent_id}", "debug")
            
            if not files:
                g.log("TorBox: No files found in torrent", "warning")
                return []
            
            return files
        except Exception as e:
            g.log(f"TorBox _fetch_source_files error: {e}", "error")
            return []

    def resolve_stream_url(self, file_info):
        """
        Convert provided source file into a link playable through TorBox.
        :param file_info: Normalised information on source file
        :return: streamable link
        """
        if file_info is None:
            g.log("TorBox resolve_stream_url: file_info is None", "error")
            return None

        if not self.torrent_id:
            g.log("TorBox resolve_stream_url: torrent_id is None", "error")
            return None

        file_id = file_info.get("id")
        if file_id is None:
            g.log(f"TorBox: No file_id in file_info: {file_info}", "error")
            return None

        g.log(f"TorBox: Resolving torrent_id={self.torrent_id}, file_id={file_id}", "debug")
        
        stream_url = self.debrid_module.resolve_torrent_file(self.torrent_id, file_id)
        
        if stream_url:
            g.log(f"TorBox: Got stream URL", "debug")
        else:
            g.log("TorBox: resolve_torrent_file returned None", "error")
            
        return stream_url

    def _do_post_processing(self, item_information, torrent, identified_file):
        """
        Perform post-processing after resolving.
        """
        if g.get_bool_setting("tb.autodelete") and self.torrent_id:
            self.debrid_module.delete_torrent(self.torrent_id)
