################################################################################
#  Registry of video/info addons whose cache databases OpenWizard can clear.   #
#  Data only - no Kodi imports - so it can be unit-tested outside Kodi.        #
#                                                                              #
#  Each target's `setting` ('include' + key) is the id of its on/off setting   #
#  in resources/settings.xml; the order of TARGETS is the display order of     #
#  the toggles and the order of the settings in settings.xml.                  #
#                                                                              #
#  Only regenerable caches are listed. Never add state databases (Seren        #
#  providers.db, search history, sync/watched data): wipe_db empties EVERY     #
#  table of a listed file.                                                     #
################################################################################

import os
from collections import namedtuple

Target = namedtuple('Target', ['key', 'title', 'addon_id', 'dbs'])

TARGETS = (
    Target('seren', 'Seren', 'plugin.video.seren',
           ('cache.db', 'torrentCache.db', 'debridCache.db', 'providerPerf.db')),
    # Umbrella's source-results cache file is providers.db (control.providercacheFile); there is no providerscache.db.
    Target('umbrella', 'Umbrella', 'plugin.video.umbrella', ('cache.db', 'metadata.db', 'providers.db')),
    Target('pov', 'POV', 'plugin.video.pov',
           ('maincache.db', 'metacache.db', 'providerscache.db', 'debridcache.db')),
    Target('otakutesting', 'Otaku Testing', 'plugin.video.otaku.testing', ('cache.db',)),
    Target('otaku', 'Otaku', 'plugin.video.otaku', ('cache.db',)),
    # Prism (Seren fork): cache.db + prism_meta.db = its Clear Cache; torrentCache.db + debridCache.db = its Clear Torrent
    # Cache. Never providers.db (provider packs), simklSync.db, premiumize.db or skins.db.
    Target('prism', 'Prism', 'plugin.video.prism',
           ('cache.db', 'prism_meta.db', 'torrentCache.db', 'debridCache.db')),
    # Redlight (Fen family, databases live in databases/): the four cache DBs its Clear All Cache empties.
    # Its simkl/trakt/mdblist caches hold synced watched state and are left alone.
    Target('redlight', 'Redlight', 'plugin.video.redlight',
           ('databases/maincache.db', 'databases/metacache.db', 'databases/debridcache.db',
            'databases/external.db')),
    Target('tmdbhelper', 'TMDb Helper', 'plugin.video.themoviedb.helper',
           # the five caches TMDb Helper's own "Delete cache" offers (TMDb, Trakt, FanartTV, OMDb, Item Details);
           # each is a single-table cache DB. Its other databases hold sync state (TraktSync_v2, MDbListSync,
           # SimklSync, TraktEpisodes_v2) or history (search_history) and must never be listed.
           ('database_v6/TMDb.db', 'database_v6/TraktAPI.db', 'database_v6/FanartTV.db',
            'database_v6/OMDb.db', 'database_v6/ItemBuilder.db')),
    Target('diamondinfo', 'Diamond Info', 'script.diamondinfo', ('cache.db',)),
    Target('extendedinfo', 'Extended Info', 'script.extendedinfo', ('cache.db',)),
)

# Databases that are cleared by "Include All" only; they have no toggle of their own.
ALL_ONLY_DBS = (
    ('script.module.simplecache', 'simplecache.db'),
)


def addon_title(addon_id):
    """Display name for an addon folder under addon_data (falls back to the id)."""
    for t in TARGETS:
        if t.addon_id == addon_id:
            return t.title
    return {'script.module.simplecache': 'SimpleCache'}.get(addon_id, addon_id)


def setting_id(target):
    return 'include' + target.key


def toggle_ids():
    """Setting ids handled by the cache toggle, in toggle_cache() order."""
    return ['includevideo', 'includeall'] + [setting_id(t) for t in TARGETS]


def toggle_titles():
    """Display names matching toggle_ids()."""
    return ['Include Video Addons', 'Include All Addons'] + ['Include {0}'.format(t.title) for t in TARGETS]


def db_paths(addon_data, include_all, is_included):
    """Database files to clear.

    include_all   -- every registered database plus ALL_ONLY_DBS
    is_included   -- callable(setting_id) -> bool, used when include_all is False
    """
    if include_all:
        targets = TARGETS
    else:
        targets = [t for t in TARGETS if is_included(setting_id(t))]
    paths = [os.path.join(addon_data, t.addon_id, db) for t in targets for db in t.dbs]
    if include_all:
        paths += [os.path.join(addon_data, addon_id, db) for addon_id, db in ALL_ONLY_DBS]
    return paths
