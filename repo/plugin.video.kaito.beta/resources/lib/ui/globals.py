# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import re
import os
import threading
import sys
import json
import traceback
import xbmc
import xbmcaddon
import xbmcplugin
import xbmcvfs
import xbmcgui

from resources.lib.ui import control
from resources.lib.modules.settings_cache import PersistedSettingsCache, RuntimeSettingsCache

viewTypes = [
    ("Default", 50),
    ("Poster", 51),
    ("Icon Wall", 52),
    ("Shift", 53),
    ("Info Wall", 54),
    ("Wide List", 55),
    ("Wall", 500),
    ("Banner", 501),
    ("Fanart", 502),
]

info_labels = [
    "genre",
    "country",
    "year",
    "episode",
    "season",
    "sortepisode",
    "sortseason",
    "episodeguide",
    "showlink",
    "top250",
    "setid",
    "tracknumber",
    "rating",
    "userrating",
    "watched",
    "playcount",
    "overlay",
    "castandrole",
    "director",
    "mpaa",
    "plot",
    "plotoutline",
    "title",
    "originaltitle",
    "sorttitle",
    "duration",
    "studio",
    "tagline",
    "writer",
    "tvshowtitle",
    "premiered",
    "status",
    "set",
    "setoverview",
    "tag",
    "imdbnumber",
    "code",
    "aired",
    "credits",
    "lastplayed",
    "album",
    "artist",
    "votes",
    "path",
    "trailer",
    "dateadded",
    "mediatype",
    "dbid",
]

info_dates = [
    "premiered",
    "aired",
    "lastplayed",
    "dateadded",
]


class GlobalVariables(object):
    CONTENT_MENU = "addons"
    CONTENT_FOLDER = "files"
    CONTENT_MOVIE = "movies"
    CONTENT_SHOW = "tvshows"
    CONTENT_SEASON = "seasons"
    CONTENT_EPISODE = "episodes"
    CONTENT_GENRES = "genres"
    CONTENT_YEARS = "years"
    MEDIA_FOLDER = "file"
    MEDIA_MOVIE = "movie"
    MEDIA_SHOW = "tvshow"
    MEDIA_SEASON = "season"
    MEDIA_EPISODE = "episode"

    DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
    DATE_TIME_FORMAT_ZULU = DATE_TIME_FORMAT + ".000Z"
    DATE_FORMAT = "%Y-%m-%d"

    PYTHON3 = control.PYTHON3
    UNICODE = control.unicode
    SEMVER_REGEX = re.compile(r"^((?:\d+\.){2}\d+)")

    def __init__(self):
        self.IS_ADDON_FIRSTRUN = None
        self.ADDON = None
        self.ADDON_DATA_PATH = None
        self.ADDON_ID = None
        self.ADDON_NAME = None
        self.VERSION = None
        self.CLEAN_VERSION = None
        self.USER_AGENT = None
        self.DEFAULT_FANART = None
        self.DEFAULT_ICON = None
        self.ADDON_USERDATA_PATH = None
        self.SETTINGS_CACHE = {}
        self.RUNTIME_SETTINGS_CACHE = None
        self.LANGUAGE_CACHE = {}
        self.PLAYLIST = None
        self.HOME_WINDOW = None
        self.KODI_FULL_VERSION = None
        self.KODI_VERSION = None
        self.PLATFORM = self._get_system_platform()
        self.URL = None
        self.PLUGIN_HANDLE = 0
        self.IS_SERVICE = True
        self.BASE_URL = None
        self.PATH = None
        self.PARAM_STRING = None
        self.REQUEST_PARAMS = None
        self.FROM_WIDGET = False
        self.PAGE = 1
        self.THEME = control.getSetting('general.icons').lower()

    def __del__(self):
        self.deinit()

    def deinit(self):
        self.ADDON = None
        del self.ADDON
        self.PLAYLIST = None
        del self.PLAYLIST
        self.HOME_WINDOW = None
        del self.HOME_WINDOW

    def init_globals(self, argv=None, addon_id=None):
        self.IS_ADDON_FIRSTRUN = self.IS_ADDON_FIRSTRUN is None
        self.SETTINGS_CACHE = {}
        self.LANGUAGE_CACHE = {}
        self.ADDON = xbmcaddon.Addon()
        self.ADDON_ID = addon_id if addon_id else self.ADDON.getAddonInfo("id")
        self.ADDON_NAME = self.ADDON.getAddonInfo("name")
        self.VERSION = self.ADDON.getAddonInfo("version")
        self.CLEAN_VERSION = self.SEMVER_REGEX.findall(self.VERSION)[0]
        self.USER_AGENT = "{} - {}".format(self.ADDON_NAME, self.CLEAN_VERSION)
        self.DEFAULT_FANART = self.ADDON.getAddonInfo("fanart")
        self.DEFAULT_ICON = self.ADDON.getAddonInfo("icon")
        self._init_kodi()
        self._init_settings_cache()
        self._init_paths()
        self.init_request(argv)
        self._init_cache()

    def _init_kodi(self):
        self.PLAYLIST = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        self.HOME_WINDOW = xbmcgui.Window(10000)
        self.KODI_FULL_VERSION = xbmc.getInfoLabel("System.BuildVersion")
        version = re.findall(r'(?:(?:((?:\d+\.?){1,3}\S+))?\s+\(((?:\d+\.?){2,3})\))', self.KODI_FULL_VERSION)
        if version:
            self.KODI_FULL_VERSION = version[0][1]
            if len(version[0][0]) > 1:
                pre_ver = version[0][0][:2]
                full_ver = version[0][1][:2]
                if pre_ver > full_ver:
                    self.KODI_VERSION = int(pre_ver[:2])
                else:
                    self.KODI_VERSION = int(full_ver[:2])
            else:
                self.KODI_VERSION = int(version[0][1][:2])
        else:
            self.KODI_FULL_VERSION = self.KODI_FULL_VERSION.split(' ')[0]
            self.KODI_VERSION = int(self.KODI_FULL_VERSION[:2])

    def _init_settings_cache(self):
        self.RUNTIME_SETTINGS_CACHE = RuntimeSettingsCache()
        self.SETTINGS_CACHE = PersistedSettingsCache()

    @staticmethod
    def _get_system_platform():
        """
        get platform on which xbmc run
        """
        platform = "unknown"
        if xbmc.getCondVisibility("system.platform.linux"):
            platform = "linux"
        elif xbmc.getCondVisibility("system.platform.xbox"):
            platform = "xbox"
        elif xbmc.getCondVisibility("system.platform.windows"):
            if "Users\\UserMgr" in os.environ.get("TMP"):
                platform = "xbox"
            else:
                platform = "windows"
        elif xbmc.getCondVisibility("system.platform.osx"):
            platform = "osx"

        return platform

    def _init_cache(self):
        from resources.lib.database.cache import Cache

        self.CACHE = Cache()

    # region global settings
    @staticmethod
    def _global_setting_key(setting_id):
        return "kaito.setting.{}".format(setting_id)

    def get_global_setting(self, setting_id):
        try:
            return eval(
                self.HOME_WINDOW.getProperty(self._global_setting_key(setting_id))
            )
        except:
            return None

    def set_global_setting(self, setting_id, value):
        return self.HOME_WINDOW.setProperty(
            self._global_setting_key(setting_id), repr(value)
        )

    def init_request(self, argv):
        if argv is None:
            return

        self.URL = control.urlparse(argv[0])
        try:
            self.PLUGIN_HANDLE = int(argv[1])
            self.IS_SERVICE = False
        except IndexError:
            self.PLUGIN_HANDLE = 0
            self.IS_SERVICE = True

        if self.URL[1] != "":
            self.BASE_URL = "{scheme}://{netloc}".format(
                scheme=self.URL[0], netloc=self.URL[1]
            )
        else:
            self.BASE_URL = ""
        self.PATH = control.unquote(self.URL[2])
        try:
            self.PARAM_STRING = argv[2].lstrip('?/')
        except IndexError:
            self.PARAM_STRING = ""
        self.REQUEST_PARAMS = dict(control.parse_qsl(self.PARAM_STRING))
        if "action_args" in self.REQUEST_PARAMS:
            self.REQUEST_PARAMS["action_args"] = control.deconstruct_action_args(
                self.REQUEST_PARAMS["action_args"]
            )
        self.PAGE = int(g.REQUEST_PARAMS.get("page", 1))

    def _init_paths(self):
        self.ADDONS_PATH = control.translate_path(
            os.path.join("special://home/", "addons/")
        )
        self.ADDON_PATH = control.translate_path(
            os.path.join(
                "special://home/", "addons/{}".format(self.ADDON_ID.lower())
            )
        )
        self.ADDON_DATA_PATH = control.translate_path(
            self.ADDON.getAddonInfo("path")
        )  # Addon folder
        self.ADDON_USERDATA_PATH = control.translate_path(
            "special://profile/addon_data/{}/".format(self.ADDON_ID)
        )  # Addon user data folder
        self.SETTINGS_PATH = control.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "settings.xml")
        )
        self.ADVANCED_SETTINGS_PATH = control.translate_path(
            "special://profile/advancedsettings.xml"
        )
        self.KODI_DATABASE_PATH = control.translate_path(
            "special://database/"
        )
        self.IMAGES_PATH = control.translate_path(
            os.path.join(self.ADDON_DATA_PATH, "resources", "images", self.THEME)
        )
        self.CACHE_DB_PATH = control.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "cache.db")
        )
        self.TORRENT_SCRAPE_CACHE = control.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "torrentScrape.db")
        )
        self.ANILIST_SYNC_DB_PATH = control.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "anilistSync.db")
        )
        self.SEARCH_HISTORY_DB_PATH = control.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "search.db")
        )
        self.MAL_DUB_FILE_PATH = control.translate_path(
            os.path.join(self.ADDON_USERDATA_PATH, "mal_dub.json")
        )
        # This will change sometimes with kodi versions
        self.KODI_VIDEO_DB_PATH = control.translate_path(
            os.path.join(self.KODI_DATABASE_PATH, "MyVideos119.db")
        )

    # region runtime settings
    def set_runtime_setting(self, setting_id, value):
        self.RUNTIME_SETTINGS_CACHE.set_setting(setting_id, value)

    def clear_runtime_setting(self, setting_id):
        self.RUNTIME_SETTINGS_CACHE.clear_setting(setting_id)

    def get_runtime_setting(self, setting_id, default_value=None):
        return self.RUNTIME_SETTINGS_CACHE.get_setting(setting_id, default_value)

    def get_float_runtime_setting(self, setting_id, default_value=None):
        return self.RUNTIME_SETTINGS_CACHE.get_float_setting(setting_id, default_value)

    def get_int_runtime_setting(self, setting_id, default_value=None):
        return self.RUNTIME_SETTINGS_CACHE.get_int_setting(setting_id, default_value)

    def get_bool_runtime_setting(self, setting_id, default_value=None):
        return self.RUNTIME_SETTINGS_CACHE.get_bool_setting(setting_id, default_value)
    # endregion

    # region KODI setting
    def set_setting(self, setting_id, value):
        self.SETTINGS_CACHE.set_setting(setting_id, value)

    def clear_setting(self, setting_id):
        self.SETTINGS_CACHE.clear_setting(setting_id)

    def get_setting(self, setting_id, default_value=None):
        return self.SETTINGS_CACHE.get_setting(setting_id, default_value)

    def get_float_setting(self, setting_id, default_value=None):
        return self.SETTINGS_CACHE.get_float_setting(setting_id, default_value)

    def get_int_setting(self, setting_id, default_value=None):
        return self.SETTINGS_CACHE.get_int_setting(setting_id, default_value)

    def get_bool_setting(self, setting_id, default_value=None):
        return self.SETTINGS_CACHE.get_bool_setting(setting_id, default_value)
    # endregion

    def get_language_string(self, language_id):
        text = self.LANGUAGE_CACHE.get(
            language_id, self.ADDON.getLocalizedString(language_id)
        )
        self.LANGUAGE_CACHE.update({language_id: text})
        return text

    def lang(self, language_id):
        text = self.ADDON.getLocalizedString(language_id)
        return control.decode_py2(text)

    def color_string(self, text, color=None):
        """Method that wraps the the text with the supplied color, or takes the user default.
        :param text:Text that needs to be wrapped
        :type text:str|int|float
        :param color:Color name used in the Kodi color tag
        :type color:str
        :return:Text wrapped in a Kodi color tag.
        :rtype:str
        """
        if color == 'default' or color == '' or color is None:
            color = 'deepskyblue'

        return "[COLOR {}]{}[/COLOR]".format(color, text)

    def clear_cache(self, silent=False):
        if not silent:
            confirm = xbmcgui.Dialog().yesno(
                self.ADDON_NAME, "Are you sure you wish to clear the cache?"
            )
            if confirm != 1:
                return
        g.CACHE.clear_all()
        g._init_cache()
        self.log(self.ADDON_NAME + ": Cache Cleared", "debug")
        if not silent:
            xbmcgui.Dialog().notification(self.ADDON_NAME, "All Cache Successfully Cleared")

    def get_view_type(self, content_type):
        no_view_type = 0
        view_type = None

        if not self.get_bool_setting("general.viewidswitch"):
            if content_type == self.CONTENT_FOLDER:
                view_type = self.get_setting("addon.view")
            if content_type == self.CONTENT_SHOW:
                view_type = self.get_setting("show.view")
            if content_type == self.CONTENT_MOVIE:
                view_type = self.get_setting("movie.view")
            if content_type == self.CONTENT_EPISODE:
                view_type = self.get_setting("episode.view")
            if content_type == self.CONTENT_SEASON:
                view_type = self.get_setting("season.view")
            if view_type is not None and view_type.isdigit() and int(view_type) > 0:
                view_name, view_type = viewTypes[int(view_type)]
                return view_type
        else:
            if content_type == self.CONTENT_FOLDER:
                view_type = self.get_setting("addon.view.id")
            if content_type == self.CONTENT_SHOW:
                view_type = self.get_setting("show.view.id")
            if content_type == self.CONTENT_MOVIE:
                view_type = self.get_setting("movie.view.id")
            if content_type == self.CONTENT_EPISODE:
                view_type = self.get_setting("episode.view.id")
            if content_type == self.CONTENT_SEASON:
                view_type = self.get_setting("season.view.id")
            if view_type is not None and view_type.isdigit() and int(view_type) > 0:
                return int(view_type)

        return no_view_type

    def log(self, msg, level="info"):
        msg = msg
        msg = "{} ({}): {}".format(self.ADDON_NAME.upper(), self.PLUGIN_HANDLE, msg)
        if level == "error":
            xbmc.log(msg, level=xbmc.LOGERROR)
        elif level == "info":
            xbmc.log(msg, level=xbmc.LOGINFO)
        elif level == "notice":
            if self.KODI_VERSION >= 19:
                xbmc.log(msg, level=xbmc.LOGINFO)
            else:
                xbmc.log(msg, level=xbmc.LOGNOTICE)  # pylint: disable=no-member
        elif level == "warning":
            xbmc.log(msg, level=xbmc.LOGWARNING)
        else:
            xbmc.log(msg)

    def log_stacktrace(self):
        """Gets the latest traceback stacktrace and logs it."""
        self.log(traceback.format_exc(), "error")

    def close_all_dialogs(self):
        xbmc.executebuiltin("Dialog.Close(all,true)")

    def close_ok_dialog(self):
        xbmc.executebuiltin("Dialog.Close(okdialog, true)")

    def close_busy_dialog(self):
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        xbmc.executebuiltin("Dialog.Close(busydialognocancel)")

    def real_debrid_enabled(self):
        if self.get_setting('rd.auth') != '' and self.get_setting('realdebrid.enabled') == 'true':
            return True
        else:
            return False

    def all_debrid_enabled(self):
        if self.get_setting('alldebrid.apikey') != '' and self.get_setting('alldebrid.enabled') == 'true':
            return True
        else:
            return False

    def premiumize_enabled(self):
        if self.get_setting('premiumize.token') != '' and self.get_setting('premiumize.enabled') == 'true':
            return True
        else:
            return False

    def myanimelist_enabled(self):
        if self.get_setting('mal.token') != '' and self.get_setting('mal.enabled') == 'true':
            return True
        else:
            return False

    def kitsu_enabled(self):
        if self.get_setting('kitsu.token') != '' and self.get_setting('kitsu.enabled') == 'true':
            return True
        else:
            return False

    def anilist_enabled(self):
        if self.get_setting('anilist.token') != '' and self.get_setting('anilist.enabled') == 'true':
            return True
        else:
            return False

    def watchlist_to_update(self):
        if self.get_setting('watchlist.update.enabled') == 'true':
            flavor = self.get_setting('watchlist.update.flavor').lower()
            if self.get_setting('%s.enabled' % flavor) == 'true':
                return flavor
        else:
            return

    def container_refresh(self):
        return xbmc.executebuiltin("Container.Refresh")

    def get_language_code(self, region=None):
        if region:
            lang = xbmc.getLanguage(xbmc.ISO_639_1, True)
            if lang.lower() == "en-de":
                lang = "en-gb"
            lang = lang.split("-")
            if len(lang) > 1:
                lang = "{}-{}".format(lang[0].lower(), lang[1].upper())
                return lang
        return xbmc.getLanguage(xbmc.ISO_639_1, False)

    def allocate_item(self, name, url, is_dir=False, image='', info='', fanart=None, poster=None, is_playable=False):
        new_res = {}
        new_res['is_dir'] = is_dir
        new_res['is_playable'] = is_playable
        new_res['image'] = {
            'poster': poster,
            'thumb': image,
            'fanart': fanart
            }
        new_res['name'] = name
        urlsplit = url.split('/')
        params = {'action': urlsplit[0]}
        params['action_args'] = {}
        if 'next page' not in name.lower():
            if info['mediatype'] == 'tvshow':
                params['action_args']['anilist_id'] = urlsplit[1]
                if urlsplit[2]:
                    params['action_args']['mal_id'] = urlsplit[2]
            elif info['mediatype'] == 'episode':
                params['action_args']['anilist_id'] = urlsplit[1]
                params['action_args']['episode'] = urlsplit[2]
            elif info['mediatype'] == 'movie':
                params['action_args']['anilist_id'] = urlsplit[1]
            params['action_args']['mediatype'] = info['mediatype']
            url_route = self.create_url(self.BASE_URL, params)
            if url_route:
                new_res['url'] = url_route
            else:
                new_res['url'] = url
        else:
            if urlsplit[0] == 'search':
                params['action_args']['query'] = urlsplit[1]
                params['action_args']['page'] = urlsplit[2]
            else:
                params['action_args']['page'] = urlsplit[1]
            url_route = self.create_url(self.BASE_URL, params)
            if url_route:
                new_res['url'] = url_route
            else:
                new_res['url'] = url
        new_res['info'] = info
        return new_res

    def _get_view_type(self, viewType):
        viewTypes = {
            'Default': 50,
            'Poster': 51,
            'Icon Wall': 52,
            'Shift': 53,
            'Info Wall': 54,
            'Wide List': 55,
            'Wall': 500,
            'Banner': 501,
            'Fanart': 502,
        }
        return viewTypes[viewType]

    def xbmc_add_player_item(self, name, url, art='', info='', draw_cm=None, bulk_add=False):
        ok=True
        u=self.addon_url(url)
        cm = draw_cm if draw_cm is not None else []

        liz=xbmcgui.ListItem(name)
        liz.setInfo('video', info)

        if art is None or type(art) is not dict:
            art = {}

        if art.get('fanart') is None:
            art['fanart'] = self.DEFAULT_FANART
        
        liz.setArt(art)

        liz.setProperty("Video", "true")
        liz.setProperty("IsPlayable", "true")
        liz.addContextMenuItems(cm)
        if bulk_add:
            return (u, liz, False)
        else:
            ok=xbmcplugin.addDirectoryItem(handle=self.PLUGIN_HANDLE,url=u,listitem=liz, isFolder=False)
            return ok

    def xbmc_add_dir(self, name, **params):
        [params.update({key: value}) for key, value in params.items()]
        menu_item = params.pop("menu_item", {})

        liz=xbmcgui.ListItem(name)
        liz.setInfo('video', menu_item['info'])

        if menu_item.pop("is_playable", False):
            liz.setProperty("IsPlayable", "true")
            is_folder = menu_item.pop("is_dir", False)
        else:
            liz.setProperty("IsPlayable", "false")
            is_folder = menu_item.pop("is_dir", True)

        cm = params.pop("draw_cm", [])
        if cm is None or not isinstance(cm, (set, list)):
            cm = []
        liz.addContextMenuItems(cm)

        art = menu_item.pop("image", {})
        if art is None or type(art) is not dict:
            art = {}

        if art.get('fanart') is None:
            art['fanart'] = self.DEFAULT_FANART
        
        liz.setArt(art)

        bulk_add = params.pop("bulk_add", False)
        url = self.addon_url(menu_item['url'])
        if bulk_add:
            return url, liz, False
        else:
            xbmcplugin.addDirectoryItem(handle=self.PLUGIN_HANDLE,url=url,listitem=liz, isFolder=is_folder)

    def draw_items(self, video_data, contentType="tvshows", viewType=None, draw_cm=None, bulk_add=False):
        for vid in video_data:
            self.xbmc_add_dir(vid['name'], menu_item=vid, draw_cm=draw_cm, bulk_add=bulk_add)

        xbmcplugin.setContent(self.PLUGIN_HANDLE, contentType)
        if contentType == 'episodes': 
            xbmcplugin.addSortMethod(self.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_EPISODE)
        xbmcplugin.endOfDirectory(self.PLUGIN_HANDLE, succeeded=True, updateListing=False, cacheToDisc=True)

        if viewType:
            xbmc.executebuiltin('Container.SetViewMode(%d)' % self._get_view_type(viewType))

        return True

    def bulk_draw_items(self, video_data, draw_cm=None, bulk_add=True):
        item_list = []
        for vid in video_data:
            item = self.xbmc_add_dir(vid['name'], menu_item=vid, draw_cm=draw_cm, bulk_add=bulk_add)
            item_list.append(item)

        return item_list

    def addon_url(self, url=''):
        return "{}/{}".format(self.BASE_URL, url)

    def add_directory_item(self, name, **params):
        [params.update({key: value}) for key, value in params.items()]
        menu_item = params.pop("menu_item", {})
        if not isinstance(menu_item, dict):
            menu_item = {}

        item = xbmcgui.ListItem(label=name, offscreen=True)
        item.setContentLookup(False)

        info = menu_item.pop("info", {})
        item.addStreamInfo("video", {})

        if info is None or not isinstance(info, dict):
            info = {}

        # self._apply_listitem_properties(item, info)

        if "unwatched_episodes" in menu_item:
            item.setProperty("UnWatchedEpisodes", g.UNICODE(menu_item["unwatched_episodes"]))
        if "watched_episodes" in menu_item:
            item.setProperty("WatchedEpisodes", g.UNICODE(menu_item["watched_episodes"]))
        if menu_item.get("episode_count", 0) \
                and menu_item.get("watched_episodes", 0) \
                and menu_item.get("episode_count", 0) == menu_item.get("watched_episodes", 0):
            info["playcount"] = 1
        if (
                menu_item.get("watched_episodes", 0) == 0
                and menu_item.get("episode_count", 0)
                and menu_item.get("episode_count", 0) > 0
        ):
            item.setProperty("WatchedEpisodes", g.UNICODE(0))
            item.setProperty(
                "UnWatchedEpisodes", g.UNICODE(menu_item.get("episode_count", 0))
            )
        if "episode_count" in menu_item:
            item.setProperty("TotalEpisodes", g.UNICODE(menu_item["episode_count"]))
        if "season_count" in menu_item:
            item.setProperty("TotalSeasons", g.UNICODE(menu_item["season_count"]))
        if (
                "percent_played" in menu_item
                and menu_item.get("percent_played") is not None
        ):
            if float(menu_item.get("percent_played", 0)) > 0:
                item.setProperty("percentplayed", g.UNICODE(menu_item["percent_played"]))
        if "resume_time" in menu_item and menu_item.get("resume_time") is not None:
            if int(menu_item.get("resume_time", 0)) > 0:
                params["resume"] = g.UNICODE(menu_item["resume_time"])
                item.setProperty("resumetime", g.UNICODE(menu_item["resume_time"]))
                # Temporarily disabling total time for pregoress indicators as it breaks resume
                # item.setProperty("totaltime", g.UNICODE(info["duration"]))
        if "play_count" in menu_item and menu_item.get("play_count") is not None:
            info["playcount"] = menu_item["play_count"]
        if "description" in params:
            info["plot"] = info["overview"] = info["description"] = params.pop(
                "description", None
            )
        if "special_sort" in params:
            item.setProperty("SpecialSort", g.UNICODE(params["special_sort"]))
        label2 = params.pop("label2", None)
        if label2 is not None:
            item.setLabel2(label2)

        if params.pop("is_playable", False) or params.get("is_movie", False):
            item.setProperty("IsPlayable", "true")
            is_folder = params.pop("is_folder", False)
        else:
            item.setProperty("IsPlayable", "false")
            is_folder = params.pop("is_folder", True)

        cast = menu_item.get("cast", [])
        if cast is None or not isinstance(cast, (set, list)):
            cast = []
        item.setCast(cast)

        [
            item.setProperty(key, g.UNICODE(value))
            for key, value in info.items()
            if key.endswith("_id")
        ]
        item.setUniqueIDs(
            {
                id_: info[i]
                for i in info.keys()
                for id_ in ["imdb", "tvdb", "tmdb", "anidb"]
                if i == "{}_id".format(id_)
            }
        )
        [
            item.setRating(
                i.split(".")[1], float(info[i].get("rating", 0.0)), int(info[i].get("votes", 0)), False
            )
            for i in info.keys()
            if i.startswith("rating.")
        ]

        cm = params.pop("cm", [])
        if cm is None or not isinstance(cm, (set, list)):
            cm = []
        item.addContextMenuItems(cm)

        art = menu_item.pop("art", {})
        if art is None or not isinstance(art, dict):
            art = {}
        if (
                art.get("fanart", art.get("season.fanart", art.get("tvshow.fanart", None)))
                is None
        ):
            art["fanart"] = self.DEFAULT_FANART
        if (
                art.get("poster", art.get("season.poster", art.get("tvshow.poster", None)))
                is None
        ):
            art["poster"] = self.DEFAULT_ICON
        if art.get("icon") is None:
            art["icon"] = self.DEFAULT_FANART
        if art.get("thumb") is None:
            art["thumb"] = self.DEFAULT_ICON
        if "next page" in name.lower():
            art["poster"] = os.path.join(self.IMAGES_PATH, 'next.png')
            art["icon"] = os.path.join(self.IMAGES_PATH, 'next.png')
            art["thumb"] = os.path.join(self.IMAGES_PATH, 'next.png')
        try:
            art = {key: value if '/' in value or '\\' in value else os.path.join(self.IMAGES_PATH, value) for key, value in art.items()}
            item.setArt(art)
        except:
            pass

        # Clear out keys not relevant to Kodi info labels
        self.clean_info_keys(info)
        media_type = info.get("mediatype", None)
        # Only TV shows/seasons/episodes have associated times, movies just have dates.
        g.log("Media type: {}".format(media_type), "debug")
        if media_type in [g.MEDIA_SHOW, g.MEDIA_SEASON, g.MEDIA_EPISODE]:
            # Convert dates to localtime for display
            g.log("Converting TV Info Dates to local time for display", "debug")
            self.convert_info_dates(info)
        url = self.create_url(self.BASE_URL, params)

        if not g.get_bool_setting("watchlist.update.enabled"):
            if params['action'] == 'get_sources' or params['action'] == 'play_movie':
                from resources.lib.ui import database
                pc = info.get('playcount')
                if not pc:
                    default_playcount = database.checkPlayed(url)
                    if default_playcount:
                        info['playcount'] = default_playcount['playCount']
                elif int(pc) == 0:
                    default_playcount = database.checkPlayed(url)
                    if default_playcount:
                        info['playcount'] = default_playcount['playCount']
        item.setInfo("video", info)

        bulk_add = params.pop("bulk_add", False)

        if bulk_add:
            return url, item, is_folder
        else:
            xbmcplugin.addDirectoryItem(
                handle=self.PLUGIN_HANDLE, url=url, listitem=item, isFolder=is_folder
            )

    def add_menu_items(self, item_list):
        xbmcplugin.addDirectoryItems(self.PLUGIN_HANDLE, item_list, len(item_list))

    @staticmethod
    def clean_info_keys(info_dict):
        if info_dict is None:
            return None

        if not isinstance(info_dict, dict):
            return info_dict

        keys_to_remove = [i for i in info_dict.keys() if i not in info_labels]
        [info_dict.pop(key) for key in keys_to_remove]

        return info_dict

    @staticmethod
    def convert_info_dates(info_dict):
        if info_dict is None:
            return None

        if not isinstance(info_dict, dict):
            return info_dict

        dates_to_convert = [i for i in info_dict.keys() if i in info_dates]
        converted_dates = {key: control.utc_to_local(info_dict.get(key))
                           for key in dates_to_convert if info_dict.get(key)}
        info_dict.update(converted_dates)
        return info_dict

    def close_directory(self, content_type, sort=False, cache=False):
        if sort == "title":
            xbmcplugin.addSortMethod(
                self.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE
            )
        if sort == "episode":
            xbmcplugin.addSortMethod(self.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_EPISODE)
        if not sort:
            xbmcplugin.addSortMethod(self.PLUGIN_HANDLE, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.setContent(self.PLUGIN_HANDLE, content_type)
        menu_caching = self.get_bool_setting("general.menucaching") or cache
        xbmcplugin.endOfDirectory(self.PLUGIN_HANDLE, cacheToDisc=menu_caching)
        self.set_view_type(content_type)

    def set_view_type(self, content_type):
        def _execute_set_view_mode(view):
            xbmc.sleep(200)
            xbmc.executebuiltin("Container.SetViewMode({})".format(view))

        if self.get_bool_setting("general.setViews") and self.is_addon_visible():
            view_type = self.get_view_type(content_type)
            if view_type > 0:
                control.run_threaded(_execute_set_view_mode, view_type)

    @staticmethod
    def is_addon_visible():
        return xbmc.getCondVisibility("Window.IsMedia")

    def cancel_directory(self):
        xbmcplugin.setContent(self.PLUGIN_HANDLE, g.CONTENT_FOLDER)
        xbmcplugin.endOfDirectory(self.PLUGIN_HANDLE, cacheToDisc=False)

    def read_all_text(self, file_path):
        try:
            f = xbmcvfs.File(file_path, "r")
            return f.read()
        except IOError:
            return None
        finally:
            try:
                f.close()
            except:
                pass

    def write_all_text(self, file_path, content):
        try:
            f = xbmcvfs.File(file_path, "w")
            return f.write(content)
        except IOError:
            return None
        finally:
            try:
                f.close()
            except:
                pass

    # @staticmethod
    # def _apply_listitem_properties(item, info):
    #     for i in listitem_properties:
    #         if isinstance(i[0], tuple):
    #             value = info
    #             for subkey in i[0]:
    #                 value = value.get(subkey, {})
    #             if value:
    #                 item.setProperty(i[1], g.UNICODE(value))
    #         elif i[0] in info:
    #             item.setProperty(i[1], g.UNICODE(info[i[0]]))

    def create_url(self, base_url, params):
        if params is None:
            return base_url
        if params.pop("is_movie", False):
            params["action"] = 'play_movie'
        if "action_args" in params and isinstance(params["action_args"], dict):
            params["action_args"] = json.dumps(params["action_args"], sort_keys=True)
        params["from_widget"] = "true" if not self.is_addon_visible() else "false"
        return "{}/?{}".format(base_url, control.urlencode(sorted(params.items())))

    def container_update(self, replace=False):
        url = self.create_url(self.BASE_URL, self.REQUEST_PARAMS)

        if replace:
            return xbmc.executebuiltin('Container.Update({},replace)'.format(url))
        else:
            return xbmc.executebuiltin('Container.Update({})'.format(url))

    @staticmethod
    def abort_requested():
        monitor = xbmc.Monitor()
        abort_requested = monitor.abortRequested()
        del monitor
        return abort_requested

    @staticmethod
    def reload_profile():
        xbmc.executebuiltin('LoadProfile({})'.format(xbmc.getInfoLabel("system.profilename")))

    @staticmethod
    def wait_for_abort(timeout=1.0):
        monitor = xbmc.Monitor()
        abort_requested = monitor.waitForAbort(timeout)
        del monitor
        return abort_requested

    def validate_date(self, date_string):
        """Validates the path and returns only the date portion, if it invalidates it just returns none.
        :param date_string:string value with a supposed date.
        :type date_string:str
        :return:formatted datetime or none
        :rtype:str
        """

        result = None
        if not date_string:
            return date_string

        try:
            result = control.parse_datetime(date_string, self.DATE_FORMAT, False)
        except ValueError:
            pass

        if not result:
            try:
                result = control.parse_datetime(date_string, self.DATE_TIME_FORMAT_ZULU, False)
            except ValueError:
                pass

        if not result:
            try:
                result = control.parse_datetime(date_string, self.DATE_TIME_FORMAT, False)
            except ValueError:
                pass

        if not result:
            try:
                result = control.parse_datetime(date_string, "%d %b %Y", False)
            except ValueError:
                pass

        if result and result.year > 1900:
            return g.UNICODE(result.strftime(self.DATE_TIME_FORMAT))
        return None

g = GlobalVariables()