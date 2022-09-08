# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import collections
import datetime
import json
import threading
import time

import xbmcgui

from resources.lib.ui import control
from resources.lib.ui import database
from resources.lib.modules.thread_pool import ThreadPool
from resources.lib.database import Database
from resources.lib.indexers.anilist import AnilistAPI, AnilistAPI_animelist
from resources.lib.indexers.trakt import TraktAPI2
from resources.lib.ui.exceptions import (
    UnsupportedProviderType,
    InvalidMediaTypeException,
)
from resources.lib.ui.globals import g
from resources.lib.ui.global_lock import GlobalLock
from resources.lib.modules.metadataHandler import MetadataHandler
from resources.lib.modules.sync_lock import SyncLock

migrate_db_lock = threading.Lock()

schema = {
    "shows_meta": {
        "columns": collections.OrderedDict(
            [
                ("id", ["INTEGER", "NOT NULL"]),
                ("type", ["TEXT", "NOT NULL"]),
                ("meta_hash", ["TEXT", "NOT NULL"]),
                ("value", ["PICKLE", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["UNIQUE(id, type)"],
        "default_seed": [],
    },
    "seasons_meta": {
        "columns": collections.OrderedDict(
            [
                ("id", ["INTEGER", "NOT NULL"]),
                ("type", ["TEXT", "NOT NULL"]),
                ("meta_hash", ["TEXT", "NOT NULL"]),
                ("value", ["PICKLE", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["UNIQUE(id, type)"],
        "default_seed": [],
    },
    "episodes_meta": {
        "columns": collections.OrderedDict(
            [
                ("id", ["INTEGER", "NOT NULL"]),
                ("type", ["TEXT", "NOT NULL"]),
                ("meta_hash", ["TEXT", "NOT NULL"]),
                ("value", ["PICKLE", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["UNIQUE(id, type)"],
        "default_seed": [],
    },
    "movies_meta": {
        "columns": collections.OrderedDict(
            [
                ("id", ["INTEGER", "NOT NULL"]),
                ("type", ["TEXT", "NOT NULL"]),
                ("meta_hash", ["TEXT", "NOT NULL"]),
                ("value", ["PICKLE", "NOT NULL"]),
            ]
        ),
        "table_constraints": ["UNIQUE(id, type)"],
        "default_seed": [],
    },
    "shows": {
        "columns": collections.OrderedDict(
            [
                ("anilist_id", ["INTEGER", "PRIMARY KEY", "NOT NULL"]),
                ("kitsu_id", ["INTEGER", "NULL"]),
                ("mal_id", ["INTEGER", "NULL"]),
                ("simkl_id", ["INTEGER", "NULL"]),
                ("trakt_id", ["INTEGER", "NULL"]),
                ("tvdb_id", ["INTEGER", "NULL"]),
                ("tmdb_id", ["INTEGER", "NULL"]),
                ("imdb_id", ["INTEGER", "NULL"]),
                ("info", ["PICKLE", "NULL"]),
                ("cast", ["PICKLE", "NULL"]),
                ("art", ["PICKLE", "NULL"]),
                ("meta_hash", ["TEXT", "NULL"]),
                ("episode_indexer", ["TEXT", "NULL"]),
                ("episode_count", ["INTEGER", "NULL", "DEFAULT 0"]),
                ("episode_offset", ["INTEGER", "NULL", "DEFAULT 0"]),
                ("unwatched_episodes", ["INTEGER", "NULL", "DEFAULT 0"]),
                ("watched_episodes", ["INTEGER", "NULL", "DEFAULT 0"]),
                ("last_updated", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("args", ["TEXT", "NULL"]),
                ("air_date", ["TEXT"]),
                ("is_airing", ["BOOLEAN"]),
                ("needs_update", ["BOOLEAN", "NOT NULL", "DEFAULT 1"])
            ]
        ),
        "table_constraints": [],
        "default_seed": [],
    },
    "seasons": {
        "columns": collections.OrderedDict(
            [
                ("trakt_id", ["INTEGER", "PRIMARY KEY", "NOT NULL"]),
                ("trakt_show_id", ["INTEGER", "NOT NULL"]),
                ("anilist_id", ["INTEGER", "NOT NULL"]),
                ("tvdb_id", ["INTEGER", "NULL"]),
                ("tmdb_id", ["INTEGER", "NULL"]),
                ("season", ["INTEGER", "NOT NULL"]),
                ("info", ["PICKLE", "NULL"]),
                ("cast", ["PICKLE", "NULL"]),
                ("art", ["PICKLE", "NULL"]),
                ("meta_hash", ["TEXT", "NULL"]),
                ("episode_count", ["INTEGER", "NULL", "DEFAULT 0"]),
                ("unwatched_episodes", ["INTEGER", "NULL", "DEFAULT 0"]),
                ("watched_episodes", ["INTEGER", "NULL", "DEFAULT 0"]),
                ("last_updated", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("args", ["TEXT", "NOT NULL"]),
                ("air_date", ["TEXT"]),
                ("is_airing", ["BOOLEAN"]),
                ("needs_update", ["BOOLEAN", "NOT NULL", "DEFAULT 1"])
            ]
        ),
        "table_constraints": [
            "UNIQUE(anilist_id, season)",
            "FOREIGN KEY(anilist_id) REFERENCES shows(anilist_id) DEFERRABLE INITIALLY DEFERRED"
        ],
        "default_seed": [],
    },
    "episodes": {
        "columns": collections.OrderedDict(
            [
                ("trakt_id", ["INTEGER", "PRIMARY KEY", "NOT NULL"]),
                ("trakt_show_id", ["INTEGER", "NOT NULL"]),
                ("trakt_season_id", ["INTEGER", "NULL"]),
                ("anilist_id", ["INTEGER", "NOT NULL"]),
                ("season", ["INTEGER", "NOT NULL"]),
                ("tvdb_id", ["INTEGER", "NULL"]),
                ("tmdb_id", ["INTEGER", "NULL"]),
                ("imdb_id", ["INTEGER", "NULL"]),
                ("info", ["PICKLE", "NULL"]),
                ("cast", ["PICKLE", "NULL"]),
                ("art", ["PICKLE", "NULL"]),
                ("meta_hash", ["TEXT", "NULL"]),
                ("last_updated", ["TEXT", "NOT NULL", "DEFAULT '1970-01-01T00:00:00'"]),
                ("collected", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("watched", ["INTEGER", "NOT NULL", "DEFAULT 0"]),
                ("number", ["INTEGER", "NOT NULL"]),
                ("args", ["TEXT", "NOT NULL"]),
                ("air_date", ["TEXT"]),
                ("last_watched_at", ["TEXT"]),
                ("collected_at", ["TEXT"]),
                ("needs_update", ["BOOLEAN", "NOT NULL", "DEFAULT 1"])
            ]
        ),
        "table_constraints": [
            "UNIQUE(trakt_id, season, number)",
            "FOREIGN KEY(trakt_season_id) REFERENCES seasons(trakt_id) DEFERRABLE INITIALLY DEFERRED",
            "FOREIGN KEY(anilist_id) REFERENCES shows(anilist_id) DEFERRABLE INITIALLY DEFERRED"
        ],
        "default_seed": [],
    },
}


class AnilistSyncDatabase(Database):
    def __init__(self,):
        super(AnilistSyncDatabase, self).__init__(g.ANILIST_SYNC_DB_PATH, schema)
        self.metadataHandler = MetadataHandler()
        self.trakt_api = AnilistAPI()
        self.anilist_animelist = AnilistAPI_animelist()
        self.trakt_api2 = TraktAPI2()

    #     self.activities = {}
    #     self.item_list = []
    #     self.base_date = "1970-01-01T00:00:00"
        self.task_queue = ThreadPool()
        self.mill_task_queue = ThreadPool()
        self.parent_task_queue = ThreadPool()
    #     self.refresh_activities()

    #     # If you make changes to the required meta in any indexer that is cached in this database
    #     # You will need to update the below version number to match the new addon version
    #     # This will ensure that the metadata required for operations is available

    #     self.last_meta_update = "2.0.14"
    #     if self.activities is None:
    #         self.clear_all_meta(False)
    #         self.set_base_activities()

    #     if self.activities is not None:
    #         self._check_database_version()

    #     self.notification_prefix = "{}: Trakt".format(g.ADDON_NAME)
    #     self.hide_unaired = g.get_bool_setting("general.hideUnAired")
    #     self.hide_specials = g.get_bool_setting("general.hideSpecials")
    #     self.hide_watched = g.get_bool_setting("general.hideWatched")
    #     self.date_delay = g.get_bool_setting("general.datedelay")
    #     self.page_limit = g.get_int_setting("item.limit")

    # def clear_specific_item_meta(self, trakt_id, media_type):
    #     if media_type == "tvshow":
    #         media_type = "shows"
    #     elif media_type == "show":
    #         media_type = "shows"
    #     elif media_type == "movie":
    #         media_type = "movies"
    #     elif media_type == "episode":
    #         media_type = "episodes"
    #     elif media_type == "season":
    #         media_type = "seasons"

    #     if media_type not in ["shows", "movies", "seasons", "episodes"]:
    #         raise InvalidMediaTypeException(media_type)

    #     self.execute_sql(
    #         "DELETE from {}_meta where id=?".format(media_type), (trakt_id,)
    #     )
    #     self.execute_sql(
    #         "UPDATE {} SET info=null, art=null, cast=null, meta_hash=null where trakt_id=?"
    #         "".format(media_type),
    #         (trakt_id,),
    #     )

    # def _update_last_activities_call(self):
    #     self.execute_sql("UPDATE activities SET last_activities_call=? WHERE sync_id=1", (int(time.time()),))
    #     self.refresh_activities()

    # def _insert_last_activities_column(self):
    #     self.execute_sql("ALTER TABLE activities ADD last_activities_call INTEGER NOT NULL DEFAULT 1")

    @staticmethod
    def _get_datetime_now():
        return datetime.datetime.utcnow().strftime(g.DATE_TIME_FORMAT)

    # def refresh_activities(self):
    #     self.activities = self.fetchone(
    #         "SELECT * FROM activities WHERE sync_id=1"
    #     )

    # def set_base_activities(self):
    #     self.execute_sql(
    #         "INSERT OR REPLACE INTO activities(sync_id, seren_version, trakt_username) VALUES(1, ?, ?)",
    #         (self.last_meta_update, g.get_setting("trakt.username")),
    #     )
    #     self.activities = self.fetchone(
    #         "SELECT * FROM activities WHERE sync_id=1"
    #     )

    # def _check_database_version(self):
    #     # If we are updating from a database prior to database versioning, we must clear the meta data
    #     # Migrate from older versions before trakt username tracking
    #     if tools.compare_version_numbers(
    #         self.activities["seren_version"], self.last_meta_update
    #     ):
    #         g.log("Rebuilding Trakt Sync Database Version")
    #         xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30363))
    #         try:
    #             self.re_build_database(True)
    #         except:
    #             self.rebuild_database()

    # def flush_activities(self, clear_meta=False):
    #     if clear_meta:
    #         self.clear_all_meta()
    #     self.execute_sql("DELETE FROM activities")
    #     self.set_base_activities()

    # def clear_user_information(self, notify=True):
    #     username = self.activities["trakt_username"]
    #     self.execute_sql(
    #         [
    #             "UPDATE episodes SET watched=?",
    #             "UPDATE episodes SET collected=?",
    #             "UPDATE movies SET watched=?",
    #             "UPDATE movies SET collected=?",
    #             "UPDATE shows SET unwatched_episodes=?",
    #             "UPDATE shows SET watched_episodes=?",
    #             "UPDATE seasons SET unwatched_episodes=?",
    #             "UPDATE seasons SET watched_episodes=?",
    #         ],
    #         (0,),
    #     )
    #     self.execute_sql(
    #         [
    #             "UPDATE episodes SET last_watched_at=?",
    #             "UPDATE movies SET last_watched_at=?",
    #         ],
    #         (None,),
    #     )
    #     self.execute_sql(
    #         ["DELETE from bookmarks WHERE 1=1", "DELETE from hidden WHERE 1=1",]
    #     )
    #     self.execute_sql("DELETE from lists WHERE username=?", (username,))
    #     self.set_trakt_user("")
    #     self.set_base_activities()
    #     if notify:
    #         g.notification(
    #             self.notification_prefix, g.get_language_string(30297), time=5000
    #         )

    # def set_trakt_user(self, trakt_username):
    #     g.log("Setting Trakt Username: {}".format(trakt_username))
    #     self.execute_sql("UPDATE activities SET trakt_username=?", (trakt_username,))

    # def clear_all_meta(self, notify=True):
    #     if notify:
    #         confirm = xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30201))
    #         if confirm == 0:
    #             return

    #     self.execute_sql(
    #         [
    #             "UPDATE shows SET info=?, cast=?, art=?, meta_hash=?",
    #             "UPDATE seasons SET info=?, cast=?, art=?, meta_hash=?",
    #             "UPDATE episodes SET info=?, cast=?, art=?, meta_hash=?",
    #             "UPDATE movies SET info=?, cast=?, art=?, meta_hash=?",
    #         ],
    #         (None, None, None, None),
    #     )

    #     self.execute_sql(
    #         [
    #             "DELETE FROM movies_meta",
    #             "DELETE FROM shows_meta",
    #             "DELETE FROM seasons_meta",
    #             "DELETE FROM episodes_meta",
    #         ]
    #     )
    #     if notify:
    #         g.notification(
    #             self.notification_prefix, g.get_language_string(30298), time=5000
    #         )

    def re_build_database(self, silent=False):
        if not silent:
            confirm = xbmcgui.Dialog().yesno(g.ADDON_NAME, "Rebuild")
            if confirm == 0:
                return

        self.rebuild_database()
    #     self.set_base_activities()
    #     self.refresh_activities()

    #     from resources.lib.database.trakt_sync import activities

    #     sync_errors = activities.TraktSyncDatabase().sync_activities(silent)

    #     if sync_errors:
    #         g.notification(
    #             self.notification_prefix, g.get_language_string(30364), time=5000
    #         )
    #     elif sync_errors is None:
    #         self.refresh_activities()
    #     else:
    #         g.notification(
    #             self.notification_prefix, g.get_language_string(30299), time=5000
    #         )

    def filter_items_that_needs_updating(self, requested, media_type):
        if requested is None or len(requested) == 0:
            return []
        query = """WITH requested(anilist_id, meta_hash) AS (VALUES {}) select r.anilist_id as anilist_id from requested as 
        r left join {} as db on r.anilist_id == db.anilist_id where db.anilist_id IS NULL or (db.info is null or db.art is 
        null or r.meta_hash != db.meta_hash)""".format(
            ",".join(
                [
                    "({}, '{}')".format(
                        i.get("anilist_id"), self.metadataHandler.meta_hash
                    )
                    for i in requested
                ]
            ),
            media_type,
        )
        result = set(r["anilist_id"] for r in self.fetchall(query))
        return [r for r in requested if r.get("anilist_id") in result]

    def save_to_meta_table(self, items, meta_type, provider_type, id_column):
        if items is None:
            return
        sql_statement = "replace into {}_meta (id ,type, meta_hash, value) VALUES (?, ?, ?, ?)".format(
            meta_type
        )
        obj = None
        meta_hash = None
        if provider_type == "anilist":
            obj = MetadataHandler.anilist_object
            meta_hash = self.trakt_api.meta_hash
        elif provider_type == "trakt":
            obj = MetadataHandler.trakt_object
            meta_hash = self.trakt_api2.meta_hash
        elif provider_type == "tmdb":
            obj = MetadataHandler.tmdb_object
            meta_hash = '' # self.metadataHandler.tmdb_api.meta_hash
        elif provider_type == "tvdb":
            obj = MetadataHandler.tvdb_object
            meta_hash = '' # self.metadataHandler.tvdb_api.meta_hash
        elif provider_type == "fanart":
            obj = MetadataHandler.fanart_object
            meta_hash = '' # self.metadataHandler.fanarttv_api.meta_hash
        elif provider_type == "omdb":
            obj = MetadataHandler.omdb_object
            meta_hash = '' # self.metadataHandler.omdb_api.meta_hash

        if obj is None or meta_hash is None:
            raise UnsupportedProviderType(provider_type)

        with GlobalLock("save_to_meta_table", check_sum=meta_type):
            self.execute_sql(
                sql_statement,
                (
                    (i.get(id_column), provider_type, meta_hash, self.clean_meta(obj(i)))
                    for i in items
                    if i
                       and obj(i)
                       and i.get(id_column)
                       and MetadataHandler.full_meta_up_to_par(meta_type, obj(i))
                ),
            )

        for i in items:
            if i and obj(i):
                if obj(i).get("seasons"):
                    self.save_to_meta_table(
                        i.get("seasons"), "season", provider_type, id_column
                    )
                if obj(i).get("episodes"):
                    self.save_to_meta_table(
                        i.get("episodes"), "episode", provider_type, id_column
                    )

    @staticmethod
    def clean_meta(item):
        if not item:
            return None

        result = {
            "info": {
                key: value.replace('<i>', '[I]').replace('</i>', '[/I]').replace('<br>', '[CR]') if isinstance(value, str) else value
                for key, value in item.get("info", {}).items()
                if key != "seasons" and key != "episodes"
            },
            "art": item.get("art"),
            "cast": item.get("cast"),
        }
        if not result.get("info") and not result.get("art") and not result.get("cast"):
            g.log(
                "Bad Item meta discovered when cleaning - item: {}".format(item),
                "error",
            )
            return None
        else:
            return result

    @staticmethod
    def _set_needs_update(items, updated):
        updated_dict = {tid.get('anilist_id') for tid in updated}
        for i in items:
            i.update({"needs_update": "true" if i.get("anilist_id") in updated_dict else "false"})

    # def insert_trakt_movies(self, movies):
    #     g.log("Inserting Movies into sync database: {}".format(len(movies)))
    #     get = MetadataHandler.get_trakt_info
    #     self.execute_sql(
    #         self.upsert_movie_query,
    #         (
    #             (
    #                 i.get("trakt_id"),
    #                 None,
    #                 None,
    #                 None,
    #                 get(i, "collected"),
    #                 get(i, "watched"),
    #                 tools.validate_date(get(i, "aired")),
    #                 tools.validate_date(get(i, "dateadded")),
    #                 get(i, "tmdb_id"),
    #                 get(i, "imdb_id"),
    #                 None,
    #                 self._create_args(i),
    #                 tools.validate_date(get(i, "collected_at")),
    #                 tools.validate_date(get(i, "last_watched_at")),
    #                 i.get("trakt_id"),
    #             )
    #             for i in movies
    #         ),
    #     )
    #     self.save_to_meta_table(movies, "movies", "trakt", "trakt_id")

    def insert_anilist_shows(self, shows):
        if not shows:
            return

        to_insert = self._filter_trakt_items_that_needs_updating(shows, "shows")

        if not to_insert:
            return

        g.log("Inserting Shows into sync database: {}".format(len(shows)))
        get = MetadataHandler.get_anilist_info
        self.execute_sql(
            self.upsert_show_query,
            (
                (
                    i.get("anilist_id"),
                    None,
                    i.get("mal_id"),
                    None,
                    None,
                    None,
                    None,
                    None,
                    MetadataHandler.anilist_info(i),
                    MetadataHandler.anilist_art(i),
                    None,
                    control.validate_date(get(i, "aired")),
                    control.validate_date(get(i, "dateadded")),
                    self.trakt_api.meta_hash,
                    None,
                    get(i, "episode_count"),
                    None,
                    self._create_args(i),
                    get(i, "is_airing"),
                    i.get("anilist_id"),
                )
                for i in to_insert
            ),
        )
        self.save_to_meta_table(to_insert, "shows", "anilist", "anilist_id")
        self._set_needs_update(shows, to_insert)

    def insert_trakt_episodes(self, episodes):
        if not episodes:
            return

        to_insert = self._filter_trakt2_items_that_needs_updating(episodes, "episodes")

        if not to_insert:
            return
        g.log("Inserting episodes into sync database: {}".format(len(to_insert)))
        get = MetadataHandler.get_trakt_info

        missing_season_ids = [i for i in to_insert if not i.get("trakt_season_id")]
        if len(missing_season_ids) > 0:
            predicate = " OR ".join(
                ["(trakt_show_id={} AND season={})".format(get(i, "trakt_show_id"), get(i, "season")) for i in
                 missing_season_ids])
            season_ids = self.fetchall("select trakt_show_id, trakt_id, season from seasons where {}".format(predicate))
            season_ids = {"{}-{}".format(i["trakt_show_id"], i["season"]): i["trakt_id"] for i in season_ids}
            for i in to_insert:
                i["trakt_season_id"] = season_ids.get("{}-{}".format(get(i, "trakt_show_id"), get(i, "season")))
        anilist_ids = {}
        for i in to_insert:
            anilist_ids[i.get("anilist_id")] = i.get("anilist_id")
        self.execute_sql(
            self.upsert_episode_query,
            (
                (
                    i.get("anilist_id"),
                    i.get("trakt_id"),
                    i.get("trakt_show_id"),
                    i.get("trakt_season_id"),
                    get(i, "playcount"),
                    get(i, "collected"),
                    g.validate_date(get(i, "aired")),
                    g.validate_date(get(i, "dateadded")),
                    get(i, "season"),
                    get(i, "episode"),
                    get(i, "tmdb_id"),
                    get(i, "tvdb_id"),
                    get(i, "imdb_id"),
                    None,
                    None,
                    None,
                    self._create_args(i['trakt_object']),
                    g.validate_date(get(i, "last_watched_at")),
                    g.validate_date(get(i, "collected_at")),
                    self.trakt_api.meta_hash,
                    i.get("trakt_id"),
                )
                for i in to_insert
            ),
        )
        episodes_watched = {}
        for x in anilist_ids:
            episodes_watched[x] = database.get_show(x)["watched_episodes"]
        for x in episodes_watched:
            if episodes_watched[x] > 0:
                database.mark_episodes_watched(x, 1, 1, episodes_watched[x])
        self.save_to_meta_table(to_insert, "episodes", "trakt", "trakt_id")
        self._set_needs_update(episodes, to_insert)

    def insert_trakt_seasons(self, seasons):
        if not seasons:
            return

        to_insert = self._filter_trakt2_items_that_needs_updating(seasons, "seasons")

        if not to_insert:
            return

        g.log("Inserting seasons into sync database: {}".format(len(to_insert)))
        get = MetadataHandler.get_trakt_info
        self.execute_sql(
            self.upsert_season_query,
            (
                (
                    i.get("anilist_id"),
                    i.get("trakt_show_id"),
                    i.get("trakt_id"),
                    None,
                    None,
                    None,
                    control.validate_date(get(i, "aired")),
                    control.validate_date(get(i, "dateadded")),
                    get(i, "tmdb_id"),
                    get(i, "tvdb_id"),
                    self.trakt_api.meta_hash,
                    None,
                    get(i, "season"),
                    self._create_args(i),
                    i.get("trakt_id"),
                )
                for i in seasons
            ),
        )
        self.save_to_meta_table(to_insert, "seasons", "trakt", "trakt_id")
        self._set_needs_update(seasons, to_insert)

    def _alt_mill_if_needed(self, list_to_update, queue_wrapper=None, mill_episodes=True):
        if queue_wrapper is None:
            queue_wrapper = self._queue_mill_tasks

        query = """select s.anilist_id, CASE WHEN (agg.episode_count is NULL or 
        agg.episode_count != s.episode_count) or (agg.meta_count=0 or agg.meta_count!=s.episode_count) THEN 'True' 
        ELSE 'False' END as needs_update from shows as s left join(select s.anilist_id, count(e.anilist_id) as 
        episode_count, count(em.id) as meta_count from shows as s inner join episodes as e on s.anilist_id = 
        e.anilist_id left join episodes_meta as em on em.id = e.anilist_id and em.type = 'anilist' and em.meta_hash = 
        '{}' where e.season != 0 and Datetime(e.air_date) < Datetime('now') GROUP BY s.anilist_id) as agg on s.anilist_id == 
        agg.anilist_id WHERE s.anilist_id in ({})""".format(
            self.trakt_api.meta_hash,
            ",".join(
                str(i.get("anilist_id", i.get("anilist_id"))) for i in list_to_update
            ),
        )

        needs_update = self.fetchall(query)
        if needs_update is None:
            return
        needs_update = {x.get('anilist_id'): x for x in needs_update if x.get('needs_update') == "True"}
        update_size = len(needs_update)
        if update_size > 0:
            g.log("{} items require episode milling".format(update_size), "debug")
        else:
            return

        self.mill_episodes(
            [
                i
                for i in list_to_update
                if i.get("anilist_id", i.get("anilist_id")) in needs_update
            ],
            queue_wrapper,
            mill_episodes
        )

    def mill_episodes(self, trakt_collection, queue_wrapper, mill_episodes=False):
        with SyncLock(
            "mill_seasons_episodes_{}".format(mill_episodes),
            {
                show.get("anilist_id", show.get("anilist_id"))
                for show in trakt_collection
            },
        ) as sync_lock:
            # Everything we are milling may already be being milled in another process/thread
            # we need to check if there are any running IDs first.  The sync_lock wont exit until
            # the other process/thread is done with its milling giving good results.
            if len(sync_lock.running_ids) > 0:
                get = MetadataHandler.get_trakt_info
                queue_wrapper(
                    self._pull_show_episodes, [(i, mill_episodes) for i in sync_lock.running_ids]
                )
                results = self.mill_task_queue.wait_completion()
                seasons = []
                episodes = []
                trakt_info = MetadataHandler.trakt_info

                # for show in trakt_collection:
                #     extended_seasons = {get(x, "season"): x for x in get(show, "seasons", [])}
                #     item_information = control.get_item_information(show.get("anilist_id"))
                #     anilist_id = show.get("anilist_id")
                #     trakt_id_ = item_information['trakt_id']
                #     aired_year = item_information['air_date'].split('-')[0]
                #     episode_count = item_information["episode_count"]

                #     for episode in get(season, "episodes", []):
                #         trakt_info(episode).update({"trakt_show_id": trakt_id_})
                #         trakt_info(episode).update({"tmdb_show_id": get(show, "tmdb_id")})
                #         trakt_info(episode).update({"tvdb_show_id": get(show, "tvdb_id")})
                #         trakt_info(episode).update({"trakt_season_id": get(season, "trakt_id")})
                #         trakt_info(episode).update({"anilist_id": show.get("anilist_id")})

                #         episode.update({"trakt_show_id": trakt_id_})
                #         episode.update({"tmdb_show_id": show.get("tmdb_id")})
                #         episode.update({"tvdb_show_id": show.get("tvdb_id")})
                #         episode.update({"trakt_season_id": season.get("trakt_id")})
                #         episode.update({"anilist_id": show.get("anilist_id")})

                #         trakt_info(episode).update({"tvshowtitle": get(show, "title")})

                #         extended_episodes = {
                #             get(x, "episode"): x for x in get(extended_season, "episodes", [])
                #         }
                #         extended_episode = extended_episodes.get(get(episode, "episode"))
                #         if extended_episode:
                #             control.smart_merge_dictionary(episode, extended_episode, keep_original=True)

                #         episodes.append(episode)
                
                # if not retry and not seasons:
                #     self.mill_seasons(trakt_collection, queue_wrapper, mill_episodes=False, retry=True)

                # if episode_count:
                #     episodes = episodes[:episode_count]

                # self.insert_trakt_seasons(seasons)
                # self.insert_trakt_episodes(episodes)

    def _mill_if_needed(self, list_to_update, queue_wrapper=None, mill_episodes=True):
        if queue_wrapper is None:
            queue_wrapper = self._queue_mill_tasks

        if mill_episodes:
            query = """select s.anilist_id, CASE WHEN (agg.episode_count is NULL or 
            agg.episode_count != s.episode_count) or (agg.meta_count=0 or agg.meta_count!=s.episode_count) THEN 'True' 
            ELSE 'False' END as needs_update from shows as s left join(select s.anilist_id, count(e.anilist_id) as 
            episode_count, count(em.id) as meta_count from shows as s inner join episodes as e on s.anilist_id = 
            e.anilist_id left join episodes_meta as em on em.id = e.anilist_id and em.type = 'anilist' and em.meta_hash = 
            '{}' where e.season != 0 and Datetime(e.air_date) < Datetime('now') GROUP BY s.anilist_id) as agg on s.anilist_id == 
            agg.anilist_id WHERE s.anilist_id in ({})""".format(
                self.trakt_api.meta_hash,
                ",".join(
                    str(i.get("anilist_id", i.get("anilist_id"))) for i in list_to_update
                ),
            )
        else:
            query = """select s.anilist_id, agg.meta_count, s.episode_offset, s.trakt_id, CASE WHEN (agg.episode_offset is NULL or 
                agg.episode_offset != s.episode_offset) or (agg.meta_count=0 or agg.meta_count!=s.episode_offset) THEN 'True' 
                ELSE 'False' END as needs_update from shows as s left join(select s.anilist_id, count(se.anilist_id) as 
                episode_offset, count(sm.id) as meta_count from shows as s inner join seasons as se on s.anilist_id = 
                se.anilist_id left join seasons_meta as sm on sm.id = se.anilist_id and sm.type = 'anilist' and sm.meta_hash = 
                '{}' where se.season != 0 and Datetime(se.air_date) < Datetime('now') 
                GROUP BY s.anilist_id) as agg on s.anilist_id == agg.anilist_id WHERE s.anilist_id in ({})""".format(
                self.trakt_api.meta_hash,
                ",".join(
                    str(i.get("anilist_id", i.get("anilist_id"))) for i in list_to_update
                ),
            )
        needs_update = self.fetchall(query)
        if needs_update is None:
            return
        needs_update = {x.get('anilist_id'): x for x in needs_update if x.get('needs_update') == "True"}
        update_size = len(needs_update)
        if update_size > 0:
            g.log("{} items require season milling".format(update_size), "debug")
        else:
            return

        self.mill_seasons(
            [
                i
                for i in list_to_update
                if i.get("anilist_id", i.get("anilist_id")) in needs_update
            ],
            queue_wrapper,
            mill_episodes
        )

    def mill_seasons(self, trakt_collection, queue_wrapper, mill_episodes=False):
        with SyncLock(
            "mill_seasons_episodes_{}".format(mill_episodes),
            {
                show.get("anilist_id", show.get("anilist_id"))
                for show in trakt_collection
            },
        ) as sync_lock:
            # Everything we are milling may already be being milled in another process/thread
            # we need to check if there are any running IDs first.  The sync_lock wont exit until
            # the other process/thread is done with its milling giving good results.
            if len(sync_lock.running_ids) > 0:
                get = MetadataHandler.get_trakt_info
                queue_wrapper(
                    self._pull_show_seasons, [(i, mill_episodes) for i in sync_lock.running_ids]
                )
                results = self.mill_task_queue.wait_completion()
                seasons = []
                episodes = []
                trakt_info = MetadataHandler.trakt_info

                for show in trakt_collection:
                    extended_seasons = {get(x, "season"): x for x in get(show, "seasons", [])}
                    item_information = control.get_item_information(show.get("anilist_id"))
                    anilist_id = show.get("anilist_id")
                    trakt_id_ = item_information['trakt_id']
                    aired_year = item_information['air_date'].split('-')[0]
                    episode_count = item_information["episode_count"]
                    for season in results.get(trakt_id_, []):
                        if get(season, "season") == 0:
                            continue

                        if anilist_id in {113538, 119661, 104578, 116742, 127720}:
                            continue

                        if not episode_count:
                            continue

                        if episode_count and episode_count > 40:
                            continue

                        season_air_date = {get(season, "year"), get(season, "premiered")}
                        if not aired_year in season_air_date:
                            continue

                        # if retry:
                        #     part_aired_year =  '{}'.format(int(aired_year) - 1)
                        #     if not part_aired_year in get(season, "year"):
                        #         continue
                            # if retry and '2018' in get(season, "year"):
                        # import xbmcgui
                        # xbmcgui.Dialog().textviewer('sdsd', str(date_ended))
                            #     pass
                            # else:
                            #     continue

                        trakt_info(season).update({"trakt_show_id": trakt_id_})#get(show, "trakt_id")})
                        trakt_info(season).update({"tmdb_show_id": get(show, "tmdb_id")})
                        trakt_info(season).update({"tvdb_show_id": get(show, "tvdb_id")})
                        trakt_info(season).update({"anilist_id": show.get("anilist_id")})

                        season.update({"trakt_show_id": trakt_id_})#show.get("trakt_id")})
                        season.update({"tmdb_show_id": show.get("tmdb_id")})
                        season.update({"tvdb_show_id": show.get("tvdb_id")})
                        season.update({"anilist_id": show.get("anilist_id")})

                        trakt_info(season).update({"dateadded": get(show, "dateadded")})
                        trakt_info(season).update({"tvshowtitle": get(show, "title")})

                        if not get(season, "season") == 0:
                            show.update({"season_count": show.get("season_count", 0) + (
                                1 if get(season, "aired_episodes", 0) > 0 else 0)})
                            show.update(
                                {
                                    'episode_count': show.get("episode_count", 0) + get(season, "aired_episodes", 0)
                                }
                            )

                        extended_season = extended_seasons.get(get(season, "season"))
                        if extended_season:
                            control.smart_merge_dictionary(season, extended_season, keep_original=True)

                        seasons.append(season)

                        for episode in get(season, "episodes", []):
                            trakt_info(episode).update({"trakt_show_id": trakt_id_})
                            trakt_info(episode).update({"tmdb_show_id": get(show, "tmdb_id")})
                            trakt_info(episode).update({"tvdb_show_id": get(show, "tvdb_id")})
                            trakt_info(episode).update({"trakt_season_id": get(season, "trakt_id")})
                            trakt_info(episode).update({"anilist_id": show.get("anilist_id")})

                            episode.update({"trakt_show_id": trakt_id_})
                            episode.update({"tmdb_show_id": show.get("tmdb_id")})
                            episode.update({"tvdb_show_id": show.get("tvdb_id")})
                            episode.update({"trakt_season_id": season.get("trakt_id")})
                            episode.update({"anilist_id": show.get("anilist_id")})

                            trakt_info(episode).update({"tvshowtitle": get(show, "title")})

                            extended_episodes = {
                                get(x, "episode"): x for x in get(extended_season, "episodes", [])
                            }
                            extended_episode = extended_episodes.get(get(episode, "episode"))
                            if extended_episode:
                                control.smart_merge_dictionary(episode, extended_episode, keep_original=True)

                            episodes.append(episode)
                
                # if not retry and not seasons:
                #     self.mill_seasons(trakt_collection, queue_wrapper, mill_episodes=False, retry=True)

                if episode_count:
                    episodes = episodes[:episode_count]

                self.insert_trakt_seasons(seasons)
                self.insert_trakt_episodes(episodes)

                # self.execute_sql("UPDATE shows SET episode_count=?, season_count=? WHERE trakt_id=? ",
                #                  [(i.get("episode_count", 0), i.get("season_count", 0), i["trakt_id"])
                #                   for i in trakt_collection])

                # self.update_shows_statistics({"trakt_id": i} for i in sync_lock.running_ids)

                # if mill_episodes:
                #     self.update_season_statistics({"trakt_id": i['trakt_id']} for i in seasons)

    def _filter_trakt_items_that_needs_updating(self, requested, media_type):
        if not requested:
            return requested

        get = MetadataHandler.get_anilist_info
        query_predicate = ["({}, '{}', '{}', '{}')".format(
            i.get("anilist_id"), self.trakt_api.meta_hash, get(i, "dateadded"), get(i, "is_airing")
        )
            for i in requested
            if i.get("anilist_id")
               and "needs_update" not in i]

        if not query_predicate:
            return []

        query = """WITH requested(anilist_id, meta_hash, updated_at, is_airing) AS (VALUES {}) 
        select r.anilist_id as anilist_id from requested as r left join {} as db on r.anilist_id == db.anilist_id 
        left join {}_meta as m on db.anilist_id == id and type="anilist" where db.anilist_id IS NULL or m.value IS NULL or 
        m.meta_hash != r.meta_hash or (Datetime(db.last_updated) < Datetime(r.updated_at)) or db.is_airing != r.is_airing""".format(
            ",".join(query_predicate),
            media_type,
            media_type,
        )

        result = set(r["anilist_id"] for r in self.fetchall(query))
        return [
            r for r in requested if r.get("anilist_id") and r.get("anilist_id") in result
        ]

    def _filter_trakt2_items_that_needs_updating(self, requested, media_type):
        if not requested:
            return requested

        get = MetadataHandler.get_trakt_info
        query_predicate = ["({}, '{}', '{}')".format(
            i.get("trakt_id"), self.trakt_api.meta_hash, get(i, "dateadded")
        )
            for i in requested
            if i.get("trakt_id")
               and "needs_update" not in i]

        if not query_predicate:
            return []

        query = """WITH requested(trakt_id, meta_hash, updated_at) AS (VALUES {}) 
        select r.trakt_id as trakt_id from requested as r left join {} as db on r.trakt_id == db.trakt_id 
        left join {}_meta as m on db.trakt_id == id and type="trakt" where db.trakt_id IS NULL or m.value IS NULL or 
        m.meta_hash != r.meta_hash or (Datetime(db.last_updated) < Datetime(r.updated_at))""".format(
            ",".join(query_predicate),
            media_type,
            media_type,
        )

        result = set(r["trakt_id"] for r in self.fetchall(query))
        return [
            r for r in requested if r.get("trakt_id") and r.get("trakt_id") in result
        ]

    def _filter_tmdb_items_that_needs_updating(self, requested, media_type):
        if not requested:
            return requested

        # get = MetadataHandler.info
        query_predicate = ["({}, '{}')".format(
            i["info"].get("tmdb_id"), i["info"].get("aired")
        )
            for i in requested
            if i["info"].get("tmdb_id")
               and "needs_update" not in i]

        if not query_predicate:
            return []

        query = """WITH requested(trakt_id, updated_at) AS (VALUES {}) 
        select r.trakt_id as trakt_id from requested as r left join {} as db on r.trakt_id == db.trakt_id 
        where db.trakt_id IS NULL or (Datetime('now') < Datetime(r.updated_at))""".format(
            ",".join(query_predicate),
            media_type,
        )

        query_result = self.fetchall(query) + [{"trakt_id": r["info"].get("tmdb_id")} for r in requested if not r["info"].get("plot")]

        result = set(r["trakt_id"] for r in query_result)
        return [
            r for r in requested if r["info"].get("tmdb_id") and r["info"].get("tmdb_id") in result
        ]

    def _filter_simkl_items_that_needs_updating(self, requested, media_type):
        if not requested:
            return requested

        # get = MetadataHandler.info
        query_predicate = ["({}, '{}')".format(
            i["info"].get("simkl_id"), i["info"].get("aired")
        )
            for i in requested
            if i["info"].get("simkl_id")
               and "needs_update" not in i]

        if not query_predicate:
            return []

        query = """WITH requested(trakt_id, updated_at) AS (VALUES {}) 
        select r.trakt_id as trakt_id from requested as r left join {} as db on r.trakt_id == db.trakt_id 
        where db.trakt_id IS NULL or (Datetime('now') < Datetime(r.updated_at))""".format(
            ",".join(query_predicate),
            media_type,
        )

        query_result = self.fetchall(query) + [{"trakt_id": r["info"].get("simkl_id")} for r in requested if not r["info"].get("plot")]

        result = set(r["trakt_id"] for r in query_result)
        return [
            r for r in requested if r["info"].get("simkl_id") and r["info"].get("simkl_id") in result
        ]

    def _pull_show_seasons(self, show_id, mill_episodes=False):
        show_id = control.get_item_information(show_id)['trakt_id']
        return {
            show_id: self.trakt_api2.get_json(
                "/shows/{}/seasons".format(show_id),
                extended="full,episodes" if mill_episodes else "full",
                translations=g.get_language_code(),
            )
        }

    @staticmethod
    def _create_args(item):
        get = MetadataHandler.get_anilist_info
        info = MetadataHandler.info
        args = {
            "anilist_id": get(item, "anilist_id", info(item).get("anilist_id")),
            "mediatype": get(item, "mediatype", info(item).get("mediatype")),
        }
        if args["anilist_id"] is None:
            import inspect
            g.log(inspect.stack())
            g.log(item)
        if args["mediatype"] == "movie":
            args['url'] = "play_movie/{}/1/".format(args['anilist_id'])
        if args["mediatype"] == "season":
            args["trakt_id"] = get(
                item, "trakt_id", info(item).get("trakt_id")
            )
            args["trakt_show_id"] = get(
                item, "trakt_show_id", info(item).get("trakt_show_id")
            )
        if args["mediatype"] == "episode":
            args["episode"] = info(item).get("episode")
            args["trakt_show_id"] = get(
                item, "trakt_show_id", info(item).get("trakt_show_id")
            )
            args["trakt_season_id"] = get(
                item, "trakt_season_id", info(item).get("trakt_season_id")
            )
        return control.quote(json.dumps(args, sort_keys=True))

    def _queue_mill_tasks(self, func, args):
        for arg in args:
            self.mill_task_queue.put(func, *arg)

    # @staticmethod
    # def requires_update(new_date, old_date):
    #     if tools.parse_datetime(
    #         new_date, g.DATE_TIME_FORMAT_ZULU, False
    #     ) > tools.parse_datetime(old_date, g.DATE_TIME_FORMAT, False):
    #         return True
    #     else:
    #         return False

    @staticmethod
    def wrap_in_trakt_object(items):
        for item in items:
            if item.get("show") is not None:
                info = item["show"].pop("info")
                item["show"].update({"trakt_id": info.get("trakt_id")})
                item["show"].update({"trakt_object": {"info": info}})
            if item.get("episode") is not None:
                info = item["episode"].pop("info")
                item["episode"].update({"trakt_id": info.get("trakt_id")})
                item["episode"].update({"tvdb_id": info.get("tvdb_id")})
                item["episode"].update({"tmdb_id": info.get("tmdb_id")})
                item["episode"].update({"trakt_object": {"info": info}})
        return items

    def _get_single_meta(self, anilist_id, media_type):
        return self._update_single_meta(
            anilist_id,
            self.fetchone(
                """select id as anilist_id, value as anilist_object from 
        {}_meta where id = ? and type = 'anilist' """.format(
                    media_type
                ),
                (int(anilist_id),),
            ),
            media_type,
        )

    def _get_single_meta_mal(self, mal_id, media_type):
        statement = """SELECT s.anilist_id, s.mal_id FROM shows as s 
        WHERE s.mal_id == {}""".format(mal_id)

        return self.fetchone(statement)

    def _update_single_meta(self, anilist_id, item, media_type):
        anilist_object = MetadataHandler.anilist_object
        if item is None:
            item = {}
        if anilist_object(item) is None or anilist_object(item) == {}:
            new_object = self.trakt_api.get_anilist_id(anilist_id)
            self.save_to_meta_table([new_object], media_type, "anilist", "anilist_id")
            item.update(new_object)
        return item

    @staticmethod
    def update_missing_trakt_objects(db_list_to_update, list_to_update):
        for item in db_list_to_update:
            if item.get("anilist_object") is None:
                try:
                    item.update(
                        next(
                            i
                            for i in list_to_update
                            if int(i.get("anilist_id") or 0)
                            == int(item.get("anilist_id") or 0)
                        )
                    )
                except StopIteration:
                    g.log(
                        "Failed to find item in list to update, original item: \n {}".format(
                            item
                        )
                    )

    def _extract_trakt_page(self, url, media_type, **params):
        result = []

        # hide_watched = params.get("hide_watched", self.hide_watched)
        # hide_unaired = params.get("hide_unaired", self.hide_unaired)
        get = MetadataHandler.get_anilist_info

        def _handle_page(current_page):
            if not current_page:
                return []
            if media_type == "shows":
                self.insert_anilist_shows(current_page)
            query = (
                "WITH requested(anilist_id) AS (VALUES {}) select r.anilist_id as anilist_id from requested as r inner "
                "join {} as db on r.anilist_id == db.anilist_id left join {}_meta as m on db.anilist_id == "
                "id and type = 'anilist' where 1=1".format(
                    ",".join("({})".format(i.get("anilist_id", get(i, "anilist_id"))) for i in current_page),
                    media_type,
                    media_type,
                )
            )
            # if hide_unaired:
            #     query += " AND Datetime(air_date) < Datetime('now')"
            # if hide_watched:
            #     if media_type == "movies":
            #         query += " AND watched = 0"
            #     if media_type == "shows":
            #         query += " AND watched_episodes < episode_count"
            result_ids = self.fetchall(query)
            result.extend([p for p in current_page
                           if any(r for r in result_ids
                                  if p.get("anilist_id", get(p, "anilist_id")) == r.get("anilist_id"))])

        no_paging = params.get("no_paging", False)
        pull_all = params.pop("pull_all", False)
        page_number = params.pop("page", 1)
        if params['cached'] == 0:
            page, hasNextPage = self.trakt_api.post_json(url, **params)
        else:
            page, hasNextPage = self.trakt_api.post_json_cached(url, **params)
        if not hasNextPage:
            g.REQUEST_PARAMS['no_paging'] = True

        _handle_page(page)
        # import xbmcgui
        # xbmcgui.Dialog().textviewer('dsds', str(page))
        #if pull_all:
            #return
            # _handle_page(self.trakt_api.get_json_cached(url, **params))
            # if len(result) >= (self.page_limit * page_number) and not no_paging:
            #     return result[
            #         self.page_limit * (page_number - 1) : self.page_limit * page_number
            #     ]
        #else:
            # params["limit"] = params.pop("page", self.page_limit)
            # for page in self.trakt_api.get_all_pages_json(url, **params):
            #     import xbmcgui
            #     xbmcgui.Dialog().textviewer('dsds', str(page))
                
                # _handle_page(page)
                # if len(result) >= (self.page_limit * page_number) and not no_paging:
                #     return result[
                #         self.page_limit
                #         * (page_number - 1) : self.page_limit
                #         * page_number
                #     ]

        return result

    def _extract_animelist_page(self, url, media_type, **params):
        result = []

        # hide_watched = params.get("hide_watched", self.hide_watched)
        # hide_unaired = params.get("hide_unaired", self.hide_unaired)
        get = MetadataHandler.get_anilist_info

        def _handle_page(current_page):
            if not current_page:
                return []
            if media_type == "shows":
                self.insert_anilist_shows(current_page)
            query = (
                "WITH requested(anilist_id) AS (VALUES {}) select r.anilist_id as anilist_id from requested as r inner "
                "join {} as db on r.anilist_id == db.anilist_id left join {}_meta as m on db.anilist_id == "
                "id and type = 'anilist' where 1=1".format(
                    ",".join("({})".format(i.get("anilist_id", get(i, "anilist_id"))) for i in current_page),
                    media_type,
                    media_type,
                )
            )
            # if hide_unaired:
            #     query += " AND Datetime(air_date) < Datetime('now')"
            # if hide_watched:
            #     if media_type == "movies":
            #         query += " AND watched = 0"
            #     if media_type == "shows":
            #         query += " AND watched_episodes < episode_count"
            result_ids = self.fetchall(query)
            result.extend([p for p in current_page
                           if any(r for r in result_ids
                                  if p.get("anilist_id", get(p, "anilist_id")) == r.get("anilist_id"))])

        no_paging = params.get("no_paging", False)
        pull_all = params.pop("pull_all", False)
        page_number = params.pop("page", 1)

        page, hasNextPage = self.anilist_animelist.post_json_cached(url, **params)
        if not hasNextPage:
            g.REQUEST_PARAMS['no_paging'] = True

        _handle_page(page)

        return result

    def update_shows_statistics(self, trakt_list):
        self.__update_shows_statisics(trakt_list)

    def _update_all_shows_statisics(self):
        self.__update_shows_statisics()

    def __update_shows_statisics(self, trakt_list=None):
        query = (
            """INSERT or REPLACE into shows (anilist_id, kitsu_id, mal_id, simkl_id, trakt_id, tmdb_id, tvdb_id, 
            imdb_id, info, art, cast, air_date, last_updated, meta_hash, episode_indexer, episode_count, episode_offset, 
            watched_episodes, unwatched_episodes, args, is_airing, needs_update) SELECT old.anilist_id, old.kitsu_id,
            old.mal_id, old.simkl_id, old.trakt_id, old.tmdb_id, old.tvdb_id, old.imdb_id, old.info, old.art, 
            old.cast, COALESCE(new.air_date, old.air_date), old.last_updated, old.meta_hash, old.episode_indexer, 
            COALESCE(new.episode_count, old.episode_count), old.episode_offset, COALESCE(new.watched_episodes, 
            old.watched_episodes), COALESCE(new.unwatched_episodes, old.unwatched_episodes), old.args, old.is_airing, 
            old.needs_update FROM (select sh.anilist_id, CASE WHEN min(COALESCE(e.air_date, datetime(
            '9999-12-31T00:00:00'))) <> datetime('9999-12-31T00:00:00') THEN min(COALESCE(e.air_date, 
            datetime('9999-12-31T00:00:00'))) END as air_date, sum(CASE WHEN e.season 
            != 0 AND Datetime(e.air_date) < Datetime('now') THEN 1 END) as episode_count, ( CASE WHEN sum(CASE WHEN 
            e.season != 0 AND Datetime(e.air_date) < Datetime('now') THEN 1 END) > sh.episode_count THEN sum(CASE 
            WHEN e.season != 0 AND Datetime(e.air_date) < Datetime('now') THEN 1 END) ELSE sh.episode_count END ) - 
            sum(CASE WHEN e.watched > 0 AND e.season != 0 AND Datetime(e.air_date) < Datetime('now') THEN 1 ELSE 0 
            END) as unwatched_episodes, sum( CASE WHEN e.watched > 0 AND e.season != 0 AND Datetime(e.air_date) < 
            Datetime('now') THEN 1 END ) as watched_episodes from shows as sh left join episodes as e on 
            e.anilist_id = sh.anilist_id group by sh.anilist_id) AS new LEFT JOIN (SELECT * FROM shows) AS old on 
            old.anilist_id = new.anilist_id """
        )
        if trakt_list:
            trakt_ids = ",".join({str(i.get("anilist_id")) for i in trakt_list})
            query += " where old.anilist_id in ({})".format(trakt_ids)
        self.execute_sql(query)

    def update_season_statistics(self, trakt_list):
        self.__update_season_statistics(trakt_list)

    def _update_all_season_statistics(self):
        self.__update_season_statistics()

    def __update_season_statistics(self, trakt_list=None):
        query = (
            """INSERT or REPLACE into seasons ( trakt_show_id, trakt_id, info, art, cast, air_date, last_updated, 
            tmdb_id, tvdb_id, meta_hash, episode_count, watched_episodes, unwatched_episodes, is_airing, season, 
            args , needs_update) SELECT old.trakt_show_id, old.trakt_id, old.info, old.art, old.cast, 
            COALESCE(new.air_date, old.air_date), old.last_updated, old.tmdb_id, old.tvdb_id, old.meta_hash, 
            COALESCE(new.episode_count, old.episode_count), CASE WHEN COALESCE(new.watched_episodes, 
            old.watched_episodes) is not null THEN COALESCE(new.watched_episodes, old.watched_episodes) ELSE 0 END, 
            CASE WHEN COALESCE(new.unwatched_episodes, old.unwatched_episodes) is not null THEN COALESCE(
            new.unwatched_episodes, old.unwatched_episodes) ELSE COALESCE(new.episode_count, old.episode_count) END, 
            CASE WHEN COALESCE(new.is_airing, old.is_airing) is not null THEN COALESCE(new.is_airing, old.is_airing) 
            ELSE 0 END, old.season, old.args, old.needs_update FROM (SELECT se.trakt_id, CASE WHEN min(COALESCE(
            e.air_date, datetime('9999-12-31T00:00:00'))) <> datetime('9999-12-31T00:00:00') THEN min(COALESCE(
            e.air_date, datetime('9999-12-31T00:00:00'))) END as air_date, sum(CASE WHEN datetime(e.air_date) < 
            datetime('now') THEN 1 END) AS episode_count, sum(CASE WHEN e.watched == 0 AND datetime(e.air_date) < 
            datetime('now') THEN 1 END) AS unwatched_episodes, sum(CASE WHEN e.watched > 0 AND datetime(e.air_date) < 
            datetime('now') THEN 1 END) AS watched_episodes, CASE WHEN max(e.air_date) is not null THEN CASE WHEN 
            max(e.air_date) > datetime('now') THEN 1 ELSE 0 END END AS is_airing FROM seasons AS se LEFT JOIN 
            episodes AS e ON e.trakt_season_id = se.trakt_id GROUP BY se.trakt_id ) AS new LEFT JOIN (SELECT * FROM 
            seasons) AS old ON new.trakt_id = old.trakt_id """
        )
        if trakt_list:
            trakt_ids = ",".join({str(i.get("trakt_id")) for i in trakt_list})
            query += " where old.trakt_id in ({})".format(trakt_ids)
        else:
            query += " where old.trakt_id in (SELECT trakt_id from seasons where 1==1)"
        self.execute_sql(query)

    # @property
    # def upsert_movie_query(self):
    #     return """INSERT or REPLACE into movies ( trakt_id, info, art, cast, collected, watched, air_date, 
    #     last_updated, tmdb_id, imdb_id, meta_hash, args, collected_at, last_watched_at ) SELECT COALESCE(
    #     new.trakt_id, old.trakt_id), COALESCE(new.info, old.info), COALESCE(new.art, old.art), COALESCE(new.cast, 
    #     old.cast), COALESCE(new.collected, old.collected), COALESCE(new.watched, old.watched), COALESCE(new.air_date, 
    #     old.air_date), COALESCE(new.last_updated, old.last_updated), COALESCE(new.tmdb_id, old.tmdb_id), 
    #     COALESCE(new.imdb_id, old.imdb_id), COALESCE(new.meta_hash, old.meta_hash), COALESCE(new.args, old.args), 
    #     COALESCE(new.collected_at, old.collected_at), COALESCE(new.last_watched_at, old.last_watched_at) FROM ( 
    #     SELECT ? AS trakt_id, ? AS info, ? AS art, ? AS cast, ? AS collected, ? as watched, ? AS air_date, 
    #     ? AS last_updated, ? AS tmdb_id, ? AS imdb_id, ? AS meta_hash, ? AS args, ? AS collected_at, 
    #     ? AS last_watched_at) AS new LEFT JOIN (SELECT * FROM movies WHERE trakt_id = ? limit 1) AS old """

    @property
    def upsert_show_query(self):
        return """INSERT or REPLACE into shows (anilist_id, kitsu_id, mal_id, simkl_id, trakt_id, tmdb_id, tvdb_id, 
        imdb_id, info, art, cast, air_date, last_updated, meta_hash, episode_indexer, episode_count, episode_offset, 
        watched_episodes, unwatched_episodes, args, is_airing, needs_update) SELECT COALESCE(new.anilist_id, old.anilist_id), 
        COALESCE(new.kitsu_id, old.kitsu_id), COALESCE(new.mal_id, old.mal_id), COALESCE(new.simkl_id, old.simkl_id), 
        COALESCE(new.trakt_id, old.trakt_id), COALESCE(new.tmdb_id, old.tmdb_id), COALESCE(new.tvdb_id, old.tvdb_id), 
        COALESCE(new.imdb_id, old.imdb_id), COALESCE(new.info, old.info), COALESCE(new.art, old.art), COALESCE(new.cast, old.cast), 
        COALESCE(new.air_date, old.air_date), COALESCE(new.last_updated, old.last_updated), COALESCE(new.meta_hash, old.meta_hash),
        COALESCE(new.episode_indexer, old.episode_indexer), COALESCE(new.episode_count, old.episode_count), 
        COALESCE( new.episode_offset, old.episode_offset), COALESCE(old.watched_episodes, 0), COALESCE(old.unwatched_episodes, 0), 
        COALESCE(new.args, old.args), COALESCE(new.is_airing, old.is_airing), 
        Datetime(coalesce(old.last_updated, 0)) < Datetime(new.last_updated) as needs_update FROM (SELECT 
        ? AS anilist_id, ? AS kitsu_id, ? AS mal_id, ? AS simkl_id, ? AS trakt_id, ? AS tmdb_id, ? AS tvdb_id, ? AS imdb_id, 
        ? AS info, ? AS art, ? AS cast, ? AS air_date, ? AS last_updated, ? AS meta_hash, ? as episode_indexer, 
        ? AS episode_count, ? AS episode_offset, ? AS args, ? as is_airing) AS new LEFT JOIN 
        (SELECT * FROM shows WHERE anilist_id = ? limit 1) AS old """

    @property
    def upsert_season_query(self):
        return """INSERT or REPLACE into seasons (anilist_id, trakt_show_id, trakt_id, info, art, cast, air_date, last_updated, 
        tmdb_id, tvdb_id, meta_hash, episode_count, watched_episodes, unwatched_episodes, season, args, is_airing, needs_update) 
        SELECT COALESCE(new.anilist_id, old.anilist_id), COALESCE(new.trakt_show_id, old.trakt_show_id), 
        COALESCE(new.trakt_id, old.trakt_id), COALESCE(new.info, old.info), COALESCE(new.art, old.art), COALESCE(new.cast, old.cast), 
        COALESCE(new.air_date, old.air_date), COALESCE(new.last_updated, old.last_updated), COALESCE(new.tmdb_id, old.tmdb_id), 
        COALESCE(new.tvdb_id, old.tvdb_id), COALESCE(new.meta_hash, old.meta_hash), COALESCE(new.episode_count, old.episode_count), 
        old.watched_episodes, old.unwatched_episodes, COALESCE(new.season, old.season), COALESCE(new.args, 
        old.args), old.is_airing, Datetime(coalesce(old.last_updated, 0)) < Datetime(new.last_updated) as needs_update FROM 
        ( SELECT ? AS anilist_id, ? AS trakt_show_id, ? AS trakt_id, ? AS info, ? AS art, ? AS cast, ? 
        AS air_date, ? AS last_updated, ? AS tmdb_id, ? AS tvdb_id, ? AS meta_hash, ? AS episode_count, ? AS season, ? 
        AS args) AS new LEFT JOIN ( SELECT * FROM seasons WHERE trakt_id = ? limit 1) AS old """

    @property
    def upsert_episode_query(self):
        return """INSERT or REPLACE into episodes (anilist_id, trakt_id, trakt_show_id, trakt_season_id, watched, collected, 
        air_date, last_updated, season, number, tmdb_id, tvdb_id, imdb_id, info, art, cast, args, last_watched_at, 
        collected_at, meta_hash ) SELECT COALESCE (new.anilist_id, old.anilist_id), COALESCE (new.trakt_id , old.trakt_id), 
        COALESCE (new.trakt_show_id, old.trakt_show_id), COALESCE (new.trakt_season_id , old.trakt_season_id), COALESCE 
        (new.watched, old.watched), COALESCE (new.collected, old.collected), COALESCE (new.air_date, old.air_date), 
        COALESCE (new.last_updated, old.last_updated), COALESCE (new.season, old.season), COALESCE (new.number, old.number), 
        COALESCE (new.tmdb_id , old.tmdb_id), COALESCE (new.tvdb_id , old.tvdb_id), COALESCE (new.imdb_id , old.imdb_id), 
        COALESCE (new.info , old.info), COALESCE (new.art , old.art), COALESCE (new.cast , old.cast), COALESCE (new.args , old.args), 
        COALESCE (new.last_watched_at , old.last_watched_at), COALESCE (new.collected_at , old.collected_at), COALESCE (new.meta_hash , 
        old.meta_hash) FROM (SELECT ? AS anilist_id, ? AS trakt_id, ? AS trakt_show_id, ? AS trakt_season_id, ? AS watched, 
        ? AS collected, ? AS air_date, ? AS last_updated, ? AS season, ? AS number, ? AS tmdb_id, ? AS tvdb_id, ? AS imdb_id, 
        ? AS info, ? AS art, ? AS cast, ? AS args, ? AS last_watched_at, ? AS collected_at, ? AS meta_hash) AS new LEFT 
        JOIN ( SELECT * FROM episodes WHERE trakt_id = ? limit 1) AS old """