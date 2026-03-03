import abc
import os
from functools import cached_property

import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib.common import tools
from resources.lib.modules.globals import g


class Menus:
    def __init__(self):
        self.providers = {}
        if g.all_debrid_enabled():
            self.providers['all_debrid'] = ('All Debrid', AllDebridWalker)
        if g.premiumize_enabled():
            self.providers['premiumize'] = ('Premiumize', PremiumizeWalker)
        if g.real_debrid_enabled():
            self.providers['real_debrid'] = ('Real Debrid', RealDebridWalker)
        if g.torbox_enabled():
            self.providers['torbox'] = ('TorBox', TorBoxWalker)
        self.providers['local_downloads'] = ('Local Downloads', LocalFileWalker)

    def home(self):
        for key, value in sorted(self.providers.items()):
            args = {'debrid_provider': key, 'id': None}
            g.add_directory_item(
                value[0],
                action='myFilesFolder',
                action_args=args,
                menu_item=g.create_icon_dict(key, g.ICONS_PATH),
            )
        g.close_directory(g.CONTENT_MENU, sort='title')

    def my_files_folder(self, args):
        if args.get('id', args.get('path')) is None:
            self.providers[args['debrid_provider']][1]().get_init_list()
        else:
            self.providers[args['debrid_provider']][1]().get_folder(args)
        g.close_directory(g.CONTENT_MENU, sort='title')

    def my_files_play(self, args):
        self.providers[args['debrid_provider']][1]().play_item(args)


class BaseDebridWalker:
    provider = ''

    @abc.abstractmethod
    def get_init_list(self):
        """
        Return initial listing for menu
        :return:
        """
        pass

    @abc.abstractmethod
    def _is_folder(self, list_item):
        """
        Returns True if item is a folder
        Returns False if items is a playable file_path
        :param list_item:
        :return:
        """
        pass

    @abc.abstractmethod
    def get_folder(self, list_item):
        """
        Creates new Kodi menu list from list_item
        :param list_item:
        :return:
        """
        pass

    def play_item(self, args):
        resolved_link = self.resolve_link(args)
        item = xbmcgui.ListItem(path=resolved_link)
        xbmcplugin.setResolvedUrl(g.PLUGIN_HANDLE, True, item)

    def _format_items(self, items):
        for i in items:
            i.update({'debrid_provider': self.provider})
            if self._is_folder(i):
                name = i['name']
                is_playable = False
                is_folder = True
                action = 'myFilesFolder'
            else:
                name = f"{i['name']}  ({tools.bytes_size_display(i['size'])})" if i.get("size") else i['name']
                is_folder = False
                is_playable = True
                action = 'myFilesPlay'

            i.pop('links', None)  # De-clutter our action args a bit

            g.add_directory_item(
                name,
                action=action,
                is_playable=is_playable,
                is_folder=is_folder,
                action_args=tools.construct_action_args(i),
                menu_item=g.create_icon_dict(self.provider, g.ICONS_PATH),
            )

    @abc.abstractmethod
    def resolve_link(self, args):
        """
        Returns playable link from arguments
        :param args:
        :return:
        """


class PremiumizeWalker(BaseDebridWalker):
    provider = 'premiumize'

    @cached_property
    def premiumize(self):
        from resources.lib.debrid.premiumize import Premiumize

        return Premiumize()

    def get_init_list(self):
        items = self.premiumize.list_folder('')
        self._format_items(items)

    def _is_folder(self, list_item):
        return list_item['type'] == 'folder'

    def get_folder(self, list_item):
        items = self.premiumize.list_folder(list_item['id'])
        self._format_items(items)

    def resolve_link(self, list_item):
        return list_item['link']


class RealDebridWalker(BaseDebridWalker):
    provider = 'real_debrid'

    @cached_property
    def real_debrid(self):
        from resources.lib.debrid.real_debrid import RealDebrid

        return RealDebrid()

    def get_init_list(self):
        root = self.real_debrid.list_torrents()
        items = []

        for i in root:
            if i['status'] != 'downloaded':
                continue
            item = {
                "id": i['id'],
                "name": i['filename'],
            }
            if len(i['links']) > 1:
                item['links'] = i['links']
            else:
                item['link'] = i['links'][0]
                item['size'] = i['bytes']
            items.append(item)

        self._format_items(items)

    def _is_folder(self, list_item):
        return bool(list_item.get('links'))

    def get_folder(self, list_item):
        folder = self.real_debrid.torrent_info(list_item['id'])
        files = [file for file in folder.get("files", []) if file.get("selected") == 1]
        items = []

        for p, i in enumerate(files):
            if i['selected'] != 1:
                continue
            item = {
                "name": i['path'].split('/')[-1] if i['path'].startswith('/') else i['path'],
                "link": folder['links'][p],
                "size": i.get("bytes", 0),
            }
            items.append(item)

        self._format_items(items)

    def resolve_link(self, list_item):
        return self.real_debrid.resolve_hoster(list_item['link'])


class AllDebridWalker(BaseDebridWalker):
    provider = 'all_debrid'

    @cached_property
    def all_debrid(self):
        from resources.lib.debrid.all_debrid import AllDebrid

        return AllDebrid()

    def get_init_list(self):
        root = self.all_debrid.magnet_status(None).get("magnets", [])
        items = []

        for i in root:
            if not (isinstance(i, dict) and i.get('status') == "Ready"):
                continue
            item = {
                "id": i['id'],
                "name": i['filename'],
                "links": sorted(
                    [
                        link
                        for link in i['links']
                        if (
                            len(filenames := self._get_lowest_level_filename_for_link_files(link.get("files", []))) == 1
                            and filenames[0].endswith(g.common_video_extensions)
                        )
                    ],
                    key=lambda x: x['filename'],
                ),
            }
            if item.get("links"):
                items.append(item)

        self._format_items(items)

    def _is_folder(self, list_item):
        return bool(list_item.get("links"))

    def get_folder(self, list_item):
        links = self.all_debrid.magnet_status(list_item['id']).get("magnets", []).get("links", [])
        items = []

        for l in links:
            filenames = self._get_lowest_level_filename_for_link_files(l.get("files", []))
            if not (len(filenames) == 1 and filenames[0].endswith(tuple(g.common_video_extensions))):
                continue
            item = {"name": filenames[0], "link": l.get("link"), "size": l.get("size", 0)}
            items.append(item)

        self._format_items(sorted(items, key=lambda x: x['name']))

    def _get_lowest_level_filename_for_link_files(self, files_item):
        files = []
        for file in files_item if isinstance(files_item, list) else [files_item]:
            if entities := file.get("e"):
                files.extend(self._get_lowest_level_filename_for_link_files(entities))
            else:
                files.append(file.get("n"))
        return files

    def resolve_link(self, list_item):
        return self.all_debrid.resolve_hoster(list_item['link'])


class TorBoxWalker(BaseDebridWalker):
    provider = 'torbox'

    @cached_property
    def torbox(self):
        from resources.lib.debrid.torbox import TorBox

        return TorBox()

    def get_init_list(self):
        """List all TorBox torrents, usenet, and web downloads."""
        items = []

        # Get torrent items
        torrents = self.torbox.list_torrents()
        for torrent in torrents or []:
            files = torrent.get('files', [])
            if files:
                item = {
                    "id": torrent['id'],
                    "name": torrent['name'],
                    "type": "torrent",
                    "links": files,
                }
                items.append(item)

        # Get usenet items
        usenet = self.torbox.list_usenet()
        for download in usenet or []:
            files = download.get('files', [])
            if files:
                item = {
                    "id": download['id'],
                    "name": download['name'],
                    "type": "usenet",
                    "links": files,
                }
                items.append(item)

        # Get web download items
        webdl = self.torbox.list_webdl()
        for download in webdl or []:
            files = download.get('files', [])
            if files:
                item = {
                    "id": download['id'],
                    "name": download['name'],
                    "type": "webdl",
                    "links": files,
                }
                items.append(item)

        self._format_items(items)

    def _is_folder(self, list_item):
        return bool(list_item.get("links"))

    def get_folder(self, list_item):
        """List files within a torrent/usenet/webdl item."""
        items = []
        item_type = list_item.get('type', 'torrent')
        parent_id = list_item['id']

        # Fetch fresh data from API since links aren't passed through URL args
        # Note: _get() extracts 'data' from response, so result is already the data
        if item_type == 'torrent':
            torrent_info = self.torbox.torrent_info(parent_id)
            files = torrent_info.get('files', []) if torrent_info else []
        elif item_type == 'usenet':
            usenet_info = self.torbox.usenet_info(parent_id)
            files = usenet_info.get('files', []) if usenet_info else []
        else:  # webdl
            webdl_info = self.torbox.webdl_info(parent_id)
            files = webdl_info.get('files', []) if webdl_info else []

        for file_item in files:
            filename = file_item.get('short_name', file_item.get('name', ''))
            # Only show video files
            if not filename.lower().endswith(g.common_video_extensions):
                continue
            item = {
                "name": filename,
                "link": f"{parent_id},{file_item.get('id', '')}",
                "size": file_item.get('size', 0),
                "type": item_type,
            }
            items.append(item)

        self._format_items(sorted(items, key=lambda x: x['name']))

    def resolve_link(self, list_item):
        """Resolve TorBox file to direct download link."""
        item_type = list_item.get('type', 'torrent')
        link = list_item['link']

        # All link formats are "id,file_id"
        parts = link.split(',')
        if len(parts) != 2:
            g.log(f"TorBox invalid link format: {link}", "error")
            return None

        parent_id, file_id = parts

        if item_type == 'usenet':
            return self.torbox.resolve_usenet(link)
        elif item_type == 'webdl':
            return self.torbox.resolve_webdl(parent_id, file_id)
        else:
            # Torrent files
            return self.torbox.resolve_torrent_file(parent_id, file_id)


class LocalFileWalker(BaseDebridWalker):
    provider = "local_downloads"
    downloads_folder = g.get_setting("download.location")

    def _get_folder_list(self, path):
        directory_listing = xbmcvfs.listdir(path)
        contents = [tools.ensure_path_is_dir(i) for i in directory_listing[0]] + list(directory_listing[1])

        return [
            {
                "name": i[:-1] if i.endswith(("\\", "/")) else i,
                "path": os.path.join(path, i),
                "size": xbmcvfs.Stat(os.path.join(path, i)).st_size(),
            }
            for i in contents
        ]

    def get_init_list(self):
        self._format_items(self._get_folder_list(self.downloads_folder))

    def _is_folder(self, list_item):
        return list_item['path'].endswith(('\\', '/'))

    def get_folder(self, list_item):
        self._format_items(self._get_folder_list(list_item['path']))

    def resolve_link(self, list_item):
        return list_item['path']
