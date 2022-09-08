# -*- coding: utf-8 -*-
from __future__ import absolute_import
from builtins import map
from builtins import str
from builtins import object
import requests
import json
import ast
from functools import partial
from datetime import datetime
from .tmdb import TMDBAPI
from ..ui import database
from resources.lib.ui import control
from resources.lib.indexers.apibase import (
    ApiBase,
    handle_single_item_or_list,
)
from resources.lib.ui.globals import g
from resources.lib.database.cache import use_cache

class AnilistAPI(ApiBase):
    """
    Class to handle interactions with Anilist API
    """

    _URL = "https://graphql.anilist.co"

    def __init__(self):
        self.title_language = self._get_title_language()
        self.get_hasNextPage = ('data', 'Page', 'pageInfo', 'hasNextPage')
        self.meta_hash = control.md5_hash((self.title_language, self._URL))

        self.query = {
            'anime/id': self.anime_id_query,
            'search/anime/list': self.anime_list_query,
            'search/anime/genre': self.anime_genre_query,
            'search/anime': self.anime_search_query,
            'search/anime/recommendations': self.anime_recommendation_query,
            'anime/specificidmal': self.anime_specific_query_mal,
            'anime/specificidani': self.anime_specific_query_ani
            }

        self.TranslationNormalization = [
            (
                "title", 
                "title", 
                lambda t: self._get_title(t)
            ),
            ("description", ("plot", "plotoutline"), None),
        ]

        self.Normalization = control.extend_array(
            [
                ("genres", "genre", None),
                ("id", "anilist_id", None),
                ("idMal", "mal_id", None),
                ("duration", "duration", lambda d: d * 60),
                (
                    "startDate", 
                    ("premiered", "aired"), 
                    lambda t: self._format_date(t),
                ),
                ("startDate", "dateadded", lambda t: self._get_date_added(t)),
                ("endDate", "dateended", lambda t: self._format_date(t)),
                ("title", "aliases", lambda t: self._get_titles(t)),
                ("type", "mediatype", lambda t: t if "show" not in t else "tvshow"),
            ],
            self.TranslationNormalization,
        )

        self.MoviesNormalization = control.extend_array(
            [
                ("episodes", "episode_count", None),
                (("startDate", "year"), "year", None),
                (   
                    "startDate", 
                    ("premiered", "aired"), 
                    lambda t: self._format_date(t),
                ),
            ],
            self.Normalization,
        )

        self.ShowNormalization = control.extend_array(
            [
                ("status", "status", None),
                ("status", "is_airing", lambda t: not t in {'FINISHED', 'NOT_YET_RELEASED'}),
                ("episodes", "episode_count", None),
                (
                    "title", 
                    "tvshowtitle", 
                    lambda t: self._get_title(t)
                ),
                ("startDate", "year", lambda t: t['year']),
                (
                    "startDate",
                    ("premiered", "aired"), 
                    lambda t: self._format_date(t),
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
                    lambda t: control.validate_date(t)[:4]
                    if control.validate_date(t)
                    else None
                ),
                (
                    "first_aired",
                    ("premiered", "aired"),
                    lambda t: control.validate_date(t),
                ),
            ],
            self.Normalization,
        )

        self.EpisodeNormalization = control.extend_array(
            [
                ("number", ("episode", "sortepisode"), None),
                ("season", ("season", "sortseason"), None),
                ("collected_at", "collected", lambda t: 1),
                ("plays", "playcount", None),
                (
                    "first_aired",
                    "year",
                    lambda t: control.validate_date(t)[:4]
                    if control.validate_date(t)
                    else None
                ),
                (
                    "first_aired",
                    ("premiered", "aired"),
                    lambda t: control.validate_date(t),
                ),
            ],
            self.Normalization,
        )

        self.ArtNormalization = [
            (("coverImage", "extraLarge"), "fanart", None),
            (("coverImage", "extraLarge"), "poster", None),
            (("coverImage", "extraLarge"), "keyart", None),
        ]

        self.ListNormalization = [
            ("updated_at", "dateadded", lambda t: control.validate_date(t)),
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
            "show": self.ShowNormalization,
            "season": self.SeasonNormalization,
            "episode": self.EpisodeNormalization,
            "mixedepisode": self.MixedEpisodeNormalization,
        }

        self.MetaCollections = ("movies", "shows", "seasons", "episodes")

        self.session = requests.Session()

    def _get_title_language(self):
        title_language = g.get_setting("titlelanguage").lower()

        if 'english' in title_language:
            _title_language = 'english'
        else:
            _title_language = 'userPreferred'

        return _title_language

    def post(self, url, data):
        """
        Performs a post request to the specified endpoint and returns response
        :param url: URL endpoint to perform request to
        :param data: POST Data to send to endpoint
        :return: requests response
        """
        return self.session.post(url, json=data)

    def post_json(self, url, **params):
        """
        Performs a post request to specified endpoint, sorts results and returns JSON response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: JSON response
        """
        get_dict = params.pop('dict_key')
        query_path = params.pop('query_path')
        if query_path:
            params["query"] = self.query[query_path]()

        response = self.post(url, params)

        if response is None:
            return None
        try:
            response_json = response.json()

            hasNextPage = self._get_value(self.get_hasNextPage, {}, response_json)

            return (
                self._handle_response(
                    self._get_value(get_dict, '', response_json)
                    ),
                hasNextPage
            )
        except (ValueError, AttributeError) as e:
            g.log(
                "Failed to receive JSON from Anilist response - response: {} - error - {}".format(
                    response, e
                ),
                "error",
            )
            return None

    @use_cache()
    def post_cached(self, url, **params):
        """
        Performs a post request to specified endpoint, caches and returns response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: request response
        """
        return self.post(url, params)


    @use_cache()
    def post_json_cached(self, url, **params):
        """
        Performs a powt request to endpoint, caches and returns a json response from anilist endpoint
        :param url: URL endpoint to perform request to
        :param params: url parameters
        :return: json response from anilist
        """
        return self.post_json(url, **params)

    @handle_single_item_or_list
    def _handle_response(self, item):
        if item.get("mediaRecommendation"):
            item = item.get("mediaRecommendation")
        item = self._try_detect_type(item)
        art = self._handle_artwork(item)
        # if item.get("type") == "castcrew":
        #     item.pop("type")
        #     item = self._handle_response(
        #         [i.get("movie", i.get("show")) for i in item.pop("cast", [])]
        #     )
        #     return item
        # item = self._flatten_if_single_type(item)
        # item = self._try_detect_type(item)
        if not item.get("type") or item.get("type") not in self.MetaObjects:
            return item
        # if item["type"] == "mixedepisode":
        #     single_type = self._handle_single_type(item)
        #     [
        #         single_type.update({meta: self._handle_response(item.pop(meta, {}))})
        #         for meta in self.MetaObjects
        #         if meta in item
        #     ]
        #     single_type.update(item)
        #     return single_type
        return self._create_anilist_object(self._handle_single_type(item), art)

    @staticmethod
    def _create_anilist_object(item, art):
        result = {"anilist_object": {"info": item, "art": art}}
        [
            result.update({key: value})
            for key, value in item.items()
            if key.endswith("_id")
        ]
        return result

    def _handle_single_type(self, item):
        # translated = self._handle_translation(item)
        translated = item
        collections = {}
        # collections = {
        #     key: self._handle_response(translated[key])
        #     for key in self.MetaCollections
        #     if key in translated
        # }
        normalized = self._normalize_info(self.MetaObjects[item["type"]], translated)
        normalized.update(collections)
        return normalized

    # @handle_single_item_or_list
    # def _flatten_if_single_type(self, item):
    #     media_type = item.get("type")
    #     if media_type and media_type in item:
    #         key = media_type
    #     else:
    #         keys = [meta for meta in self.MetaObjects if meta in item]
    #         if len(keys) == 1:
    #             key = keys[0]
    #         else:
    #             return item
    #     if isinstance(item[key], dict):
    #         item.update(item.pop(key))
    #         item.update({"type": key})
    #     return item

    @staticmethod
    @handle_single_item_or_list
    def _try_detect_type(item):
        if item['format'] == 'MOVIE' and item['episodes'] == 1:
            item_type = 'movie'
        else:
            item_type = 'show'

        item.update({"type": item_type})
        return item

    def _handle_artwork(self, item):
        result = {}

        for anilist_type, kodi_type, selector in self.ArtNormalization:

            result.update(
                {
                    kodi_type: self._get_value(anilist_type, {}, item)
                }
            )

        return result

    def _get_title(self, item):
        title = item.get(self.title_language)
        if not title:
            title = item.get('userPreferred')
        title = title.encode('ascii','ignore').decode("utf-8")
        return title

    @staticmethod
    def _get_titles(item):
        titles = list(set(item.values()))
        # if res['format'] == 'MOVIE':
        #     titles = list(item['title'].values())
        titles = list(map(lambda x: x.encode('ascii','ignore').decode("utf-8") if x else [], titles))[:3]
        titles = [x for x in titles if x]
        query_titles = '({})'.format(')|('.join(map(str, titles)))
        return query_titles

    @staticmethod
    def _format_date(item):
        try:
            start_date = '{}-{:02}-{:02}'.format(item['year'], item['month'], item['day'])
        except:
            start_date = None
        finally:
            return start_date

    @staticmethod
    def _get_date_added(item):
        try:
            date_added = '{}-{:02}-{:02}'.format(item['year'], item['month'], item['day'])
        except:
            date_added = datetime.today().strftime('%Y-%m-%d')
        finally:
            return date_added

    def get_anilist_id(self, anilist_id):
        variables = {
            'id': anilist_id,
            'type': "ANIME"
            }

        dict_key = ('data', 'Media')

        show = self.post_json(
            self._URL, query_path='anime/id', variables=variables, dict_key=dict_key)[0]
        
        return show

    @staticmethod
    def anime_specific_query_mal():
        query = "query ($idMal: [Int], $page: Int = 1) {Page(page: $page, perPage: 100) {pageInfo {total perPage currentPage lastPage hasNextPage}media(idMal_in: $idMal, type: ANIME) {id idMal title{userPreferred english}coverImage{extraLarge large color}startDate{year month day}endDate{year month day}bannerImage season description type format status(version:2) episodes duration chapters volumes genres isAdult averageScore popularity nextAiringEpisode{airingAt timeUntilAiring episode}mediaListEntry{id status}studios(isMain:true){edges{isMain node{id name}}}}}}"
        return query

    @staticmethod
    def anime_specific_query_ani():
        query = "query ($id: [Int], $page: Int = 1) {Page(page: $page, perPage: 100) {pageInfo {total perPage currentPage lastPage hasNextPage}media(id_in: $id, type: ANIME) {id idMal title{userPreferred english}coverImage{extraLarge large color}startDate{year month day}endDate{year month day}bannerImage season description type format status(version:2) episodes duration chapters volumes genres isAdult averageScore popularity nextAiringEpisode{airingAt timeUntilAiring episode}mediaListEntry{id status}studios(isMain:true){edges{isMain node{id name}}}}}}"
        return query

    @staticmethod
    def anime_list_query():
        query = "query($page:Int = 1 $id:Int $type:MediaType $isAdult:Boolean = false $search:String $format:[MediaFormat]$status:MediaStatus $countryOfOrigin:CountryCode $source:MediaSource $season:MediaSeason $seasonYear:Int $year:String $onList:Boolean $yearLesser:FuzzyDateInt $yearGreater:FuzzyDateInt $episodeLesser:Int $episodeGreater:Int $durationLesser:Int $durationGreater:Int $chapterLesser:Int $chapterGreater:Int $volumeLesser:Int $volumeGreater:Int $licensedBy:[String]$isLicensed:Boolean $genres:[String]$excludedGenres:[String]$tags:[String]$excludedTags:[String]$minimumTagRank:Int $sort:[MediaSort]=[POPULARITY_DESC,SCORE_DESC]){Page(page:$page,perPage:20){pageInfo{total perPage currentPage lastPage hasNextPage}media(id:$id type:$type season:$season format_in:$format status:$status countryOfOrigin:$countryOfOrigin source:$source search:$search onList:$onList seasonYear:$seasonYear startDate_like:$year startDate_lesser:$yearLesser startDate_greater:$yearGreater episodes_lesser:$episodeLesser episodes_greater:$episodeGreater duration_lesser:$durationLesser duration_greater:$durationGreater chapters_lesser:$chapterLesser chapters_greater:$chapterGreater volumes_lesser:$volumeLesser volumes_greater:$volumeGreater licensedBy_in:$licensedBy isLicensed:$isLicensed genre_in:$genres genre_not_in:$excludedGenres tag_in:$tags tag_not_in:$excludedTags minimumTagRank:$minimumTagRank sort:$sort isAdult:$isAdult){id idMal title{userPreferred english}coverImage{extraLarge large color}startDate{year month day}endDate{year month day}bannerImage season description type format status(version:2)episodes duration chapters volumes genres isAdult averageScore popularity nextAiringEpisode{airingAt timeUntilAiring episode}mediaListEntry{id status}studios(isMain:true){edges{isMain node{id name}}}}}}"
        return query

    @staticmethod
    def anime_genre_query():
        query = "query($page:Int = 1 $id:Int $type:MediaType $isAdult:Boolean = false $search:String $format:[MediaFormat]$status:MediaStatus $countryOfOrigin:CountryCode $source:MediaSource $season:MediaSeason $seasonYear:Int $year:String $onList:Boolean $yearLesser:FuzzyDateInt $yearGreater:FuzzyDateInt $episodeLesser:Int $episodeGreater:Int $durationLesser:Int $durationGreater:Int $chapterLesser:Int $chapterGreater:Int $volumeLesser:Int $volumeGreater:Int $licensedBy:[String]$isLicensed:Boolean $genres:[String]$excludedGenres:[String]$tags:[String]$excludedTags:[String]$minimumTagRank:Int $sort:[MediaSort]=[POPULARITY_DESC,SCORE_DESC]){Page(page:$page,perPage:20){pageInfo{total perPage currentPage lastPage hasNextPage}media(id:$id type:$type season:$season format_in:$format status:$status countryOfOrigin:$countryOfOrigin source:$source search:$search onList:$onList seasonYear:$seasonYear startDate_like:$year startDate_lesser:$yearLesser startDate_greater:$yearGreater episodes_lesser:$episodeLesser episodes_greater:$episodeGreater duration_lesser:$durationLesser duration_greater:$durationGreater chapters_lesser:$chapterLesser chapters_greater:$chapterGreater volumes_lesser:$volumeLesser volumes_greater:$volumeGreater licensedBy_in:$licensedBy isLicensed:$isLicensed genre_in:$genres genre_not_in:$excludedGenres tag_in:$tags tag_not_in:$excludedTags minimumTagRank:$minimumTagRank sort:$sort isAdult:$isAdult){id idMal title{userPreferred english}coverImage{extraLarge large color}startDate{year month day}endDate{year month day}bannerImage season description type format status(version:2)episodes duration chapters volumes genres isAdult averageScore popularity nextAiringEpisode{airingAt timeUntilAiring episode}mediaListEntry{id status}studios(isMain:true){edges{isMain node{id name}}}}}}"
        return query

    @staticmethod
    def anime_search_query():
        query = "query($page:Int = 1 $id:Int $type:MediaType $isAdult:Boolean = false $search:String $format:[MediaFormat]$status:MediaStatus $countryOfOrigin:CountryCode $source:MediaSource $season:MediaSeason $seasonYear:Int $year:String $onList:Boolean $yearLesser:FuzzyDateInt $yearGreater:FuzzyDateInt $episodeLesser:Int $episodeGreater:Int $durationLesser:Int $durationGreater:Int $chapterLesser:Int $chapterGreater:Int $volumeLesser:Int $volumeGreater:Int $licensedBy:[String]$isLicensed:Boolean $genres:[String]$excludedGenres:[String]$tags:[String]$excludedTags:[String]$minimumTagRank:Int $sort:[MediaSort]=[POPULARITY_DESC,SCORE_DESC]){Page(page:$page,perPage:20){pageInfo{total perPage currentPage lastPage hasNextPage}media(id:$id type:$type season:$season format_in:$format status:$status countryOfOrigin:$countryOfOrigin source:$source search:$search onList:$onList seasonYear:$seasonYear startDate_like:$year startDate_lesser:$yearLesser startDate_greater:$yearGreater episodes_lesser:$episodeLesser episodes_greater:$episodeGreater duration_lesser:$durationLesser duration_greater:$durationGreater chapters_lesser:$chapterLesser chapters_greater:$chapterGreater volumes_lesser:$volumeLesser volumes_greater:$volumeGreater licensedBy_in:$licensedBy isLicensed:$isLicensed genre_in:$genres genre_not_in:$excludedGenres tag_in:$tags tag_not_in:$excludedTags minimumTagRank:$minimumTagRank sort:$sort isAdult:$isAdult){id idMal title{userPreferred english}coverImage{extraLarge large color}startDate{year month day}endDate{year month day}bannerImage season description type format status(version:2)episodes duration chapters volumes genres isAdult averageScore popularity nextAiringEpisode{airingAt timeUntilAiring episode}mediaListEntry{id status}studios(isMain:true){edges{isMain node{id name}}}}}}"
        return query

    @staticmethod
    def anime_id_query():
        query = '''
        query($id: Int, $type: MediaType){Media(id: $id, type: $type) {
            id
            idMal
            title {
                userPreferred,
                romaji,
                english
            }
            coverImage {
                extraLarge
            }
            startDate {
                year,
                month,
                day
            }
            description
            synonyms
            format
            episodes
            status
            genres
            duration
            }
        }
        '''

        return query

    @staticmethod
    def anime_recommendation_query():
        query = '''
        query media($id:Int,$page:Int){Media(id:$id) {
            id
            recommendations (page:$page, perPage: 20, sort:[RATING_DESC,ID]) {
                pageInfo {
                    hasNextPage
                }
                nodes {
                    mediaRecommendation {
                        id
                        idMal
                        title {
                            userPreferred,
                            romaji,
                            english
                        }
                        format
                        type
                        status
                        coverImage {
                            extraLarge
                        }
                        startDate {
                            year,
                            month,
                            day
                        }
                        endDate {
                            year,
                            month,
                            day
                        }
                        description
                        duration
                        genres
                        synonyms
                        episodes
                        format
                    }
                }
            }
        }
                                       }
        '''

        return query

class AnilistAPI_animelist(ApiBase):
    """
    Class to handle interactions with Anilist API user animelist
    """

    _URL = "https://graphql.anilist.co"

    def __init__(self):
        self.title_language = self._get_title_language()
        self.get_hasNextPage = ('data', 'Page', 'pageInfo', 'hasNextPage')
        self.meta_hash = control.md5_hash((self.title_language, self._URL))

        self.query = {
            'animelist/status': self.animelist_status_query,
            'animelist/allstatus': self.all_animelist_status_query
            }

        self.TranslationNormalization = [
            (
                "title", 
                "title", 
                lambda t: self._get_title(t)
            ),
            ("description", ("plot", "plotoutline"), None),
        ]

        self.Normalization = control.extend_array(
            [
                ("genres", "genre", None),
                ("id", "anilist_id", None),
                ("idMal", "mal_id", None),
                ("duration", "duration", lambda d: d * 60),
                (
                    "startDate", 
                    ("premiered", "aired"), 
                    lambda t: self._format_date(t),
                ),
                ("startDate", "dateadded", lambda t: self._get_date_added(t)),
                ("endDate", "dateended", lambda t: self._format_date(t)),
                ("title", "aliases", lambda t: self._get_titles(t)),
                ("type", "mediatype", lambda t: t if "show" not in t else "tvshow"),
            ],
            self.TranslationNormalization,
        )

        self.MoviesNormalization = control.extend_array(
            [
                ("episodes", "episode_count", None),
                (("startDate", "year"), "year", None),
                (   
                    "startDate", 
                    ("premiered", "aired"), 
                    lambda t: self._format_date(t),
                ),
            ],
            self.Normalization,
        )

        self.ShowNormalization = control.extend_array(
            [
                ("status", "status", None),
                ("status", "is_airing", lambda t: not t in {'FINISHED', 'NOT_YET_RELEASED'}),
                ("episodes", "episode_count", None),
                ("progress_title", "progress_title", None),
                (
                    "title", 
                    "tvshowtitle", 
                    lambda t: self._get_title(t)
                ),
                ("startDate", "year", lambda t: t['year']),
                (
                    "startDate",
                    ("premiered", "aired"), 
                    lambda t: self._format_date(t),
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
                    lambda t: control.validate_date(t)[:4]
                    if control.validate_date(t)
                    else None
                ),
                (
                    "first_aired",
                    ("premiered", "aired"),
                    lambda t: control.validate_date(t),
                ),
            ],
            self.Normalization,
        )

        self.EpisodeNormalization = control.extend_array(
            [
                ("number", ("episode", "sortepisode"), None),
                ("season", ("season", "sortseason"), None),
                ("collected_at", "collected", lambda t: 1),
                ("plays", "playcount", None),
                (
                    "first_aired",
                    "year",
                    lambda t: control.validate_date(t)[:4]
                    if control.validate_date(t)
                    else None
                ),
                (
                    "first_aired",
                    ("premiered", "aired"),
                    lambda t: control.validate_date(t),
                ),
            ],
            self.Normalization,
        )

        self.ArtNormalization = [
            (("coverImage", "extraLarge"), "fanart", None),
            (("coverImage", "extraLarge"), "poster", None),
            (("coverImage", "extraLarge"), "keyart", None),
        ]

        self.ListNormalization = [
            ("updated_at", "dateadded", lambda t: control.validate_date(t)),
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
            "show": self.ShowNormalization,
            "season": self.SeasonNormalization,
            "episode": self.EpisodeNormalization,
            "mixedepisode": self.MixedEpisodeNormalization,
        }

        self.MetaCollections = ("movies", "shows", "seasons", "episodes")

        self.session = requests.Session()

    def _get_title_language(self):
        title_language = g.get_setting("titlelanguage").lower()

        if 'english' in title_language:
            _title_language = 'english'
        else:
            _title_language = 'userPreferred'

        return _title_language

    def post(self, url, data):
        """
        Performs a post request to the specified endpoint and returns response
        :param url: URL endpoint to perform request to
        :param data: POST Data to send to endpoint
        :return: requests response
        """
        return self.session.post(url, json=data)

    def post_json(self, url, **params):
        """
        Performs a post request to specified endpoint, sorts results and returns JSON response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: JSON response
        """

        get_dict = params.pop('dict_key')
        query_path = params.pop('query_path')
        if query_path:
            params["query"] = self.query[query_path]()

        response = self.post(url, params)

        if response is None:
            return None
        try:
            response_json = response.json()

            hasNextPage = self._get_value(self.get_hasNextPage, {}, response_json)

            return (
                self._handle_response(
                    self._get_value(get_dict, '', response_json)
                    ),
                hasNextPage
            )
        except (ValueError, AttributeError) as e:
            g.log(
                "Failed to receive JSON from Anilist response - response: {} - error - {}".format(
                    response, e
                ),
                "error",
            )
            return None

    @use_cache()
    def post_cached(self, url, **params):
        """
        Performs a post request to specified endpoint, caches and returns response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: request response
        """
        return self.post(url, params)


    #@use_cache()
    def post_json_cached(self, url, **params):
        """
        Performs a powt request to endpoint, caches and returns a json response from anilist endpoint
        :param url: URL endpoint to perform request to
        :param params: url parameters
        :return: json response from anilist
        """
        return self.post_json(url, **params)

    @handle_single_item_or_list
    def _handle_response(self, item):
        item = self._try_detect_type(item)
        item = self._add_progress_title(item)
        art = self._handle_artwork(item)
        # if item.get("type") == "castcrew":
        #     item.pop("type")
        #     item = self._handle_response(
        #         [i.get("movie", i.get("show")) for i in item.pop("cast", [])]
        #     )
        #     return item
        # item = self._flatten_if_single_type(item)
        # item = self._try_detect_type(item)
        if not item.get("type") or item.get("type") not in self.MetaObjects:
            return item
        # if item["type"] == "mixedepisode":
        #     single_type = self._handle_single_type(item)
        #     [
        #         single_type.update({meta: self._handle_response(item.pop(meta, {}))})
        #         for meta in self.MetaObjects
        #         if meta in item
        #     ]
        #     single_type.update(item)
        #     return single_type
        return self._create_anilist_object(self._handle_single_type(item), art)

    @staticmethod
    def _create_anilist_object(item, art):
        result = {"anilist_object": {"info": item, "art": art}}
        [
            result.update({key: value})
            for key, value in item.items()
            if key.endswith("_id")
        ]
        return result

    def _handle_single_type(self, item):
        # translated = self._handle_translation(item)
        translated = item
        collections = {}
        # collections = {
        #     key: self._handle_response(translated[key])
        #     for key in self.MetaCollections
        #     if key in translated
        # }
        normalized = self._normalize_info(self.MetaObjects[item["type"]], translated)
        normalized.update(collections)
        return normalized

    # @handle_single_item_or_list
    # def _flatten_if_single_type(self, item):
    #     media_type = item.get("type")
    #     if media_type and media_type in item:
    #         key = media_type
    #     else:
    #         keys = [meta for meta in self.MetaObjects if meta in item]
    #         if len(keys) == 1:
    #             key = keys[0]
    #         else:
    #             return item
    #     if isinstance(item[key], dict):
    #         item.update(item.pop(key))
    #         item.update({"type": key})
    #     return item

    @staticmethod
    @handle_single_item_or_list
    def _try_detect_type(item):
        progress = item['progress']
        item = item['media']
        if item['format'] == 'MOVIE' and item['episodes'] == 1:
            item_type = 'movie'
        else:
            item_type = 'show'

        item.update({"type": item_type, "progress": progress})
        return item

    def _add_progress_title(self, item):
        progress_title = '{} - {}/{}'.format(
            self._get_title(item["title"]),
            item["progress"],
            item['episodes'] if item['episodes'] is not None else 0
        )

        item.update({"progress_title": progress_title})
        return item

    def _handle_artwork(self, item):
        result = {}

        for anilist_type, kodi_type, selector in self.ArtNormalization:

            result.update(
                {
                    kodi_type: self._get_value(anilist_type, {}, item)
                }
            )

        return result

    def _get_title(self, item):
        title = item.get(self.title_language)
        if not title:
            title = item.get('userPreferred')
        title = title.encode('ascii','ignore').decode("utf-8")
        return title

    @staticmethod
    def _get_titles(item):
        titles = list(set(item.values()))
        # if res['format'] == 'MOVIE':
        #     titles = list(item['title'].values())
        titles = list(map(lambda x: x.encode('ascii','ignore').decode("utf-8") if x else [], titles))[:3]
        titles = [x for x in titles if x]
        query_titles = '({})'.format(')|('.join(map(str, titles)))
        return query_titles

    @staticmethod
    def _format_date(item):
        try:
            start_date = '{}-{:02}-{:02}'.format(item['year'], item['month'], item['day'])
        except:
            start_date = None
        finally:
            return start_date

    @staticmethod
    def _get_date_added(item):
        try:
            date_added = '{}-{:02}-{:02}'.format(item['year'], item['month'], item['day'])
        except:
            date_added = datetime.today().strftime('%Y-%m-%d')
        finally:
            return date_added

    @staticmethod
    def all_animelist_status_query():
        query = '''
        query ($userId: Int, $userName: String, $status_in: [MediaListStatus], $type: MediaType, $sort: [MediaListSort]) {
            MediaListCollection(userId: $userId, userName: $userName, status_in: $status_in, type: $type, sort: $sort) {
                lists {
                    entries {
                        ...mediaListEntry
                        }
                    }
                }
            }

        fragment mediaListEntry on MediaList {
            id
            mediaId
            status
            progress
            customLists
            media {
                id
                idMal
                title {
                    userPreferred,
                    romaji,
                    english
                }
                coverImage {
                    extraLarge
                }
                startDate {
                    year,
                    month,
                    day
                }
                description
                synonyms
                format                
                status
                episodes
                genres
                duration
            }
        }
        '''

        return query

    @staticmethod
    def animelist_status_query():
        query = '''
        query ($userId: Int, $userName: String, $status: MediaListStatus, $type: MediaType, $sort: [MediaListSort]) {
            MediaListCollection(userId: $userId, userName: $userName, status: $status, type: $type, sort: $sort) {
                lists {
                    entries {
                        ...mediaListEntry
                        }
                    }
                }
            }

        fragment mediaListEntry on MediaList {
            id
            mediaId
            status
            progress
            customLists
            media {
                id
                idMal
                title {
                    userPreferred,
                    romaji,
                    english
                }
                coverImage {
                    extraLarge
                }
                startDate {
                    year,
                    month,
                    day
                }
                description
                synonyms
                format                
                status
                episodes
                genres
                duration
            }
        }
        '''

        return query
