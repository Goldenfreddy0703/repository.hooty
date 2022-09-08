# -*- coding: utf-8 -*-
from __future__ import absolute_import
from builtins import map
from builtins import str
import json
from .ui import database
from resources.lib.ui.globals import g
from resources.lib.ui import control
from .debrid import all_debrid, real_debrid, premiumize
from . import pages
from .ui.BrowserBase import BrowserBase
from .indexers import simkl, trakt, tmdb, tmdb2
import ast
import re
import requests
import datetime
from resources.lib.database.cache import use_cache
from resources.lib.database.anilist_sync import shows
from resources.lib.modules.list_builder import ListBuilder


class KaitoBrowser(BrowserBase):

    def __init__(self, title_key=None):
        self.shows_database = shows.AnilistSyncDatabase()
        self.list_builder = ListBuilder()

    def _parse_history_view(self, res):
        name = res
        return g.allocate_item(name, "search/" + name + "/1", True)

    def _parse_airing_dub_view(self, res):
        mal_id = res['mal_id']
        name = res['title']
        image = res['image']
        menu_item = {
            'art': {
                'poster': image,
                'fanart': image,
                'keyart': image
            },
            "info": {
                "mediatype": 'tvshow',
            }
        }

        g.add_directory_item(
            name,
            action='mal_season_episodes',
            action_args={"mal_id": mal_id},
            menu_item=menu_item
        )

    def _json_request(self, url, data=''):
        response = json.loads(self._get_request(url, data))
        return response

    # TODO: Not sure i want this here..
    def search_history(self, history_array):
        g.add_directory_item(
            "New Search",
            action="search",
            menu_item={"art": {'poster': 'new search.png',
                               'thumb': 'new search.png',
                               'icon': 'new search.png'}}
        )

        if g.get_bool_setting("general.menus"):
            for i in history_array:
                action_args = {
                    'query': i,
                    'page': 1
                }
                g.add_directory_item(
                    i,
                    action="search",
                    action_args=control.construct_action_args(action_args),
                )
        else:
            for i in history_array:
                g.add_directory_item(
                    i,
                    action="search_results",
                    action_args=control.construct_action_args(i),
                )
        g.add_directory_item(
            "Clear Search History...",
            action="clear_history",
            mediatype="tvshow",
            menu_item={"art": {'poster': 'clear search history.png',
                               'icon': 'clear search history.png',
                               'thumb': 'clear search history.png'}},
            is_folder=False,
        )
        g.close_directory(g.CONTENT_MENU)

    def get_airing_dub(self):
        resp = requests.get('https://arm2.vercel.app/api/airingdub')

        if not resp.ok:
            return []

        all_results = list(map(self._parse_airing_dub_view, resp.json()))
        g.close_directory(g.CONTENT_SHOW)

    def get_latest(self, real_debrid_enabled, premiumize_enabled):
        if real_debrid_enabled or premiumize_enabled:
            page = pages.nyaa.sources
        else:
            page = pages.gogoanime.sources

        latest = page().get_latest()
        return latest

    def get_latest_dub(self, real_debrid_enabled, premiumize_enabled):
        if real_debrid_enabled or premiumize_enabled:
            page = pages.nyaa.sources
        else:
            page = pages.gogoanime.sources

        latest_dub = page().get_latest_dub()
        return latest_dub

    @use_cache(168)
    def get_backup(self, anilist_id, source):
        item_information = control.get_item_information(anilist_id)
        mal_id = item_information['mal_id']

        if not mal_id:
            mal_id = self.get_mal_id(anilist_id)
            self.shows_database.mark_show_record(
                "mal_id",
                mal_id,
                anilist_id
            )

        result = requests.get("https://arm2.vercel.app/api/kaito-b?type=myanimelist&id={}".format(mal_id)).json()
        result = result.get('Pages', {})
        result = result.get(source, {})
        return result

    def get_anilist_id(self, mal_id):
        arm_resp = self._json_request("https://armkai.vercel.app/api/search?type=mal&id={}".format(mal_id))
        anilist_id = arm_resp["anilist"]
        return anilist_id

    def get_mal_id(self, anilist_id):
        arm_resp = self._json_request("https://armkai.vercel.app/api/search?type=anilist&id={}".format(anilist_id))
        mal_id = arm_resp["mal"]
        return mal_id

    def clean_show(self, show_id, meta_ids):
        database.add_meta_ids(show_id, meta_ids)
        database.remove_season(show_id)
        database.remove_episodes(show_id)
        name = ast.literal_eval(database.get_show(show_id)['kodi_meta'])
        name.pop('fanart', None)
        database.add_fanart(show_id, name)

    def show_seasons(self, args):
        item_information = control.get_item_information(args["anilist_id"])
        episode_indexer = item_information["episode_indexer"]
        episode_count = item_information["episode_count"]
        simkl_id = item_information["simkl_id"]
        trakt_id = item_information["trakt_id"]
        tmdb_id = item_information["tmdb_id"]
        # tmdb_result = tmdb2.TMDBAPI().get_episodes(tmdb_id, item_information)
        # if tmdb_result:
        #     self.shows_database.format_tmdb_episodes(tmdb_result, args["anilist_id"], tmdb_id, trakt_id)
        #     self.list_builder._common_menu_builder(
        #         tmdb_result, 
        #         g.CONTENT_EPISODE, 
        #         is_folder=False, 
        #         is_playable=True, 
        #         sort="episode",
        #         no_paging=True
        #     )
        # self.list_builder.episode_list_builder(args["anilist_id"], trakt_id, None, alt_indexer=True, no_paging=True)
        # tmdb_id = tmdb2.TMDBAPI().get_anime_tmdb_id(item_information)
        # self.list_builder._common_menu_builder(tmdb_id, g.CONTENT_EPISODE, is_folder=False, is_playable=True, sort="episode")
        # import xbmcgui
        # xbmcgui.Dialog().textviewer('sdsd', str(tmdb_id))      
        # self.list_builder._common_menu_builder(simkl.SIMKLAPI().get_episodes(41066), g.CONTENT_EPISODE)
        # # if trakt_id:
        # #     # self.list_builder.season_list_builder(args["anilist_id"], item_information.get('trakt_id'), no_paging=True)
        # #     season = shows.AnilistSyncDatabase().get_season_list(args["anilist_id"], trakt_id, no_paging=True)
        # #     self.list_builder.episode_list_builder(
        # #         args["anilist_id"], item_information.get('trakt_id'), None, no_paging=True
        # #         )
        if not episode_indexer:
            meta_ids = {}
            if not trakt_id:
                meta_ids = trakt.TRAKTAPI().get_trakt_id(item_information)
                if meta_ids:
                    for i in meta_ids.keys():
                        for id_ in ["trakt", "imdb", "tvdb", "tmdb"]:
                            if i == id_:
                                self.shows_database.mark_show_record(
                                    "{}_id".format(id_),
                                    meta_ids[i],
                                    args["anilist_id"]
                                )
                    trakt_id = meta_ids['trakt']

                if not trakt_id:
                    trakt_id = 0
                    self.shows_database.mark_show_record(
                        "trakt_id",
                        0,
                        args["anilist_id"]
                    )
                    # tmdb_id = tmdb2.TMDBAPI().search_show_tmdb_id(item_information)
                    # simkl_id = simkl.SIMKLAPI().get_simkl_id(item_information)

                    # if tmdb_id:
                    #     meta_ids = trakt.TRAKTAPI().get_tmdb_to_trakt(tmdb_id)
                    #     if meta_ids:
                    #         for i in meta_ids.keys():
                    #             for id_ in ["trakt", "imdb", "tvdb", "tmdb"]:
                    #                 if i == id_:
                    #                     self.shows_database.mark_show_record(
                    #                         "{}_id".format(id_),
                    #                         meta_ids[i],
                    #                         args["anilist_id"]
                    #                     )
                    #         trakt_id = meta_ids['trakt']  

            if trakt_id and trakt_id != 0:
                if args["anilist_id"] in {113538, 119661, 104578, 116742, 127720, 127400}:
                    self.shows_database.mark_show_record("episode_indexer", "tmdb_season", args["anilist_id"])
                    tmdb_result = tmdb2.TMDBAPI().get_season(args["anilist_id"], item_information)
                    self.shows_database.format_tmdb_episodes(tmdb_result, args["anilist_id"], tmdb_id, trakt_id)
                    return self.list_builder.episode_alt_list_builder(args["anilist_id"], sort="episode", no_paging=True)

                season = shows.AnilistSyncDatabase().get_season_list(args["anilist_id"], trakt_id, no_paging=True)

                if season:
                    self.list_builder.episode_list_builder(args["anilist_id"], trakt_id, None, sort="episode", no_paging=True)
                    self.shows_database.mark_show_record("episode_indexer", "trakt", args["anilist_id"])
                elif not episode_count or episode_count > 40:
                    if meta_ids:
                        tmdb_id = meta_ids['tmdb']
                    if not tmdb_id:
                        tmdb_id = tmdb2.TMDBAPI().search_show_tmdb_id(item_information)
                    if tmdb_id:
                        tmdb_result = tmdb2.TMDBAPI().get_episodes(tmdb_id, item_information)
                        if tmdb_result:
                            self.shows_database.format_tmdb_episodes(tmdb_result, args["anilist_id"], tmdb_id, trakt_id)
                            self.list_builder.episode_alt_list_builder(args["anilist_id"], sort="episode", no_paging=True)
                            self.shows_database.mark_show_record("episode_indexer", "tmdb", args["anilist_id"])
                        else:
                            if not simkl_id:
                                simkl_id = simkl.SIMKLAPI().get_simkl_id(item_information)

                            simkl_result = simkl.SIMKLAPI().get_episodes(simkl_id, item_information)
                            if simkl_result:
                                self.shows_database.format_simkl_episodes(simkl_result, args["anilist_id"], tmdb_id, trakt_id)
                                self.list_builder.episode_alt_list_builder(args["anilist_id"], sort="episode", no_paging=True)
                                self.shows_database.mark_show_record("episode_indexer", "simkl", args["anilist_id"])
                else:
                    if not simkl_id:
                        simkl_id = simkl.SIMKLAPI().get_simkl_id(item_information)

                    simkl_result = simkl.SIMKLAPI().get_episodes(simkl_id, item_information)
                    if simkl_result:
                        self.shows_database.format_simkl_episodes(simkl_result, args["anilist_id"], tmdb_id, trakt_id)
                        self.list_builder.episode_alt_list_builder(args["anilist_id"], sort="episode", no_paging=True)
                        self.shows_database.mark_show_record("episode_indexer", "simkl", args["anilist_id"])
            elif tmdb_id:
                tmdb_result = tmdb2.TMDBAPI().get_episodes(tmdb_id, item_information)
                if tmdb_result:
                    self.shows_database.format_tmdb_episodes(tmdb_result, args["anilist_id"], tmdb_id, trakt_id)
                    self.list_builder.episode_alt_list_builder(args["anilist_id"], sort="episode", no_paging=True)
                    self.shows_database.mark_show_record("episode_indexer", "tmdb", args["anilist_id"])
            elif simkl_id:
                simkl_result = simkl.SIMKLAPI().get_episodes(simkl_id, item_information)
                if simkl_result:
                    self.shows_database.format_simkl_episodes(simkl_result, args["anilist_id"], tmdb_id, trakt_id)
                    self.list_builder.episode_alt_list_builder(args["anilist_id"], sort="episode", no_paging=True)
                    self.shows_database.mark_show_record("episode_indexer", "simkl", args["anilist_id"])
            else:
                simkl_id = simkl.SIMKLAPI().get_simkl_id(item_information)
                simkl_result = simkl.SIMKLAPI().get_episodes(simkl_id, item_information)
                if simkl_result:
                    self.shows_database.format_simkl_episodes(simkl_result, args["anilist_id"], tmdb_id, trakt_id)
                    self.list_builder.episode_alt_list_builder(args["anilist_id"], sort="episode", no_paging=True)
                    self.shows_database.mark_show_record("episode_indexer", "simkl", args["anilist_id"])
        else:
            if episode_indexer == "trakt":
                season = shows.AnilistSyncDatabase().get_season_list(args["anilist_id"], trakt_id, no_paging=True)
                self.list_builder.episode_list_builder(args["anilist_id"], trakt_id, None, sort="episode", no_paging=True)
            elif episode_indexer == "tmdb_season":
                tmdb_result = tmdb2.TMDBAPI().get_season(args["anilist_id"], item_information)
                self.shows_database.format_tmdb_episodes(tmdb_result, args["anilist_id"], tmdb_id, trakt_id)
                return self.list_builder.episode_alt_list_builder(args["anilist_id"], sort="episode", no_paging=True)
            elif episode_indexer == "tmdb":
                tmdb_result = tmdb2.TMDBAPI().get_episodes(tmdb_id, item_information)
                if tmdb_result:
                    self.shows_database.format_tmdb_episodes(tmdb_result, args["anilist_id"], tmdb_id, trakt_id)
                    self.list_builder.episode_alt_list_builder(args["anilist_id"], sort="episode", no_paging=True)
            elif episode_indexer == "simkl":
                simkl_result = simkl.SIMKLAPI().get_episodes(simkl_id, item_information)
                if simkl_result:
                    self.shows_database.format_simkl_episodes(simkl_result, args["anilist_id"], tmdb_id, trakt_id)
                    self.list_builder.episode_alt_list_builder(args["anilist_id"], sort="episode", no_paging=True)

                # self.shows_database.update_show_art(
                #     "fanart",
                #     tmdb.TMDBAPI().showFanart(meta_ids)['fanart'],
                #     args["anilist_id"]
                # )
                # season = shows.AnilistSyncDatabase().get_season_list(args["anilist_id"], meta_ids['trakt'], no_paging=True)
                # self.list_builder.episode_list_builder(
                #     args["anilist_id"], item_information.get('trakt_id'), None, no_paging=True
                #     )
                # self.list_builder.season_list_builder(args["anilist_id"], meta_ids['trakt'], no_paging=True)

        # seasons = trakt.TRAKTAPI().get_anime(item_information, trakt_id)
        # self.list_builder.season_list_builder(trakt_id, no_paging=True)

    def mal_season_episodes(self, args):
        item_information = control.get_item_information_mal(args["mal_id"])
        if item_information:
            _args = item_information
        else:
            _args = {
                'anilist_id': self.get_anilist_id(args["mal_id"])
            }
        
        self.show_seasons(_args)

    def season_episodes(self, args):
        self.list_builder.episode_list_builder(
            args["anilist_id"], args["trakt_show_id"], args["trakt_id"], no_paging=True
        )

    def is_anime_part(self, anilist_id):
        simkl_id = None
        anime_part = {
            113538: {
                "simkl_id": 1229235,
            },
            119661: {
                "simkl_id": 1367345,
            },
            104578: {
                "simkl_id": 931899,
            }
        }

        if anilist_id in anime_part:
            simkl_id = anime_part[anilist_id]["simkl_id"]
            self.shows_database.mark_show_record(
                "simkl_id",
                simkl_id,
                anilist_id
            )
        
        return simkl_id

    def search_trakt_shows(self, anilist_id):
        shows = trakt.TRAKTAPI().search_trakt_shows(anilist_id)
        return shows

    def get_trakt_episodes(self, show_id, season, page=1):
        return trakt.TRAKTAPI().get_trakt_episodes(show_id, season)

    def get_anime_trakt(self, anilist_id, db_correction=False, filter_lang=None):
        anime = trakt.TRAKTAPI().get_anime(anilist_id, db_correction)

        if anime and filter_lang:
            for i in anime[0]:
                i['url'] += filter_lang

        if not anime:
            anime = self.get_anime_simkl(anilist_id, filter_lang)

        return anime

    def get_anime_simkl(self, anilist_id, params):
        return simkl.SIMKLAPI().get_anime(anilist_id, params)

    def get_anime_init(self, anilist_id, filter_lang=None):
        show_meta = database.get_show(anilist_id)

        if not show_meta:
            from .AniListBrowser import AniListBrowser
            show_meta = AniListBrowser().get_anilist(anilist_id)

        if not show_meta['trakt_id']:
            item_information = control.get_item_information(anilist_id)
            trakt_id = trakt.TRAKTAPI().get_trakt_id(item_information)

            if not trakt_id:
                return self.get_anime_simkl(anilist_id, filter_lang)

            database.add_meta_ids(anilist_id, trakt_id['trakt'], 'trakt_id')
            database.add_meta_ids(anilist_id, trakt_id['tvdb'], 'tvdb_id')
            database.add_meta_ids(anilist_id, trakt_id['tmdb'], 'tmdb_id')

        return self.get_anime_trakt(anilist_id, filter_lang=filter_lang)

    def build_playlist(self, args):
        # episodes = database.get_episode_list(int(show_id))

        # if episodes:
        #     items = trakt.TRAKTAPI()._process_trakt_episodes(show_id, '', episodes, '')
        # else:
        #     items = simkl.SIMKLAPI().get_episodes(show_id)

        # if rescrape:
        #     return items
        anilist_id = args['anilist_id']
        item_information = control.get_item_information(anilist_id)
        simkl_id = item_information["simkl_id"]
        trakt_id = item_information["trakt_id"]
        tmdb_id = item_information["tmdb_id"]

        try:
            [
                g.PLAYLIST.add(url=i[0], listitem=i[1])
                for i in self.list_builder.episode_list_builder(
                    anilist_id,
                    trakt_id,
                    minimum_episode=None,
                    smart_play=True,
                    hide_unaired=True,
                )
            ]
        except TypeError:
            g.log(
                "Unable to add more episodes to the playlist, they may not be available for the requested season",
                "warning",
            )
            return

        # if indexer == 'trakt':
        #     items = self.list_builder.episode_list_builder(show_id, trakt_id, None, no_paging=True, smart_play=True, hide_unaired=True)
        # elif indexer == 'tmdb':
        #     items = self.list_builder._common_menu_builder(
        #         tmdb2.TMDBAPI().get_episodes(tmdb_id, item_information), 
        #         g.CONTENT_EPISODE, 
        #         is_folder=False, 
        #         is_playable=True, 
        #         sort="episode",
        #         no_paging=True,
        #         smart_play=True,
        #         hide_unaired=True
        #     )
        # elif indexer == 'simkl':
        #     items = self.list_builder._common_menu_builder(
        #         simkl.SIMKLAPI().get_episodes(simkl_id, item_information), 
        #         g.CONTENT_EPISODE,
        #         is_folder=False, 
        #         is_playable=True, 
        #         sort="episode",
        #         no_paging=True,
        #         smart_play=True,
        #         hide_unaired=True
        #     )

        # try:
        #     [
        #         g.PLAYLIST.add(url=i[0], listitem=i[1])
        #         for i in items
        #     ]
        #     import xbmcgui
        #     xbmcgui.Dialog().textviewer("dfffdd", 'pla')
        # except TypeError:
        #     import xbmcgui
        #     xbmcgui.Dialog().textviewer("dfffdd", str(items))
        #     g.log(
        #         "Unable to add more episodes to the playlist, they may not be available for the requested season",
        #         "warning",
        #     )
        #     return

    def is_aired(self, info):
        try:
            try:
                air_date = info['aired']               
            except:
                air_date = info.get('premiered')
            if not air_date:
                return False
            if int(air_date[:4]) < 2019:
                return True

            todays_date = datetime.datetime.today().strftime('%Y-%m-%d')

            if air_date > todays_date:
                return False
            else:
                return True
        except:
            import traceback
            traceback.print_exc()
            # Assume an item is not aired if we do not have any information on it or fail to identify
            return False

    def get_sources(self, anilist_id, episode, filter_lang, media_type, rescrape=False):
        # show = database.get_show(anilist_id)
        # kodi_meta = ast.literal_eval(show['kodi_meta'])
        item_information = control.get_item_information(anilist_id)
        actionArgs = {
            'query': item_information['info']['aliases'],
            'anilist_id': anilist_id,
            'episode': episode,
            'status': item_information['info'].get('status'),
            'filter_lang': filter_lang,
            'media_type': media_type,
            'rescrape': rescrape,
            'get_backup': self.get_backup
            }
        sources = pages.getSourcesHelper(actionArgs)
        return sources

    def get_latest_sources(self, debrid_provider, hash_):
        resolvers = {'premiumize':  premiumize.Premiumize,
                     'all_debrid': all_debrid.AllDebrid,
                     'real_debrid': real_debrid.RealDebrid}

        magnet = 'magnet:?xt=urn:btih:' + hash_
        api = resolvers[debrid_provider]
        link = api().resolve_single_magnet(hash_, magnet)
        return link
