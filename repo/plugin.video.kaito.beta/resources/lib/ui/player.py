# -*- coding: utf-8 -*-
from __future__ import absolute_import
from builtins import range
from builtins import object
import sys
import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui
from . import http

from resources.lib.ui.globals import g
from resources.lib.ui import control
from resources.lib.modules import smartPlay
from resources.lib.database.anilist_sync import shows


kodiGui = xbmcgui
execute = xbmc.executebuiltin

playList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
player = xbmc.Player

progressDialog = xbmcgui.DialogProgress()
kodi = xbmc

class hook_mimetype(object):
    __MIME_HOOKS = {}

    @classmethod
    def trigger(cls, mimetype, item):

        if mimetype in list(cls.__MIME_HOOKS.keys()):
            return cls.__MIME_HOOKS[mimetype](item)

        return item

    def __init__(self, mimetype):
        self._type = mimetype

    def __call__(self, func):
        assert self._type not in list(self.__MIME_HOOKS.keys())
        self.__MIME_HOOKS[self._type] = func
        return func

class watchlistPlayer(xbmc.Player):

    def __init__(self):
        super(watchlistPlayer, self).__init__()
        self._on_playback_done = None
        self._on_stopped = None
        self._on_percent = None
        self._watchlist_update = None
        self.current_time = 0
        self.updated = False
        self.media_type = None
        self.season = None
        self.shows_sync = shows.AnilistSyncDatabase()
##        self.AVStarted = False

    def handle_player(self, args, watchlist_update):
        # self.anilist_id = args['anilist_id']

        if watchlist_update:
            self._watchlist_update = watchlist_update(args['anilist_id'], args['episode'])

        # self._build_playlist = build_playlist
        # self._episode = episode
        # self._filter_lang = filter_lang
        # self._indexer = indexer
        self.media_type = args['mediatype']
        self.args = args
        self.keepAlive()
        
    def onPlayBackStarted(self):
        # import xbmcgui
        # xbmcgui.Dialog().textviewer('dsdsd', str(self.args))
        if self.media_type != 'movie' and g.get_setting('smartplay.skipintrodialog') == 'true':
            while self.isPlaying():
                time_ = int(self.getTime())
                if time_ > 240:
                    break
                elif time_ >= 1:
                    PlayerDialogs()._show_skip_intro()
                    break
                else:
                    xbmc.sleep(250)

        if g.PLAYLIST.size() == 1:
            smartPlay.SmartPlay(self.args).build_playlist()
        # if self._build_playlist and g.PLAYLIST.size() == 1:
        #     self._build_playlist(self._anilist_id, self._episode, self._filter_lang, indexer=self._indexer)

        try:
            current_ = g.PLAYLIST.getposition()
            self.season = g.PLAYLIST[current_].getVideoInfoTag().getSeason()
        except:
            pass
        # g.set_setting('addon.last_watched', self._anilist_id)
        # pass

##    def onAVStarted(self):
##        self.AVStarted = True
##
##    def onAVChange(self):
##        self.AVStarted = True

    def onPlayBackStopped(self):
        g.PLAYLIST.clear()

##    def onPlayBackEnded(self):
##        pass

    def onPlayBackError(self):
        g.PLAYLIST.clear()
        sys.exit(1)

    def getWatchedPercent(self):
        try:
            current_position = self.getTime()
        except:
            current_position = self.current_time

        media_length = self.getTotalTime()
        watched_percent = 0

        if int(media_length) != 0:
            watched_percent = float(current_position) / float(media_length) * 100

        return watched_percent

    def _mark_playing_item_watched(self):
        while self.isPlaying() and not self.updated:
            try:
                watched_percentage = self.getWatchedPercent()

                try:
                    self.current_time = self.getTime()

                except:
                    import traceback
                    traceback.print_exc()
                    pass

                if watched_percentage > 80:
                    if self.season and self.media_type != 'movie':
                        self.shows_sync.mark_episode_watched(
                            self.args['anilist_id'],
                            self.season,
                            self.args['episode']
                        )

                    self.updated = True
                    break

            except:
                import traceback
                traceback.print_exc()
                xbmc.sleep(1000)
                continue

            xbmc.sleep(1000)

        else:
            return


    def onWatchedPercent(self):
        if not self._watchlist_update:
            return self._mark_playing_item_watched()

        while self.isPlaying() and not self.updated:
            try:
                watched_percentage = self.getWatchedPercent()

                try:
                    self.current_time = self.getTime()

                except:
                    import traceback
                    traceback.print_exc()
                    pass

                if watched_percentage > 80:
                    self._watchlist_update()

                    if self.season and self.media_type != 'movie':
                        self.shows_sync.mark_episode_watched(
                            self.args['anilist_id'],
                            self.season,
                            self.args['episode']
                        )

                    self.updated = True
                    break

            except:
                import traceback
                traceback.print_exc()
                xbmc.sleep(1000)
                continue

            xbmc.sleep(1000)

        else:
            return

    def keepAlive(self):
        for i in range(0, 480):
            if self.isPlayingVideo():
                break
            xbmc.sleep(250)

##        for i in range(0, 480):
##            if self.AVStarted:
##                break

        # g.close_all_dialogs()

        try:
            audio_lang = self.getAvailableAudioStreams()
            if len(audio_lang) > 1:
                try:
                    preferred_audio = int(g.get_setting('general.audio'))
                    audio_int = audio_lang.index(g.lang(preferred_audio))
                    self.setAudioStream(audio_int)
                except:
                    pass
                try:
                    if preferred_audio == 40315:
                        self.setSubtitleStream(1)
                except:
                    pass
        except:
            pass

        # if self.media_type == 'movie':
        #     return self.onWatchedPercent()

        scrobble = self.onWatchedPercent()

        if g.get_setting('smartplay.playingnextdialog') == 'true':
            endpoint = int(g.get_setting('playingnext.time'))
        else:
            endpoint = False

        if endpoint:
            while self.isPlaying():
                if int(self.getTotalTime()) - int(self.getTime()) <= endpoint:
                    xbmc.executebuiltin('RunPlugin("plugin://plugin.video.kaito?action=run_player_dialogs")')
                    break
                else:
                    xbmc.sleep(1000)

class PlayerDialogs(xbmc.Player):

    def __init__(self):
        super(PlayerDialogs, self).__init__()
        self._min_time = 30
        self.playing_file = self.getPlayingFile()

    def display_dialog(self):

        if g.PLAYLIST.size() == 0 or g.PLAYLIST.getposition() == (g.PLAYLIST.size() - 1):
            return

        target = self._show_playing_next

        if self.playing_file != self.getPlayingFile():
            return

        if not self.isPlayingVideo():
            return

        if not self._is_video_window_open():
            return

        target()

    @staticmethod
    def _still_watching_calc():
        return False

    def _show_playing_next(self):
        from resources.lib.windows.playing_next import PlayingNext

        PlayingNext(*('playing_next.xml', g.ADDON_DATA_PATH),
                    actionArgs=self._get_next_item_args()).doModal()

    def _show_skip_intro(self):
        from resources.lib.windows.skip_intro import SkipIntro

        SkipIntro(*('skip_intro.xml', g.ADDON_DATA_PATH),
                    actionArgs={'item_type': 'skip_intro'}).doModal()

    def _show_still_watching(self):
        return True

    @staticmethod
    def _get_next_item_args():
        current_position = g.PLAYLIST.getposition()
        next_item = g.PLAYLIST[  # pylint: disable=unsubscriptable-object
            current_position + 1
        ]
        
        next_info = {
            "art": {}
        }
        next_info['episode'] = next_item.getVideoInfoTag().getEpisode()
        next_info['season'] = next_item.getVideoInfoTag().getSeason()
        next_info['tvshowtitle'] = next_item.getVideoInfoTag().getTVShowTitle()
        next_info['aired'] = next_item.getVideoInfoTag().getFirstAired()
        next_info['rating'] = next_item.getVideoInfoTag().getRating()
        next_info['art']['thumb'] = next_item.getArt('thumb')
        next_info['name'] = next_item.getLabel()
        next_info['playnext'] = True

        return next_info

    @staticmethod
    def _is_video_window_open():

        if kodiGui.getCurrentWindowId() != 12005:
            return False
        return True

def cancelPlayback():
    g.PLAYLIST.clear()
    xbmcplugin.setResolvedUrl(g.PLUGIN_HANDLE, False, xbmcgui.ListItem())

def _prefetch_play_link(link):
    if callable(link):
        link = link()

    if not link:
        return None

    linkInfo = http.head_request(link);
    if linkInfo.status_code != 200:
        raise Exception('could not resolve %s. status_code=%d' %
                        (link, linkInfo.status_code))
    return {
        "url": linkInfo.url,
        "headers": linkInfo.headers,
    }

def play_source(link, action_args, watchlist_update):
    linkInfo = _prefetch_play_link(link)
    if not linkInfo:
        cancelPlayback()
        return

    item = xbmcgui.ListItem(path=linkInfo['url'])

    # if rescrape:
    #     episode_info = build_playlist(anilist_id, '', filter_lang, rescrape=True)[episode - 1]
    #     item.setInfo('video', infoLabels=episode_info['info'])
    #     item.setArt(episode_info['image'])

    if 'Content-Type' in linkInfo['headers']:
        item.setProperty('mimetype', linkInfo['headers']['Content-Type'])

    # Run any mimetype hook
    item = hook_mimetype.trigger(linkInfo['headers']['Content-Type'], item)
    xbmcplugin.setResolvedUrl(g.PLUGIN_HANDLE, True, item)
    watchlistPlayer().handle_player(action_args, watchlist_update)

@hook_mimetype('application/dash+xml')
def _DASH_HOOK(item):
    import inputstreamhelper
    is_helper = inputstreamhelper.Helper('mpd')
    if is_helper.check_inputstream():
        item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        item.setProperty('inputstream.adaptive.manifest_type',
                             'mpd')
        item.setContentLookup(False)
    else:
        raise Exception("InputStream Adaptive is not supported.")

    return item

@hook_mimetype('application/vnd.apple.mpegurl')
def _HLS_HOOK(item):
    import inputstreamhelper
    is_helper = inputstreamhelper.Helper('hls')
    if is_helper.check_inputstream():
        item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        item.setProperty('inputstream.adaptive.manifest_type',
                             'hls')
        item.setContentLookup(False)
    else:
        raise Exception("InputStream Adaptive is not supported.")

    return item