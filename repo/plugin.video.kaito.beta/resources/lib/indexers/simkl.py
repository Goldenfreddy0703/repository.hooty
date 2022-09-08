# -*- coding: utf-8 -*-
from __future__ import absolute_import
from builtins import map
from builtins import str
from builtins import object
import requests
import json
import ast
from functools import partial
from functools import wraps
from .tmdb import TMDBAPI
from ..ui import database
from resources.lib.ui import control
from resources.lib.indexers.apibase import (
    ApiBase,
    handle_single_item_or_list,
)
from resources.lib.ui.globals import g
from resources.lib.database.cache import use_cache
from resources.lib.database.anilist_sync import shows


def wrap_simkl_object(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        return {"simkl_object": func(*args, **kwarg)}

    return wrapper

class SIMKLAPI(ApiBase):
    """
    Class to handle interactions with Simkl API
    """

    baseUrl = "https://api.simkl.com/"
    imageBaseUrl = "https://simkl.in/"

    def __init__(self):
        self.ClientID = "5178a709b7942f1f5077b737b752eea0f6dee684d0e044fa5acee8822a0cbe9b"
        # self.baseUrl = "https://api.simkl.com/"
        # self.imageBaseUrl = "https://simkl.in/episodes/%s_w.jpg"
        self.art = {}
        self.request_response = None
        self.threads = []
        self.shows_database = shows.AnilistSyncDatabase()
        self.meta_hash = control.md5_hash((self.baseUrl, self.imageBaseUrl))

        self.artwork_url_structure = {
            "fanart": "fanart/{}_medium.jpg",
            "episodes": "episodes/{}_w.jpg"
        }

        self.TranslationNormalization = [
            ("title", ("title", "sorttitle"), None),
            ("description", ("plot", "plotoutline"), None),
        ]

        self.Normalization = control.extend_array(
            [
                (("ids", "simkl_id"), "simkl_id", None),
                (("ids", "tmdb_id"), "tmdb_id", None),
                ("type", "mediatype", None),
            ],
            self.TranslationNormalization,
        )

        self.MoviesNormalization = control.extend_array(
            [
                ("plays", "playcount", None),
                ("year", "year", None),
                ("released", ("premiered", "aired"), lambda t: g.validate_date(t)),
            ],
            self.Normalization,
        )

        self.ShowNormalization = control.extend_array(
            [
                ("status", "status", None),
                ("status", "is_airing", lambda t: not t == "ended"),
                ("tvshowtitle", "tvshowtitle", None),
                ("year", "year", None),
                (
                    "first_aired",
                    ("premiered", "aired"),
                    lambda t: g.validate_date(t),
                ),
            ],
            self.Normalization,
        )

        self.SeasonNormalization = control.extend_array(
            [
                ("number", ("season", "sortseason"), None),
                ("episode_count", "episode_count", None),
                ("aired_episodes", "aired_episodes", None),
                (
                    "first_aired",
                    "year",
                    lambda t: g.validate_date(t)[:4]
                    if g.validate_date(t)
                    else None
                ),
                (
                    "first_aired",
                    ("premiered", "aired"),
                    lambda t: g.validate_date(t),
                ),
            ],
            self.Normalization,
        )

        self.EpisodeNormalization = control.extend_array(
            [
                ("episode", ("episode", "sortepisode"), None),
                ("season", ("season", "sortseason"), None),
                ("args", "args", None),
                ("tvshowtitle", "tvshowtitle", None),
                (
                    "date",
                    "year",
                    lambda t: g.validate_date(t)[:4]
                    if g.validate_date(t)
                    else None
                ),
                (
                    "date",
                    ("premiered", "aired"),
                    lambda t: g.validate_date(t[:19]),
                ),
            ],
            self.Normalization,
        )

        self.ListNormalization = [
            ("date", "dateadded", lambda t: g.validate_date(t)),
            (("ids", "trakt"), "trakt_id", None),
            (("ids", "slug"), "slug", None),
            ("sort_by", "sort_by", None),
            ("sort_how", "sort_how", None),
            (("user", "ids", "slug"), "username", None),
            ("name", ("name", "title"), None),
            ("type", "mediatype", None),
        ]

        self.MixedEpisodeNormalization = [
            (("show", "ids", "trakt"), "trakt_show_id", None),
            (("episode", "ids", "trakt"), "trakt_id", None),
            ("show", "show", None),
            ("episode", "episode", None),
        ]

        self.MetaObjects = {
            "movie": self.MoviesNormalization,
            "list": self.ListNormalization,
            "tvshow": self.ShowNormalization,
            "season": self.SeasonNormalization,
            "episode": self.EpisodeNormalization,
            "mixedepisode": self.MixedEpisodeNormalization,
        }

        self.MetaCollections = ("movies", "shows", "seasons", "episodes")

        self.session = requests.Session()

    def _to_url(self, url=''):
        if url.startswith("/"):
            url = url[1:]

        return "%s/%s" % (self.baseUrl, url)

    def _json_request(self, url, data=''):
        response = requests.get(url, data)
        response = response.json()
        return response

    def get(self, url, **params):
        return self.session.get(
            control.urljoin(self.baseUrl, url),
            data=params,
        )

    def get_json(self, url, **params):
        response = self.get(url, **params)
        if response is None:
            return None
        return self._handle_response(response.json())

    @use_cache()
    def get_json_cached(self, url, **params):
        response = self.get(url, **params)
        if response is None:
            return None
        return response.json()

    @handle_single_item_or_list
    def _handle_response(self, item):
        result = {}
        self._try_detect_type(item)
        # self._apply_localized_alternative_titles(item)
        # self._apply_releases(item)
        # self._apply_content_ratings(item)
        # self._apply_release_dates(item)
        # self._apply_trailers(item)
        result.update({"art": self._handle_artwork(item)})
        # result.update({"cast": self._handle_cast(item)})
        if item.get("mediatype"):
            result.update(
                {
                    "info": self._normalize_info(
                        self.MetaObjects[item["mediatype"]], item
                    )
                }
            )

        return result

    @staticmethod
    def _try_detect_type(item):
        _type = item.get('type')
        if _type == 'movie':
            item.update({"mediatype": "movie"})
        elif _type == 'episode':
            item.update({"mediatype": "episode"})
            item.update({"season": 1})
        else:
            item.update({"mediatype": "tvshow"})
        return item

    def _handle_artwork(self, item):
        result = {}
        if item.get("img") is not None:
            result.update(
                {
                    "thumb": "{}/episodes/{}_w.jpg".format(self.imageBaseUrl, item["img"]),
                    "fanart": "{}/episodes/{}_w.jpg".format(self.imageBaseUrl, item["img"]),
                }
            )
        if item.get("poster_path") is not None:
            result.update(
                {
                    "poster": item["poster_path"],
                }
            )
        # if item.get("img") is not None:
        #     result.update(
        #         {
        #             "fanart": "{}/episodes/{}_w.jpg".format(self.imageBaseUrl, item["image"]),
        #         }
        #     )
        return result

    def _get_absolute_image_path(self, relative_path, size="orginal"):
        if not relative_path:
            return None
        return "/".join(
            [self.imageBaseUrl.strip("/"), relative_path.strip("/")]
        )

        # # if item.get("poster_path") is not None:
        # #     result.update(
        # #         {
        # #             "poster": self._get_absolute_image_path(
        # #                 item["poster_path"],
        # #                 self._create_tmdb_image_size(self.artwork_size["poster"]),
        # #             )
        # #         }
        # #     )
        # images = item.get("images", item)
        # for tmdb_type, kodi_type, selector in self.art_normalization:
        #     if tmdb_type not in images or not images[tmdb_type]:
        #         continue
        #     result.update(
        #         {
        #             kodi_type: [
        #                 {
        #                     "url": self._get_absolute_image_path(
        #                         i["file_path"],
        #                         self._create_tmdb_image_size(
        #                             self.artwork_size[kodi_type]
        #                         ),
        #                     ),
        #                     "language": i["iso_639_1"]
        #                     if i["iso_639_1"] != "xx"
        #                     else None,
        #                     "rating": self._normalize_rating(i),
        #                     "size": int(
        #                         i["width" if tmdb_type != "posters" else "height"]
        #                     )
        #                     if int(i["width" if tmdb_type != "posters" else "height"])
        #                     < self.artwork_size[kodi_type]
        #                     else self.artwork_size[kodi_type],
        #                 }
        #                 for i in images[tmdb_type]
        #                 if selector is None or selector(i)
        #             ]
        #         }
        #     )
        return result

    def _parse_episode_view(self, res, anilist_id, poster, fanart, eps_watched, filter_lang):
        url = "%s/%s/" % (anilist_id, res['episode'])

        if filter_lang:
            url += filter_lang
        
        name = 'Ep. %d (%s)' % (res['episode'], res.get('title'))
        #image =  self.imageBaseUrl % res['img']
        info = {}
        info['plot'] = res['description']
        info['title'] = res['title']
        info['season'] = 1
        info['episode'] = res['episode']

        try:
            info['aired'] = res['date'][:10]
        except:
            pass
        import pickle
        info['tvshowtitle'] = pickle.loads(database.get_show(anilist_id)['info'])['title']
        info['mediatype'] = 'episode'
        parsed = g.allocate_item(name, "play/" + str(url), False, None, info, None, None, True)
        return parsed

    def _process_episode_view(self, anilist_id, json_resp, filter_lang, base_plugin_url, page):
        kodi_meta = database.get_show(anilist_id)['info']
        fanart = kodi_meta.get('fanart')
        poster = kodi_meta.get('poster')
        eps_watched = kodi_meta.get('eps_watched')
        json_resp = [x for x in json_resp if x['type'] == 'episode']
        mapfunc = partial(self._parse_episode_view, anilist_id=anilist_id, poster=poster, fanart=fanart, eps_watched=eps_watched, filter_lang=filter_lang)
        all_results = list(map(mapfunc, json_resp))

        return all_results

    def get_anime(self, anilist_id, filter_lang):
        show = database.get_show(anilist_id)

        if show['simkl_id']:
            return self.get_episodes(show['simkl_id'], control.get_item_information(anilist_id)), 'episodes'

        import pickle
        kodi_meta = pickle.loads(show['info'])
        mal_id = show['mal_id']

        if not mal_id:
            mal_id = self.get_mal_id(anilist_id)
            database.add_mapping_id(anilist_id, 'mal_id', str(mal_id))

        simkl_id = str(self.get_anime_id(mal_id))
        #import web_pdb
        #web_pdb.set_trace()
        database.add_mapping_id(anilist_id, 'simkl_id', simkl_id)
        #if show:
            #if not kodi_meta.get('fanart'):
                #kodi_meta['fanart'] = TMDBAPI().showFanart(show).get('fanart')
                #database.update_kodi_meta(int(anilist_id), kodi_meta)

        return self.get_episodes(simkl_id, control.get_item_information(anilist_id)), 'episodes'

    def _get_episodes(self, anilist_id):
        simkl_id = database.get_show(anilist_id)['simkl_id']
        data = {
            "extended": 'full',
        }
        url = self._to_url("anime/episodes/%s" % str(simkl_id))
        json_resp = self._json_request(url, data)
        return json_resp

    # def get_episodes(self, anilist_id, filter_lang=None, page=1):
    #     episodes = database.get(self._get_episodes, 6, anilist_id)
    #     return self._process_episode_view(anilist_id, episodes, filter_lang, "animes_page/%s/%%d" % anilist_id, page)

    def get_anime_search(self, q):
        data = {
            "q": q,
            "client_id": self.ClientID
        }
        json_resp = self._json_request("https://api.simkl.com/search/anime", data)
        if not json_resp:
            return []

        anime_id = json_resp[0]['ids']['simkl_id']
        return anime_id

    @wrap_simkl_object
    def get_show(self, simkl_id):
        return self.get_json_cached(
            "anime/{}?extended=full".format(simkl_id)
        )

    def get_episodes(self, simkl_id, item_information):
        # simkl_id = self.get_id(item_information)
        # if not simkl_id:
        #     return
        episodes = self.get_json_cached(
            "anime/episodes/{}?extended=full".format(simkl_id)
        )
        episodes = [episode for episode in episodes if episode.get("type") == "episode"]
        ret = []
        for episode in episodes:
            episode.update(
                {
                    "tvshowtitle": item_information["info"]["title"],
                    "poster_path": item_information["art"].get("poster"),
                    "args": self._create_args(item_information, episode["episode"]),
                }
            )
            if g.get_bool_setting('general.menus'):
                tmp = self._parse_episode_view(episode, item_information['anilist_id'], None, None, item_information['watched_episodes'], None)
                ret.append(tmp)
        if g.get_bool_setting("general.menus"):
            return ret
        else:
            return self._handle_response(episodes)


    def get_simkl_id(self, item_information):
        mal_id = item_information["mal_id"]
        if not mal_id:
            mal_id = self.get_mal_id(item_information["anilist_id"])
        data = {
            "mal": mal_id,
            "client_id": self.ClientID,
        }
        url = self._to_url("search/id")
        json_resp = self._json_request(url, data)
        if not json_resp:
            return []

        simkl_id = json_resp[0]['ids'].get('simkl')

        self.shows_database.mark_show_record(
            "simkl_id",
            simkl_id,
            item_information["anilist_id"]
        )

        return simkl_id

    def get_anime_id(self, mal_id):
        data = {
            "mal": mal_id,
            "client_id": self.ClientID,
        }
        url = self._to_url("search/id")
        json_resp = self._json_request(url, data)
        if not json_resp:
            return []

        anime_id = json_resp[0]['ids'].get('simkl')
        return anime_id

    def get_mal_id(self, anilist_id):
        arm_resp = self._json_request("https://armkai.vercel.app/api/search?type=anilist&id={}".format(anilist_id))
        mal_id = arm_resp["mal"]
        return mal_id

    @staticmethod
    def _create_args(item_information, episode_number):
        args = {
            "anilist_id": item_information["anilist_id"],
            "mediatype": "episode",
            "episode": episode_number,
            "trakt_show_id": item_information["trakt_id"],
            "trakt_season_id": None,
            "indexer": "simkl",
        }
        return control.quote(json.dumps(args, sort_keys=True))