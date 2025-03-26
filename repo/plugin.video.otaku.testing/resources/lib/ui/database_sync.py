from resources.lib.ui import control
from sqlite3 import version
from resources.lib.ui.database import SQL

sqlite_version = version


class SyncDatabase:
    def __init__(self):
        self.activites = None

        self.build_sync_activities()
        self.build_show_table()
        self.build_showmeta_table()
        self.build_episode_table()
        self.build_show_data_table()

        # If you make changes to the required meta in any indexer that is cached in this database
        # You will need to update the below version number to match the new addon version
        # This will ensure that the metadata required for operations is available
        # You may also update this version number to force a rebuild of the database after updating Otaku
        self.last_meta_update = '1.0.5'
        self.refresh_activites()
        self.check_database_version()

    def refresh_activites(self):
        with SQL(control.malSyncDB) as cursor:
            cursor.execute('SELECT * FROM activities WHERE sync_id=1')
            self.activites = cursor.fetchone()

    def set_base_activites(self):
        with SQL(control.malSyncDB) as cursor:
            cursor.execute('INSERT INTO activities(sync_id, otaku_version) VALUES(1, ?)', (self.last_meta_update,))
            cursor.connection.commit()

    def check_database_version(self):
        # import xbmcvfs
        if not self.activites or self.activites.get('otaku_version') != self.last_meta_update:
            # xbmcvfs.delete(control.sort_options_json)
            # xbmcvfs.delete(control.searchHistoryDB)
            if control.getSetting('version') == '0.5.43':
                self.migration_process()
            self.re_build_database(True)

    @staticmethod
    def build_show_table():
        with SQL(control.malSyncDB) as cursor:
            cursor.execute('CREATE TABLE IF NOT EXISTS shows (mal_id INTEGER PRIMARY KEY, '
                           'anilist_id INTEGER,'
                           'simkl_id INTEGER,'
                           'kitsu_id INTEGER,'
                           'kodi_meta BLOB NOT NULL, '
                           'anime_schedule_route TEXT NOT NULL, '
                           'UNIQUE(mal_id))')
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_shows ON "shows" (mal_id ASC )')
            cursor.connection.commit()

    @staticmethod
    def build_showmeta_table():
        with SQL(control.malSyncDB) as cursor:
            cursor.execute('CREATE TABLE IF NOT EXISTS shows_meta (mal_id INTEGER PRIMARY KEY, '
                           'meta_ids BLOB,'
                           'art BLOB, '
                           'UNIQUE(mal_id))')
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_shows_meta ON "shows_meta" (mal_id ASC )')
            cursor.connection.commit()

    @staticmethod
    def build_show_data_table():
        with SQL(control.malSyncDB) as cursor:
            cursor.execute('CREATE TABLE IF NOT EXISTS show_data (mal_id INTEGER PRIMARY KEY, '
                           'data BLOB NOT NULL, '
                           'last_updated TEXT NOT NULL, '
                           'UNIQUE(mal_id))')
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_show_data ON "show_data" (mal_id ASC )')
            cursor.connection.commit()

    @staticmethod
    def build_episode_table():
        with SQL(control.malSyncDB) as cursor:
            cursor.execute('CREATE TABLE IF NOT EXISTS episodes (mal_id INTEGER NOT NULL, '
                           'season INTEGER NOT NULL, '
                           'kodi_meta BLOB NOT NULL, '
                           'last_updated TEXT NOT NULL, '
                           'number INTEGER NOT NULL, '
                           'filler TEXT, '
                           'anidb_ep_id INTEGER, '
                           'FOREIGN KEY(mal_id) REFERENCES shows(mal_id) ON DELETE CASCADE)')
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_episodes ON episodes (mal_id ASC, season ASC, number ASC)')
            cursor.connection.commit()

    @staticmethod
    def build_sync_activities():
        with SQL(control.malSyncDB) as cursor:
            cursor.execute('CREATE TABLE IF NOT EXISTS activities (sync_id INTEGER PRIMARY KEY, otaku_version TEXT NOT NULL)')
            cursor.connection.commit()

    def re_build_database(self, silent=False):
        import service

        if not silent:
            confirm = control.yesno_dialog(control.ADDON_NAME, control.lang(30032))
            if confirm == 0:
                return

        service.update_mappings_db()
        service.update_dub_json()

        with open(control.malSyncDB, 'w'):
            pass

        self.build_sync_activities()
        self.build_show_table()
        self.build_showmeta_table()
        self.build_episode_table()
        self.build_show_data_table()

        self.set_base_activites()
        self.refresh_activites()
        if not silent:
            control.notify(f'{control.ADDON_NAME}: Database', 'Metadata Database Successfully Cleared', sound=False)

    def migration_process(self):
        import json
        import xbmc

        # Retrieve current settings
        watchlist_update_enabled = control.getSetting('watchlist.update.enabled')
        watchlist_update_flavor = control.getSetting('watchlist.update.flavor')
        watchlist_update_percent = control.getSetting('watchlist.update.percent')
        watchlist_sync_enabled = control.getSetting('watchlist.sync.enabled')
        anilist_enabled = control.getSetting('anilist.enabled')
        anilist_username = control.getSetting('anilist.username')
        anilist_token = control.getSetting('anilist.token')
        anilist_userid = control.getSetting('anilist.userid')
        mal_enabled = control.getSetting('mal.enabled')
        mal_username = control.getSetting('mal.username')
        mal_authvar = control.getSetting('mal.authvar')
        mal_refresh = control.getSetting('mal.refresh')
        mal_token = control.getSetting('mal.token')
        mal_expiry = control.getSetting('mal.expiry')
        kitsu_enabled = control.getSetting('kitsu.enabled')
        kitsu_username = control.getSetting('kitsu.username')
        kitsu_authvar = control.getSetting('kitsu.authvar')
        kitsu_password = control.getSetting('kitsu.password')
        kitsu_refresh = control.getSetting('kitsu.refresh')
        kitsu_token = control.getSetting('kitsu.token')
        kitsu_userid = control.getSetting('kitsu.userid')
        kitsu_expiry = control.getSetting('kitsu.expiry')
        simkl_enabled = control.getSetting('simkl.enabled')
        simkl_username = control.getSetting('simkl.username')
        simkl_token = control.getSetting('simkl.token')
        version = control.ADDON_VERSION

        # First, clear existing settings
        control.clear_settings(True)

        # Save all these settings to migrationSettings (migration.json)
        migration_data = {
            "watchlist.update.enabled": watchlist_update_enabled,
            "watchlist.update.flavor": watchlist_update_flavor,
            "watchlist.update.percent": watchlist_update_percent,
            "watchlist.sync.enabled": watchlist_sync_enabled,
            "anilist.enabled": anilist_enabled,
            "anilist.username": anilist_username,
            "anilist.token": anilist_token,
            "anilist.userid": anilist_userid,
            "mal.enabled": mal_enabled,
            "mal.username": mal_username,
            "mal.authvar": mal_authvar,
            "mal.refresh": mal_refresh,
            "mal.token": mal_token,
            "mal.expiry": mal_expiry,
            "kitsu.enabled": kitsu_enabled,
            "kitsu.username": kitsu_username,
            "kitsu.authvar": kitsu_authvar,
            "kitsu.password": kitsu_password,
            "kitsu.refresh": kitsu_refresh,
            "kitsu.token": kitsu_token,
            "kitsu.userid": kitsu_userid,
            "kitsu.expiry": kitsu_expiry,
            "simkl.enabled": simkl_enabled,
            "simkl.username": simkl_username,
            "simkl.token": simkl_token,
            "version": version,
        }
        try:
            with open(control.migrationSettings, 'w', encoding='utf-8') as f:
                json.dump(migration_data, f, indent=4, sort_keys=True)
        except Exception as e:
            control.log(f"Error writing migration settings: {e}")

        # Inform user and force restart Kodi
        control.ok_dialog(control.ADDON_NAME, "Otaku has gotten a major update and requires a force restart to complete the watchlist migration.\nPlease restart Otaku to complete the migration.")
        xbmc.executebuiltin('Quit')
