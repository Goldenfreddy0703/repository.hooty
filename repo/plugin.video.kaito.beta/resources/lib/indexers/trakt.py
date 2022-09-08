# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import inspect
import threading
import time
from collections import OrderedDict
from functools import wraps

import requests
import xbmc
import xbmcgui
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from resources.lib.ui import control
from resources.lib.modules.thread_pool import ThreadPool
from resources.lib.database.cache import use_cache
from resources.lib.indexers.apibase import (
    ApiBase,
    handle_single_item_or_list,
)
from resources.lib.ui.exceptions import RanOnceAlready
from resources.lib.ui.global_lock import GlobalLock
from resources.lib.ui.globals import g

from builtins import next
from builtins import str
from builtins import map
from builtins import object
import json
import ast
import re
from functools import partial
from .tmdb import TMDBAPI
from ..ui import database

CLOUDFLARE_ERROR_MSG = "Service Unavailable - Cloudflare error"

TRAKT_STATUS_CODES = {
    200: "Success",
    201: "Success - new resource created (POST)",
    204: "Success - no content to return (DELETE)",
    400: "Bad Request - request couldn't be parsed",
    401: "Unauthorized - OAuth must be provided",
    403: "Forbidden - invalid API key or unapproved app",
    404: "Not Found - method exists, but no record found",
    405: "Method Not Found - method doesn't exist",
    409: "Conflict - resource already created",
    412: "Precondition Failed - use application/json content type",
    422: "Unprocessable Entity - validation errors",
    429: "Rate Limit Exceeded",
    500: "Server Error - please open a support issue",
    503: "Service Unavailable - server overloaded (try again in 30s)",
    504: "Service Unavailable - server overloaded (try again in 30s)",
    502: "Unspecified Error",
    520: CLOUDFLARE_ERROR_MSG,
    521: CLOUDFLARE_ERROR_MSG,
    522: CLOUDFLARE_ERROR_MSG,
    524: CLOUDFLARE_ERROR_MSG,
}


def trakt_auth_guard(func):
    """
    Decorator to ensure method will only run if a valid Trakt auth is present
    :param func: method to run
    :return: wrapper method
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        """
        Wrapper method
        :param args: method args
        :param kwargs: method kwargs
        :return: method results
        """
        if g.get_setting("trakt.auth"):
            return func(*args, **kwargs)
        elif xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30507)):
            TraktAPI2().auth()
        else:
            g.cancel_directory()

    return wrapper


def _log_connection_error(args, kwarg, e):
    g.log("Connection Error to Trakt: {} - {}".format(args, kwarg), "error")
    g.log(e, "error")


def _connection_failure_dialog():
    if (
        g.get_float_setting("general.trakt.failure.timeout") + (2 * 60 * (60 * 60))
        < time.time()
        and not xbmc.Player().isPlaying()
    ):
        xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(30025).format("Trakt"))
        g.set_setting("general.trakt.failure.timeout", g.UNICODE(time.time()))


def _reset_trakt_auth():
    settings = ["trakt.refresh", "trakt.auth", "trakt.expires", "trakt.username"]
    for i in settings:
        g.set_setting(i, "")
    xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30578))


def trakt_guard_response(func):
    """
    Decorator for Trakt API requests, handles retries and error responses
    :param func:
    :return:
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        """
        Wrapper method for decorator
        :param args: method args
        :param kwargs: method kwargs
        :return:
        """
        method_class = args[0]
        try:
            response = func(*args, **kwargs)
            if response.status_code in [200, 201, 204]:
                return response

            if (
                response.status_code == 400
                and response.url == "https://api.trakt.tv/oauth/device/token"
            ):
                return response
            if (
                response.status_code == 400
                and response.url == "https://api.trakt.tv/oauth/token"
            ):
                _reset_trakt_auth()
                raise Exception("Unable to refresh Trakt auth")

            if response.status_code == 403:
                g.log("Trakt: invalid API key or unapproved app, resetting auth", "error")
                _reset_trakt_auth()
                g.cancel_directory()
                return None

            if response.status_code == 401:
                if inspect.stack(1)[1][3] == "try_refresh_token":
                    xbmcgui.Dialog().notification(
                        g.ADDON_NAME, g.get_language_string(30373)
                    )
                    g.log(
                        "Attempts to refresh Trakt token have failed. User intervention is required",
                        "error",
                    )
                else:
                    try:
                        with GlobalLock("trakt.oauth", run_once=True, check_sum=method_class.access_token):
                            if method_class.refresh_token is not None:
                                method_class.try_refresh_token(True)
                            if (
                                method_class.refresh_token is None
                                and method_class.username is not None
                            ):
                                xbmcgui.Dialog().ok(
                                    g.ADDON_NAME, g.get_language_string(30373)
                                )
                    except RanOnceAlready:
                        pass
                    if method_class.refresh_token is not None:
                        return func(*args, **kwargs)

            g.log(
                "Trakt returned a {} ({}): while requesting {}".format(
                    response.status_code,
                    TRAKT_STATUS_CODES[response.status_code],
                    response.url,
                ),
                "error",
            )

            return response
        except requests.exceptions.ConnectionError as e:
            _log_connection_error(args, kwargs, e)
            raise
        except Exception as e:
            _connection_failure_dialog()
            _log_connection_error(args, kwargs, e)
            raise

    return wrapper


class TraktAPI2(ApiBase):
    """
    Class to handle interactions with Trakt API
    """

    ApiUrl = "https://api.trakt.tv/"

    username_setting_key = "trakt.username"

    def __init__(self):
        self._load_settings()
        self.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
        self.try_refresh_token()
        self.progress_dialog = xbmcgui.DialogProgress()
        self.language = g.get_language_code()
        self.country = g.get_language_code(True).split("-")[-1].lower()

        self.meta_hash = control.md5_hash((self.language, self.ApiUrl, self.username))

        self.TranslationNormalization = [
            ("title", ("title", "originaltitle", "sorttitle"), None),
            ("language", "language", None),
            ("overview", ("plot", "plotoutline"), None),
        ]

        self.Normalization = control.extend_array(
            [
                ("certification", "mpaa", None),
                ("genres", "genre", None),
                (("ids", "imdb"), ("imdbnumber", "imdb_id"), None),
                (("ids", "trakt"), "trakt_id", None),
                (("ids", "slug"), "trakt_slug", None),
                (("ids", "tvdb"), "tvdb_id", None),
                (("ids", "tmdb"), "tmdb_id", None),
                ("id", "playback_id", None),
                (("show", "ids", "trakt"), "trakt_show_id", None),
                ("network", "studio", lambda n: [n]),
                ("runtime", "duration", lambda d: d * 60),
                ("progress", "percentplayed", None),
                ("updated_at", "dateadded", lambda t: g.validate_date(t)),
                ("last_updated_at", "dateadded", lambda t: g.validate_date(t)),
                ("collected_at", "collected_at", lambda t: g.validate_date(t)),
                (
                    "last_watched_at",
                    "last_watched_at",
                    lambda t: g.validate_date(t),
                ),
                ("paused_at", "paused_at", lambda t: g.validate_date(t)),
                (
                    "rating",
                    "rating",
                    lambda t: control.safe_round(control.get_clean_number(t), 2),
                ),
                ("votes", "votes", lambda t: control.get_clean_number(t)),
                (
                    None,
                    "rating.trakt",
                    (
                        ("rating", "votes"),
                        lambda r, v: {
                            "rating": control.safe_round(control.get_clean_number(r), 2),
                            "votes": control.get_clean_number(v),
                        },
                    ),
                ),
                ("tagline", "tagline", None),
                (
                    "trailer",
                    "trailer",
                    lambda t: control.youtube_url.format(t.split("?v=")[-1])
                    if t
                    else None,
                ),
                ("type", "mediatype", lambda t: t if "show" not in t else "tvshow"),
                ("available_translations", "available_translations", None),
                ("score", "score", None),
                ("action", "action", None),
                ("added", "added", None),
                ("rank", "rank", None),
                ("listed_at", "listed_at", None),
                (
                    "country",
                    "country_origin",
                    lambda t: t.upper() if t is not None else None,
                ),
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
                ("title", "tvshowtitle", None),
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
                ("number", ("episode", "sortepisode"), None),
                ("season", ("season", "sortseason"), None),
                ("collected_at", "collected", lambda t: 1),
                ("plays", "playcount", None),
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

        self.ListNormalization = [
            ("updated_at", "dateadded", lambda t: g.validate_date(t)),
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
        retries = Retry(
            total=4,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 524],
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def __del__(self):
        self.session.close()

    def _get_headers(self):
        headers = {
            "Content-Type": "application/json",
            "trakt-api-key": self.client_id,
            "trakt-api-version": "2",
            "User-Agent": g.USER_AGENT
        }
        if self.access_token:
            headers["Authorization"] = "Bearer {}".format(self.access_token)
        return headers

    def revoke_auth(self):
        """
        Revokes current authorisation if present
        :return:
        """
        url = "oauth/revoke"
        # post_data = {"token": self.access_token}
        # if self.access_token:
        #     self.post(url, post_data)
        # self._save_settings(
        #     {
        #         "access_token": None,
        #         "refresh_token": None,
        #         "expires_in": 0,
        #         "created_at": 0,
        #     }
        # )
        # g.set_setting(self.username_setting_key, None)
        # from resources.lib.database.trakt_sync import activities

        # activities.TraktSyncDatabase().clear_user_information()
        # xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30022))

    def auth(self):
        return
        # """
        # Performs OAuth with Trakt
        # :return: None
        # """
        # self.username = None
        # response = self.post("oauth/device/code", data={"client_id": self.client_id})
        # if not response.ok:
        #     xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30178))
        #     return
        # try:
        #     response = response.json()
        #     user_code = response["user_code"]
        #     device = response["device_code"]
        #     interval = int(response["interval"])
        #     expiry = int(response["expires_in"])
        #     token_ttl = int(response["expires_in"])
        # except (KeyError, ValueError):
        #     xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30024))
        #     raise

        # control.copy2clip(user_code)
        # self.progress_dialog.create(
        #     g.ADDON_NAME + ": " + g.get_language_string(30023),
        #     control.create_multiline_message(
        #         line1=g.get_language_string(30019).format(
        #             g.color_string(g.color_string("https://trakt.tv/activate"))
        #         ),
        #         line2=g.get_language_string(30020).format(g.color_string(user_code)),
        #         line3=g.get_language_string(30048),
        #     ),
        # )
        # failed = False
        # self.progress_dialog.update(100)
        # while (
        #     not failed
        #     and self.username is None
        #     and not token_ttl <= 0
        #     and not self.progress_dialog.iscanceled()
        # ):
        #     xbmc.sleep(1000)
        #     if token_ttl % interval == 0:
        #         failed = self._auth_poll(device)
        #     progress_percent = int(float((token_ttl * 100) / expiry))
        #     self.progress_dialog.update(progress_percent)
        #     token_ttl -= 1

        # self.progress_dialog.close()

    def _auth_poll(self, device):
        return
        # response = self.post(
        #     "oauth/device/token",
        #     data={
        #         "code": device,
        #         "client_id": self.client_id,
        #         "client_secret": self.client_secret,
        #     },
        # )
        # if response.status_code == 200:
        #     response = response.json()
        #     self._save_settings(response)
        #     username = self.get_username()
        #     self.username = username
        #     self.progress_dialog.close()
        #     xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30300))

        #     # Synchronise Trakt Database with new user
        #     from resources.lib.database.trakt_sync import activities

        #     database = activities.TraktSyncDatabase()
        #     if database.activities["trakt_username"] != username:
        #         database.clear_user_information(
        #             True if database.activities["trakt_username"] else False
        #         )
        #         database.flush_activities(False)
        #         database.set_trakt_user(username)
        #         xbmc.executebuiltin(
        #             'RunPlugin("{}?action=syncTraktActivities")'.format(g.BASE_URL)
        #         )

        #     g.set_setting(self.username_setting_key, username)

        # elif response.status_code == 404 or response.status_code == 410:
        #     self.progress_dialog.close()
        #     xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30024))
        #     return True
        # elif response.status_code == 409:
        #     self.progress_dialog.close()
        #     return True
        # elif response.status_code == 429:
        #     xbmc.sleep(1 * 1000)
        # return False

    def _save_settings(self, response):
        if "access_token" in response:
            g.set_setting("trakt.auth", response["access_token"])
            self.access_token = response["access_token"]
        if "refresh_token" in response:
            g.set_setting("trakt.refresh", response["refresh_token"])
            self.refresh_token = response["refresh_token"]
        if "expires_in" in response and "created_at" in response:
            g.set_setting(
                "trakt.expires", g.UNICODE(response["created_at"] + response["expires_in"])
            )
            self.token_expires = float(response["created_at"] + response["expires_in"])

    def _load_settings(self):
        self.client_id = g.get_setting(
            "trakt.clientid",
            "94babdea045e1b9cfd54b278f7dda912ae559fde990590db9ffd611d4806838c",
        )
        self.client_secret = g.get_setting(
            "trakt.secret",
            "bf02417f27b514cee6a8d135f2ddc261a15eecfb6ed6289c36239826dcdd1842",
        )
        self.access_token = g.get_setting("trakt.auth")
        self.refresh_token = g.get_setting("trakt.refresh")
        self.token_expires = g.get_float_setting("trakt.expires")
        self.default_limit = g.get_int_setting("item.limit")
        self.username = g.get_setting(self.username_setting_key)

    def try_refresh_token(self, force=False):
        """
        Attempts to refresh current Trakt Auth Token
        :param force: Set to True to avoid Global Lock and forces refresh
        :return: None
        """
        if not self.refresh_token:
            return
        if not force and self.token_expires > float(time.time()):
            return

        try:
            with GlobalLock(self.__class__.__name__, True, self.access_token):
                g.log("Trakt Token requires refreshing...")
                response = self.post(
                    "/oauth/token",
                    {
                        "refresh_token": self.refresh_token,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                        "grant_type": "refresh_token",
                    },
                ).json()
                self._save_settings(response)
                g.log("Refreshed Trakt Token")
        except RanOnceAlready:
            self._load_settings()
            return

    @trakt_guard_response
    def get(self, url, **params):
        """
        Performs a GET request to specified endpoint and returns response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: request response
        """
        timeout = params.pop("timeout", 10)
        self._try_add_default_paging(params)
        self._clean_params(params)
        return self.session.get(
            control.urljoin(self.ApiUrl, url),
            params=params,
            headers=self._get_headers(),
            timeout=timeout,
        )

    def _try_add_default_paging(self, params):
        if params.pop("no_paging", False):
            params.pop("limit", "")
            params.pop("page", "")
            return
        if "page" not in params and "limit" in params:
            params.update({"page": 1})
        if "page" in params and "limit" not in params:
            params.update({"limit": self.default_limit})

    @staticmethod
    def _clean_params(params):
        if "hide_watched" in params:
            del params["hide_watched"]
        if "hide_unaired" in params:
            del params["hide_unaired"]

    def get_json(self, url, **params):
        """
        Performs a GET request to specified endpoint, sorts results and returns JSON response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: JSON response
        """
        response = self.get(url=url, **params)
        if response is None:
            return None
        try:
            return self._handle_response(
                self._try_sort(
                    response.headers.get("X-Sort-By"),
                    response.headers.get("X-Sort-How"),
                    response.json(),
                )
            )
        except (ValueError, AttributeError) as e:
            g.log(
                "Failed to receive JSON from Trakt response - response: {} - error - {}".format(
                    response, e
                ),
                "error",
            )
            return None

    @use_cache()
    def get_cached(self, url, **params):
        """
        Performs a GET request to specified endpoint, caches and returns response
        :param url: endpoint to perform request against
        :param params: URL params for request
        :return: request response
        """
        return self.get(url, **params)

    @handle_single_item_or_list
    def _handle_response(self, item):
        item = self._try_detect_type(item)
        if item.get("type") == "castcrew":
            item.pop("type")
            item = self._handle_response(
                [i.get("movie", i.get("show")) for i in item.pop("cast", [])]
            )
            return item
        item = self._flatten_if_single_type(item)
        item = self._try_detect_type(item)
        if not item.get("type") or item.get("type") not in self.MetaObjects:
            return item
        if item["type"] == "mixedepisode":
            single_type = self._handle_single_type(item)
            [
                single_type.update({meta: self._handle_response(item.pop(meta, {}))})
                for meta in self.MetaObjects
                if meta in item
            ]
            single_type.update(item)
            if single_type.get("trakt_id"):
                single_type["episode"]["trakt_show_id"] = single_type.get("trakt_show_id")
                single_type["episode"]["trakt_object"]["info"]["trakt_show_id"] = single_type.get("trakt_show_id")
            return single_type
        return self._create_trakt_object(self._handle_single_type(item))

    @staticmethod
    def _create_trakt_object(item):
        result = {"trakt_object": {"info": item}}
        [
            result.update({key: value})
            for key, value in item.items()
            if key.endswith("_id")
        ]
        return result

    def _handle_single_type(self, item):
        translated = self._handle_translation(item)
        collections = {
            key: self._handle_response(translated[key])
            for key in self.MetaCollections
            if key in translated
        }
        normalized = self._normalize_info(self.MetaObjects[item["type"]], translated)
        normalized.update(collections)
        return normalized

    @staticmethod
    def _get_all_pages(func, url, **params):
        if "progress" in params:
            progress_callback = params.pop("progress")
        else:
            progress_callback = None
        response = func(url, **params)
        yield response
        if "X-Pagination-Page-Count" not in response.headers:
            return
        for i in range(2, int(response.headers["X-Pagination-Page-Count"]) + 1):
            params.update({"page": i})
            if "limit" not in params:
                params.update({"limit": int(response.headers["X-Pagination-Limit"])})
            if progress_callback is not None:
                progress_callback(
                    (i / (int(response.headers["X-Pagination-Page-Count"]) + 1)) * 100
                )
            params.update({"page": i})
            if "limit" not in params:
                params.update({"limit": int(response.headers["X-Pagination-Limit"])})
            yield func(url, **params)

    def get_all_pages_json(self, url, **params):
        """
        Iterates of all available pages from a trakt endpoint and yields the normalised results
        :param url: endpoint to call against
        :param params: any params for the url
        :return: Yields trakt pages
        """
        ignore_cache = params.pop("ignore_cache", False)
        get_method = self.get if ignore_cache else self.get_cached

        for response in self._get_all_pages(get_method, url, **params):
            if not response:
                return
            yield self._handle_response(
                self._try_sort(
                    response.headers.get("X-Sort-By"),
                    response.headers.get("X-Sort-How"),
                    response.json(),
                )
            )

    @use_cache()
    def get_json_cached(self, url, **params):
        """
        Performs a get request to endpoint, caches and returns a json response from a trakt enpoint
        :param url: URL endpoint to perform request to
        :param params: url parameters
        :return: json response from Trakt
        """
        return self.get_json(url, **params)

    @trakt_guard_response
    def post(self, url, data):
        """
        Performs a post request to the specified endpoint and returns response
        :param url: URL endpoint to perform request to
        :param data: POST Data to send to endpoint
        :return: requests response
        """
        return self.session.post(
            control.urljoin(self.ApiUrl, url), json=data, headers=self._get_headers()
        )

    def post_json(self, url, data):
        """
        Performs a post request to the specified endpoint and returns response
        :param url: URL endpoint to perform request to
        :param data: POST Data to send to endpoint
        :return: JSON response from trakt endpoint
        """
        return self.post(url, data).json()

    @trakt_guard_response
    def delete_request(self, url):
        """
        Performs a delete request to the specified endpoint and returns response
        :param url: URL endpoint to perform request to
        :return: requests response
        """
        return self.session.delete(
            control.urljoin(self.ApiUrl, url), headers=self._get_headers()
        )

    @staticmethod
    def _get_display_name(content_type):
        if content_type == "movie":
            return g.get_language_string(30290)
        else:
            return g.get_language_string(30312)

    def get_username(self):
        """
        Fetch current signed in users username
        :return: string username
        """
        user_details = self.get_json("users/me")
        return user_details["username"]

    def _try_sort(self, sort_by, sort_how, items):
        if not isinstance(items, (set, list)):
            return items

        if sort_by is None or sort_how is None:
            return items

        supported_sorts = [
            "added",
            "rank",
            "title",
            "released",
            "runtime",
            "popularity",
            "votes",
            "random",
            "runtime",
            "percentage",
        ]

        if sort_by not in supported_sorts:
            return items

        if sort_by == "added":
            items = sorted(items, key=lambda x: x.get("listed_at"))
        elif sort_by == "rank":
            items = sorted(items, key=lambda x: x.get("rank"), reverse=True)
        elif sort_by == "title":
            items = sorted(items, key=self._title_sorter)
        elif sort_by == "released":
            items = sorted(items, key=self._released_sorter)
        elif sort_by == "runtime":
            items = sorted(items, key=lambda x: x[x["type"]].get("runtime"))
        elif sort_by == "popularity":
            items = sorted(
                items,
                key=lambda x: float(
                    x[x["type"]].get("rating", 0) * int(x[x["type"]].get("votes", 0))
                ),
            )
        elif sort_by == "votes":
            items = sorted(items, key=lambda x: x[x["type"]].get("votes"))
        elif sort_by == "percentage":
            items = sorted(items, key=lambda x: x[x["type"]].get("rating"))
        elif sort_by == "random":
            import random

            random.shuffle(items)

        if sort_how == "desc":
            items.reverse()

        return items

    @staticmethod
    def _title_sorter(item):
        return control.SORT_TOKEN_REGEX.sub("", item[item["type"]].get("title", "").lower())

    @staticmethod
    def _released_sorter(item):
        released = item[item["type"]].get("released")
        if not released:
            released = item[item["type"]].get("first_aired")
        if not released:
            released = ""
        return released

    @handle_single_item_or_list
    def _flatten_if_single_type(self, item):
        media_type = item.get("type")
        if media_type and media_type in item:
            key = media_type
        else:
            keys = [meta for meta in self.MetaObjects if meta in item]
            if len(keys) == 1:
                key = keys[0]
            else:
                return item
        if isinstance(item[key], dict):
            item.update(item.pop(key))
            item.update({"type": key})
        return item

    @staticmethod
    @handle_single_item_or_list
    def _try_detect_type(item):
        item_types = [
            ("list", lambda x: "item_count" in x and "sort_by" in x),
            ("mixedepisode", lambda x: "show" in x and "episode" in x),
            ("show", lambda x: "show" in x),
            ("movie", lambda x: "movie" in x),
            (
                "movie",
                lambda x: "title" in x and "year" in x and "network" not in x,
            ),
            ("show", lambda x: "title" in x and "year" in x and "network" in x),
            (
                "episode",
                lambda x: "number" in x
                and (
                    "season" in x
                    or ("last_watched_at" in x and "plays" in x)
                    or ("collected_at" in x)
                ),
            ),
            ("season", lambda x: "number" in x),
            ("castcrew", lambda x: "cast" in x and "crew" in x),
            ("sync", lambda x: "all" in x),
            ("genre", lambda x: "name" in x and "slug" in x),
            ("network", lambda x: "name")
        ]
        for item_type in item_types:
            if item_type[1](item):
                item.update({"type": item_type[0]})
                break
        if "type" not in item:
            g.log("Error detecting trakt item type for: {}".format(item), "error")
        return item

    def get_show_aliases(self, trakt_show_id):
        """
        Fetches aliases for a show
        :param trakt_show_id: Trakt ID of show item
        :return: list of aliases
        """
        return sorted(
            {
                i["title"]
                for i in self.get_json_cached("/shows/{}/aliases".format(trakt_show_id))
                if i["country"] in [self.country, 'us']
            }
        )

    def get_show_translation(self, trakt_id):
        return self._normalize_info(
            self.TranslationNormalization,
            self.get_json_cached("shows/{}/translations/{}".format(trakt_id, self.language))[
                0
            ],
        )

    def get_movie_translation(self, trakt_id):
        return self._normalize_info(
            self.TranslationNormalization,
            self.get_json_cached("movies/{}/translations/{}".format(trakt_id, self.language))[
                0
            ],
        )

    @handle_single_item_or_list
    def _handle_translation(self, item):
        if "language" in item and item.get("language") == self.language:
            return item

        if "translations" in item:
            for translation in item.get("translations", []):
                self._apply_translation(item, translation)
        return item

    def _apply_translation(self, item, translation):
        if not item or not translation:
            return
        if translation.get("language") == self.language:
            [
                item.update({k: v})
                for k, v in list(translation.items())
                if v
                and str(item.get("number", 0)) not in v
                and item.get("title")
                and str(item.get("number", 0)) not in item.get("title")
            ]

class TRAKTAPI(object):
    def __init__(self):
        self.ClientID = "94babdea045e1b9cfd54b278f7dda912ae559fde990590db9ffd611d4806838c"
        self.baseUrl = 'https://api.trakt.tv/'
        self.art = {}
        self.request_response = None
        self.headers = {'trakt-api-version': '2',
                        'trakt-api-key': self.ClientID,
                        'content-type': 'application/json'}

    def _json_request(self, url):
        url = self.baseUrl + url
        response = requests.get(url, headers=self.headers)
        response = response.json()
        return response

    def _parse_trakt_seasons(self, res, show_id, eps_watched):
        parsed = database.get_show(show_id)
        parsed = ast.literal_eval(res['kodi_meta'])

        try:
            if int(eps_watched) >= res['number']:
                parsed['info']['playcount'] = 1
        except:
            pass

        return parsed

    def _parse_search_trakt(self, res, show_id):
        url = '%s/%s' %(show_id, res['show']['ids'])
        name = res['show']['title']
        image = TMDBAPI().showPoster(res['show']['ids'])
        if image:
            image = image['poster']
        info = {}
        info['plot'] = res['show']['overview']
        info['mediatype'] = 'tvshow'
        parsed = g.allocate_item(name, "season_correction_database/" + str(url), True, image, info)
        return parsed

    def _parse_trakt_view(self, res, show_id, show_meta):
        url = '%s/%d' % (show_id, res['number']) 
        name = res['title']
        image = TMDBAPI().showSeasonToListItem(res['number'], show_meta)
        if image:
            image = image['poster']
        info = {}
        info['plot'] = res['overview']
        info['mediatype'] = 'season'
        parsed = g.allocate_item(name, "animes_trakt/" + str(url), True, image, info)
        return parsed

    def _parse_trakt_episode_view(self, res, show_id, show_meta, season, poster, fanart, eps_watched, update_time):
        url = "%s/%s/" % (show_id, res['number'])
        name = 'Ep. %d (%s)' % (res['number'], res.get('title', ''))
        try:
            image = TMDBAPI().episodeIDToListItem(season, str(res['number']), show_meta)['thumb']
        except:
            image = 'DefaultVideo.png'
        info = {}
        info['plot'] = res['overview']
        info['title'] = res.get('title', '')
        info['season'] = int(season)
        info['episode'] = res['number']
        try:
            if int(eps_watched) >= res['number']:
                info['playcount'] = 1
        except:
            pass
        try:
            info['aired'] = res['first_aired'][:10]
        except:
            pass

        import pickle
        info['tvshowtitle'] = pickle.loads(database.get_show(show_id)['info'])['title']
        info['mediatype'] = 'episode'
        parsed = g.allocate_item(name, "play/" + str(url), False, image, info, fanart, poster, True)
        database._update_episode(show_id, season, res['number'], res['number_abs'], update_time, parsed)
        return parsed

    def _process_trakt_episodes(self, anilist_id, season, episodes, eps_watched):
        mapfunc = partial(self._parse_trakt_seasons, show_id=anilist_id, eps_watched=eps_watched)
        all_results = list(map(mapfunc, episodes))

        return all_results

    def _process_season_view(self, anilist_id, meta_ids, kodi_meta, url):
        result = self._json_request(url)
        mapfunc = partial(self._parse_trakt_view, show_id=anilist_id, show_meta=meta_ids)
        all_results = list(map(mapfunc, result))
        return all_results, 'seasons'

    def _process_direct_season_view(self, anilist_id, meta_ids, kodi_meta, url):
        result = self._json_request(url)

        try:
            season_year = str(kodi_meta['year']) + '-'
            seasons = [k for k in result if k['number'] != 0]
            season = next((item for item in seasons if season_year in item["first_aired"]), None)
            database._update_season(anilist_id, season['number'])
            all_results = self.get_trakt_episodes(anilist_id, season['number']), 'episodes'
        except:
            mapfunc = partial(self._parse_trakt_view, show_id=anilist_id, show_meta=meta_ids)
            all_results = list(map(mapfunc, result)), 'seasons'

        return all_results
    
    def _process_trakt_episode_view(self, anilist_id, show_meta, season, poster, fanart, eps_watched, url, data, base_plugin_url):
        from datetime import datetime, timedelta
        update_time = (datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d')
        result = self._json_request(url)
        mapfunc = partial(self._parse_trakt_episode_view, show_id=anilist_id, show_meta=show_meta, season=season, poster=poster, fanart=fanart, eps_watched=eps_watched, update_time=update_time)
        all_results = list(map(mapfunc, result))
        return all_results

    def get_tmdb_to_trakt(self, tmdb_id):
        url = 'search/tmdb/%s?type=show' % tmdb_id
        result = self._json_request(url)

        if not result:
            return

        return result[0]['show']['ids']

    def get_trakt_id(self, item_information):
        # Check for english or romaji title. Search for english if romaji.
        title_language = g.get_setting("titlelanguage").lower()
        if 'english' in title_language:
            title = item_information['info']['title']
        else:
            split_title = item_information['info']['aliases'].split(")")
            title = split_title[1]
            if title == '':
                title = item_information['info']['title']
        title = re.sub('[^A-Za-z0-9]', ' ', title)
        url = 'search/show?query=%s&genres=anime&extended=full' % title
        result = self._json_request(url)
        if not result:
            title = title.replace('?', '')
            if 'season' in title.lower():
                part_search = re.search('(?:part\s?\d)', title, re.I)
                if part_search:
                    title = title.replace(part_search[0], '')
                first_test = re.search('[^\s]+\sseason(?=\s[^\d])', title, re.I)
                second_test = re.search('(\d{1,2}(?:st|nd|rd|th)(?:\s|_|&|\+|,|.|-)?(?:season))', title, re.I)
                third_test = re.search('(?:season\s?\d)', title, re.I)
                if first_test:
                    title = title.replace(first_test[0], '')
                elif second_test:
                    title = title.replace(second_test[0], '')
                elif third_test:
                    title = title.replace(third_test[0], '')
            else:
                title = re.findall('\d*\D+', title)[0]
            url = 'search/show?query=%s&genres=anime&extended=full' % title
            result = self._json_request(url)

        if not result:
            return

        return result[0]['show']['ids']

    def get_trakt_id_backup(self, item_information):
        title = item_information['info']['title']
        url = 'search/show?query=%s&genres=anime&extended=full' % title
        result = self._json_request(url)

        if not result:
            title = title.replace('?', '')
            title = re.findall('\d*\D+', title)[0]
            url = 'search/show?query=%s&genres=anime&extended=full' % title
            result = self._json_request(url)

        if not result:
            return

        if len(result) == 1:
            show = result[0]['show']
        else:
            aired_year = int(item_information['air_date'].split('-')[0])
            show = next((i['show'] for i in result if i['show'].get('year') == aired_year), None)
            if not show:
                episode_count = item_information['episode_count']
                show = next((i['show'] for i in result if i['show'].get('aired_episodes') == episode_count), result[0]['show'])

        return show['ids']

    def search_trakt_shows(self, anilist_id):
        name = ast.literal_eval(database.get_show(anilist_id)['kodi_meta'])['name']
        url = 'search/show?query=%s&genres=anime&extended=full' % name
        result = self._json_request(url)

        if not result:
            name = re.findall('\d*\D+', name)[0]
            name = name.replace('?', '')
            url = 'search/show?query=%s&genres=anime&extended=full' % name
            result = self._json_request(url)

        if not result:
            return []

        mapfunc = partial(self._parse_search_trakt, show_id=anilist_id)
        all_results = list(map(mapfunc, result))
        return all_results

    def _add_fanart(self, anilist_id, meta_ids, kodi_meta):
        try:
            if not kodi_meta.get('fanart'):
                kodi_meta['fanart'] = TMDBAPI().showFanart(meta_ids)['fanart']
                database.update_kodi_meta(anilist_id, kodi_meta)
        except:
            pass        

    def get_trakt_seasons(self, anilist_id, meta_ids, kodi_meta, db_correction):
        fanart = self._add_fanart(anilist_id, meta_ids, kodi_meta)

        url = 'shows/%d/seasons?extended=full' % meta_ids['trakt_id']

        if db_correction:
            target = self._process_season_view
        else:
            target = self._process_direct_season_view

        return target(anilist_id, meta_ids, kodi_meta, url)

    def get_anime(self, anilist_id, db_correction):
        seasons = database.get_season_list(anilist_id)

        if seasons:                
            return self.get_trakt_episodes(anilist_id, seasons['season']), 'episodes'

        show = database.get_show(anilist_id)
        import pickle
        kodi_meta = pickle.loads(show['info'])

        if show['episode_count'] is None or int(show['episode_count']) > 30:
            return

        meta_ids = control.get_item_information(anilist_id)

        return self.get_trakt_seasons(anilist_id, meta_ids, kodi_meta, db_correction)

    def get_trakt_episodes(self, show_id, season):
        show_meta = database.get_show(show_id)
        import pickle
        kodi_meta = pickle.loads(show_meta['info'])
        fanart = kodi_meta.get('fanart')
        poster = kodi_meta.get('poster')
        eps_watched = show_meta.get('watched_episodes')
        #episodes = database.get_episode_list(int(show_id))

        #if episodes:
        #    return self._process_trakt_episodes(show_id, season, episodes, eps_watched)

        url = "shows/%d/seasons/%s?extended=full" % (show_meta['trakt_id'], str(season))
        data = ''
        return self._process_trakt_episode_view(show_id, show_meta, season, poster, fanart, eps_watched, url, data, "animes_page/%s/%%d" % show_id)

    def get_trakt_all_seasons(self, show_id):
        url = 'shows/%d/seasons/?extended=full' % show_id
        result = self._json_request(url)

        if not result:
            return

        return result

    def get_trakt_show(self, show_id, mediatype):
        if mediatype == 'movie':
            url = 'movies/%d/' % show_id
        else:
            url = 'shows/%d/' % show_id
        result = self._json_request(url)

        if not result:
            return

        return result
