# -*- coding: utf-8 -*-
from resources.lib.ui import control
from resources.lib.ui import player
from resources.lib.ui import database
from resources.lib.database.searchHistory import SearchHistory
from resources.lib.ui.globals import g
from resources.lib.ui.router import on_param, route, router_process
from resources.lib.KaitoBrowser import KaitoBrowser
from resources.lib.AniListBrowser import AniListBrowser
from resources.lib.WatchlistIntegration import set_browser, add_watchlist, watchlist_update, WATCHLIST_WATCHED_UPDATE
import ast
import sys

from resources.lib.third_party import anitopy

g.init_globals(sys.argv)

MENU_ITEMS = [
    {"name": g.lang(30012), "action": "shows_next_up", "menu_item": {"art": {'poster': 'next up.png',
                                                                             'thumb': 'next up.png',
                                                                             'icon': 'next up.png'}}},
    {"name": g.lang(30001), "action": "anilist_airing", "menu_item": {"art": {'poster': 'airing anime calendar.png',
                                                                              'thumb': 'airing anime calendar.png',
                                                                              'icon': 'airing anime calendar.png'}}},
    {"name": g.lang(30002), "action": "airing_dub", "menu_item": {"art": {'poster': 'airing dubbed anime.png',
                                                                          'thumb': 'airing dubbed anime.png',
                                                                          'icon': 'airing dubbed anime.png'}}},
    {"name": g.lang(30003), "action": "latest", "menu_item": {"art": {'poster': 'latest.png',
                                                                      'thumb': 'latest.png',
                                                                      'icon': 'latest.png'}}},
    {"name": g.lang(30004), "action": "latest_dub", "menu_item": {"art": {'poster': 'latest - english dubbed.png',
                                                                          'thumb': 'latest - english dubbed.png',
                                                                          'icon': 'latest - english dubbed.png'}}},
    {"name": g.lang(30005), "action": "anilist_trending", "menu_item": {"art": {'poster': 'trending now.png',
                                                                                'thumb': 'trending now.png',
                                                                                'icon': 'trending now.png'}}},
    {"name": g.lang(30006), "action": "anilist_popular", "menu_item": {"art": {'poster': 'popular this season.png',
                                                                               'thumb': 'popular this season.png',
                                                                               'icon': 'popular this season.png'}}},
    {"name": g.lang(30007), "action": "anilist_upcoming", "menu_item": {"art": {'poster': 'upcoming next season.png',
                                                                                'thumb': 'upcoming next season.png',
                                                                                'icon': 'upcoming next season.png'}}},
    {"name": g.lang(30008), "action": "anilist_all_time_popular", "menu_item": {"art": {'poster': 'all time popular.png',
                                                                                        'thumb': 'all time popular.png',
                                                                                        'icon': 'all time popular.png'}}},
    {"name": g.lang(30009), "action": "anilist_genres", "menu_item": {"art": {'poster': 'genres & tags.png',
                                                                              'thumb': 'genres & tags.png',
                                                                              'icon': 'genres & tags.png'}}},
    {"name": g.lang(30010), "action": "search_history", "menu_item": {"art": {'poster': 'search.png',
                                                                              'thumb': 'search.png',
                                                                              'icon': 'search.png'}}},
    {"name": g.lang(30011), "action": "tools", "menu_item": {"art": {'poster': 'tools.png',
                                                                     'thumb': 'tools.png',
                                                                     'icon': 'tools.png'}}},
]

_TITLE_LANG = g.get_setting("titlelanguage")

_BROWSER = KaitoBrowser()

_ANILIST_BROWSER = AniListBrowser(_TITLE_LANG)

def _add_last_watched():
    anilist_id = g.get_setting("addon.last_watched")
    if not anilist_id:
        return

    try:
        last_watched = ast.literal_eval(database.get_show(anilist_id)['kodi_meta'])
    except:
        return

    MENU_ITEMS.insert(0, (
        "%s[I]%s[/I]" % (g.lang(30000), control.decode_py2(last_watched['name'])),
        "animes/%s/null/" % anilist_id,
        last_watched['poster']
    ))

def get_animes_contentType(seasons=None):
    contentType = g.get_setting("contenttype.episodes")
    if seasons and seasons[0]['is_dir']:
        contentType = g.get_setting("contenttype.seasons")

    return contentType

#Will be called at handle_player
def on_percent():
    return int(g.get_setting('watchlist.percent'))

#Will be called when player is stopped in the middle of the episode
def on_stopped():
    return control.yesno_dialog(g.lang(30200), g.lang(30201), g.lang(30202))

#Will be called on genre page
def genre_dialog(genre_display_list):
    return control.multiselect_dialog(g.lang(30009), genre_display_list)

@route('season_correction/*')
def seasonCorrection(payload, params):
    anilist_id, mal_id, filter_lang = payload.split("/")[1:]
    trakt = _BROWSER.search_trakt_shows(anilist_id)
    return g.draw_items(trakt)

@route('season_correction_database/*')
def seasonCorrectionDatabase(payload, params):
    show_id, meta_ids = payload.rsplit("/")
    clean_show = _BROWSER.clean_show(show_id, meta_ids)
    trakt, content_type = _BROWSER.get_anime_trakt(show_id, True)
    return g.draw_items(trakt, content_type)

@route('find_similar')
def FIND_SIMILAR(payload, params):
    action_args = params.get('action_args')
    anilist_id = action_args['anilist_id']
    _ANILIST_BROWSER.get_recommendation(anilist_id)

@route('authAllDebrid')
def authAllDebrid(payload, params):
    from resources.lib.debrid.all_debrid import AllDebrid
    AllDebrid().auth()

@route('authRealDebrid')
def authRealDebrid(payload, params):
    from resources.lib.debrid.real_debrid import RealDebrid
    RealDebrid().auth()

@route('authPremiumize')
def authPremiumize(payload, params):
    from resources.lib.debrid.premiumize import Premiumize
    Premiumize().auth()

@route('settings')
def SETTINGS(payload, params):
    return control.settingsMenu();

@route('clear_cache')
def CLEAR_CACHE(payload, params):
    g.clear_cache()

@route('clear_torrent_cache')
def CLEAR_TORRENT_CACHE(payload, params):
    return
    # return database.torrent_cache_clear()

@route('rebuild_database')
def REBUILD_DATABASE(payload, params):
        from resources.lib.database.anilist_sync import AnilistSyncDatabase

        AnilistSyncDatabase().re_build_database()
        g.clear_cache(True)

@route('wipe_addon_data')
def WIPE_ADDON_DATA(payload, params):
    from resources.lib.ui import maintenance
    maintenance.wipe_install()

@route('toggleLanguageInvoker')
def TOGGLE_LANGUAGE_INVOKER(payload, params):
    from resources.lib.ui.maintenance import toggle_reuselanguageinvoker
    toggle_reuselanguageinvoker()    

@route('show_seasons')
def SHOW_SEASONS(payload, params):
    import xbmcgui
    xbmcgui.Dialog().textviewer('dssds', str(params))

@route('show_episodes')
def SHOW_EPISODES(payload, params):
    action_args = params.get('action_args')
    _BROWSER.show_seasons(action_args)

@route('season_episodes')
def SEASON_EPISODES(payload, params):
    action_args = params.get('action_args')
    _BROWSER.season_episodes(action_args)

@route('mal_season_episodes')
def MAL_SEASON_EPISODES(payload, params):
    action_args = params.get('action_args')
    _BROWSER.mal_season_episodes(action_args)
    # mal_id = action_args['mal_id']
    # item_information = control.get_item_information_mal(45576)
    # #if not item_information:

    # import xbmcgui
    # xbmcgui.Dialog().textviewer('dsds', str(item_information))

@route('animes')
def ANIMES_PAGE(payload, params):
    anilist_id = params['action_args']['anilist_id']
    mal_id = params['action_args']['mal_id']
    filter_lang = None
    anime_general, content = _BROWSER.get_anime_init(anilist_id, filter_lang)
    return g.draw_items(anime_general, content)

@route('animes_trakt/*')
def ANIMES_TRAKT(payload, params):
    show_id, season = payload.rsplit("/")
    database._update_season(show_id, season)
    return g.draw_items(_BROWSER.get_trakt_episodes(show_id, season), 'episodes')

@route('run_player_dialogs')
def RUN_PLAYER_DIALOGS(payload, params):
    from resources.lib.ui.player import PlayerDialogs
    try:
        PlayerDialogs().display_dialog()
    except:
        import traceback
        traceback.print_exc()

@route('test')
def TEST(payload, params):
    anime = control.get_item_information(117193)
    import xbmcgui
    xbmcgui.Dialog().textviewer('dsds', str(anime))
    return

@route('shows_next_up')
def SHOWS_NEXT_UP(payload, params):
    from resources.lib.database.anilist_sync import shows
    from resources.lib.modules.list_builder import ListBuilder

    anime = shows.AnilistSyncDatabase().get_nextup_episodes()
    ListBuilder().mixed_episode_builder(anime, sort='episode', no_paging=True)

@route('anilist_airing')
def ANILIST_AIRING(payload, params):
    '''
    Anichart, need to re-add redirect to episode page
    '''
    airing = _ANILIST_BROWSER.get_airing()
    from resources.lib.windows.anichart import Anichart

    anime = Anichart(*('anichart.xml', g.ADDON_DATA_PATH),
                        get_anime=_BROWSER.get_anime_init, anime_items=airing).doModal()


    # if not anime:
    #     anime = [[], 'tvshows']

    # anime, content_type = anime

    # return g.draw_items(anime, content_type)

    return

@route('airing_dub')
def AIRING_DUB(payload, params):
    _BROWSER.get_airing_dub()

@route('latest')
def LATEST(payload, params):
    _BROWSER.get_latest(g.real_debrid_enabled(), g.premiumize_enabled())

@route('latest_dub')
def LATEST_DUB(payload, params):
    _BROWSER.get_latest_dub(g.real_debrid_enabled(), g.premiumize_enabled())

@route('anilist_trending')
def ANILIST_TRENDING(payload, params):
    if g.get_bool_setting("general.menus"):
        action_args = params.get('action_args')
        if isinstance(action_args, dict):
            g.draw_items(_ANILIST_BROWSER.get_trending(int(action_args['page'])))
        else:
            g.draw_items(_ANILIST_BROWSER.get_trending())
    else:
        _ANILIST_BROWSER.get_trending()

@route('anilist_popular')
def ANILIST_POPULAR(payload, params):
    if g.get_bool_setting("general.menus"):
        action_args = params.get('action_args')
        if isinstance(action_args, dict):
            g.draw_items(_ANILIST_BROWSER.get_popular(int(action_args['page'])))
        else:
            g.draw_items(_ANILIST_BROWSER.get_popular())

    else:
        _ANILIST_BROWSER.get_popular()

@route('anilist_upcoming')
def ANILIST_UPCOMING(payload, params):
    if g.get_bool_setting("general.menus"):
        action_args = params.get('action_args')
        if isinstance(action_args, dict):
            g.draw_items(_ANILIST_BROWSER.get_upcoming(int(action_args['page'])))
        else:
            g.draw_items(_ANILIST_BROWSER.get_upcoming())

    else:
        _ANILIST_BROWSER.get_upcoming()

@route('anilist_all_time_popular')
def ANILIST_ALL_TIME_POPULAR(payload, params):
    if g.get_bool_setting("general.menus"):
        action_args = params.get('action_args')
        if isinstance(action_args, dict):
            g.draw_items(_ANILIST_BROWSER.get_all_time_popular(int(action_args['page'])))
        else:
            g.draw_items(_ANILIST_BROWSER.get_all_time_popular())

    else:
        _ANILIST_BROWSER.get_all_time_popular()

@route('anilist_genres')
def ANILIST_GENRES(payload, params):
    _ANILIST_BROWSER.get_genres()

@route('anilist_genres_page')
def ANILIST_GENRES_PAGES(payload, params):
    genres_tags = params.get('action_args')
    _ANILIST_BROWSER.select_genres(genre_dialog, genres_tags)

@route('search_history')
def SEARCH_HISTORY(payload, params):
    history = SearchHistory().get_search_history("show")
    if "Yes" in g.get_setting('searchhistory') :
        _BROWSER.search_history(history)
    else:
        return SEARCH(payload, params)

@route('clear_history')
def CLEAR_HISTORY(payload, params):
    from resources.lib.database.searchHistory import SearchHistory
    SearchHistory().clear_search_history()

@route('search')
def SEARCH(payload, params):
    action_args = params.get('action_args')
    if isinstance(action_args, dict):
        query = action_args['query']
    else:
        query = control.keyboard(g.lang(30010))
    if not query:
        return False

    # TODO: Better logic here, maybe move functionatly into router?
    if "Yes" in g.get_setting('searchhistory'):
        SearchHistory().add_search_history("show", query)

    if g.get_bool_setting("general.menus"):
        action_args = params.get('action_args')
        if isinstance(action_args, dict):
            g.draw_items(_ANILIST_BROWSER.get_search(query, (int(action_args['page']))))
        else:
            g.draw_items(_ANILIST_BROWSER.get_search(query))
    else:
        _ANILIST_BROWSER.get_search(query)

@route('search_results')
def SEARCH_PAGES(payload, params):
    query = params.get('action_args')
    _ANILIST_BROWSER.get_search(query)

@route('play_latest')
def PLAY_LATEST(payload, params):
    action_args = params.get('action_args')
    debrid_provider = action_args["debrid_provider"]
    hash_ = action_args["hash"]
    link = _BROWSER.get_latest_sources(debrid_provider, hash_)
    player.play_source(link, action_args, None)

@route('play_movie')
def PLAY_MOVIE(payload, params):
    action_args = params.get('action_args')
    action_args["episode"] = 1
    anilist_id = action_args['anilist_id']
    # # indexer = action_args.get('indexer', 'trakt')
    sources = _BROWSER.get_sources(anilist_id, '1', "", 'movie')
    _mock_args = {"anilist_id": anilist_id}

    if g.get_setting('general.playstyle.movie') == '1' or params.get('source_select'):

        from resources.lib.windows.source_select import SourceSelect

        link = SourceSelect(*('source_select.xml', g.ADDON_DATA_PATH),
                            actionArgs=_mock_args, sources=sources).doModal()
    else:
        from resources.lib.windows.resolver import Resolver

        resolver = Resolver(*('resolver.xml', g.ADDON_DATA_PATH),
                            actionArgs=_mock_args)

        link = resolver.doModal(sources, {}, False)

    # player.play_source(link,
    #                     anilist_id,
    #                     watchlist_update,
    #                     None,
    #                     int(action_args["episode"]),
    #                     "",
    #                     indexer=indexer)
    player.play_source(link, action_args, watchlist_update)

@route('play_gogo')
def PLAY_GOGO(payload, params):
    action_args = params.get('action_args')
    slug = action_args["slug"]
    episode = action_args["_episode"]
    from resources.lib.pages import gogoanime
    sources = gogoanime.sources()._process_gogo(slug, '', episode)

    _mock_args = {}
    from resources.lib.windows.source_select import SourceSelect

    link = SourceSelect(*('source_select.xml', g.ADDON_DATA_PATH),
                        actionArgs=_mock_args, sources=sources).doModal()

    player.play_source(link, action_args, None)

@route('get_sources')
def GET_SOURCES(payload, params):
    action_args = params.get('action_args')
    anilist_id = action_args['anilist_id']
    # # indexer = action_args.get('indexer', 'trakt')
    sources = _BROWSER.get_sources(anilist_id, action_args["episode"], "", 'show')
    _mock_args = {"anilist_id": anilist_id}

    if g.get_setting('general.playstyle.episode') == '1' or params.get('source_select'):

        from resources.lib.windows.source_select import SourceSelect

        link = SourceSelect(*('source_select.xml', g.ADDON_DATA_PATH),
                            actionArgs=_mock_args, sources=sources).doModal()
    else:
        from resources.lib.windows.resolver import Resolver

        resolver = Resolver(*('resolver.xml', g.ADDON_DATA_PATH),
                            actionArgs=_mock_args)

        link = resolver.doModal(sources, {}, False)

    # player.play_source(link,
    #                     anilist_id,
    #                     watchlist_update,
    #                     None,
    #                     int(action_args["episode"]),
    #                     "",
    #                     indexer=indexer)
    player.play_source(link, action_args, watchlist_update)

@route('play')
def PLAY(payload, params):
    action_args = params.get('action_args')
    anilist_id = params['action_args']['anilist_id']
    episode = params['action_args']['episode']
    sources = _BROWSER.get_sources(anilist_id, episode, "", 'show')
    _mock_args = {"anilist_id": anilist_id}

    if g.get_setting('general.playstyle.episode') == '1' or params.get('source_select'):

        from resources.lib.windows.source_select import SourceSelect

        link = SourceSelect(*('source_select.xml', g.ADDON_DATA_PATH),
                            actionArgs=_mock_args, sources=sources).doModal()
    else:
        from resources.lib.windows.resolver import Resolver

        resolver = Resolver(*('resolver.xml', g.ADDON_DATA_PATH),
                            actionArgs=_mock_args)

        link = resolver.doModal(sources, {}, False)

    player.play_source(link, action_args, watchlist_update)

@route('rescrape_play/*')
def RESCRAPE_PLAY(payload, params):
    anilist_id, episode, filter_lang = payload.rsplit("/")
    sources = _BROWSER.get_sources(anilist_id, episode, filter_lang, 'show', True)
    _mock_args = {"anilist_id": anilist_id}

    from resources.lib.windows.source_select import SourceSelect

    link = SourceSelect(*('source_select.xml', g.ADDON_DATA_PATH),
                        actionArgs=_mock_args, sources=sources, anilist_id=anilist_id, rescrape=True).doModal()

    player.play_source(link,
                        anilist_id,
                        watchlist_update,
                        _BROWSER.get_episodeList,
                        int(episode),
                        filter_lang,
                        rescrape=True)

@route('tmdb_helper')
def TMDB_HELPER(payload, params):
    from resources.lib.indexers.anilist import AnilistAPI
    from resources.lib.indexers.trakt import TRAKTAPI
    trakt_show_name = params['title']
    source_select = params['sourceselect']
    action_args = ast.literal_eval(params.get('actionArgs'))
    media_type = action_args['item_type']
    trakt_id = action_args['trakt_id']
    season = action_args.get('season', None)
    episode = action_args.get('episode', 1)
    if not trakt_show_name:
        trakt_show = TRAKTAPI().get_trakt_show(trakt_id, media_type)
        trakt_show_name = trakt_show['title']
    if not media_type == 'movie':
        if int(season) > 1 and not trakt_show_name.lower() == 'one piece' and not trakt_show_name.lower() == 'case closed':
            trakt_show_name += " season " + str(season)
    if 'attack on titan' == trakt_show_name.lower():
        if int(season) == 4:
            if int(episode) <= 16:
                trakt_show_name = 'attack on titan final season'
            elif int(episode) <= 28:
                trakt_show_name = 'attack on titan final season part 2'
            elif int(episode) > 28:
                trakt_show_name = 'attack on titan final season part 3'
    params = {}
    params['dict_key'] = ('data', 'Page', 'media')
    params['query_path'] = 'search/anime'
    params['variables'] = {'page': 1,
                           'search': trakt_show_name,
                           'sort': 'SEARCH_MATCH',
                           'type': 'ANIME'}
    result, page = AnilistAPI().post_json(AnilistAPI._URL, **params)
    top_result = result[0]
    if not top_result['anilist_object']['info']['mediatype'] == media_type:
        for x in result:
            if x['anilist_object']['info']['mediatype'] == media_type:
                top_result = x
                break
    if media_type == 'movie':
        pars = {}
        pars['action_args'] = {'anilist_id': top_result['anilist_id'], 'mediatype': media_type}
        if source_select == 'true':
            pars['source_select'] = 'true'
        PLAY_MOVIE('', pars)
    else:
        if ("part" in top_result['anilist_object']['info']['title'].lower() or "part" in result[1]['anilist_object']['info']['title'].lower()) and not 'attack on titan' == trakt_show_name.lower():
            import xbmcgui
            if xbmcgui.Dialog().yesno('Anime Season', "Is this season split into parts AND is this episode in the second part? \nIf you do not know, please look up your anime and season on anilist.co, myanimelist.net, or kitsu.io"):
                params['variables']['search'] = trakt_show_name + " part 2"
                params['dict_key'] = ('data', 'Page', 'media')
                params['query_path'] = 'search/anime'
                refetched_anilist, op = AnilistAPI().post_json(AnilistAPI._URL, **params)
                pars = {}
                pars['action_args'] = {'anilist_id': refetched_anilist[0]['anilist_id'], 'episode': episode, 'mediatype': media_type}
                if source_select == 'true':
                    pars['source_select'] = 'true'
                GET_SOURCES('', pars)

            else:
                pars = {}
                pars['action_args'] = {'anilist_id': top_result['anilist_id'], 'episode': episode, 'mediatype': media_type}
                if source_select == 'true':
                    pars['source_select'] = 'true'
                GET_SOURCES('', pars)
        else:
            pars = {}
            if source_select == 'true':
                pars['source_select'] = 'true'
            pars['action_args'] = {'anilist_id': top_result['anilist_id'], 'episode': episode, 'mediatype': media_type}
            GET_SOURCES('', pars)

@route('tools')
def TOOLS_MENU(payload, params):
    TOOLS_ITEMS = [
        (g.lang(30020), "settings", {"art": {'poster': 'open settings menu.png',
                                             'thumb': 'open settings menu.png',
                                             'icon': 'open settings menu.png'}}),
        (g.lang(30021), "clear_cache", {"art": {'poster': 'clear cache.png',
                                                'thumb': 'clear cache.png',
                                                'icon': 'clear cache.png'}}),
        (g.lang(30022), "clear_torrent_cache", {"art": {'poster': 'clear local torrent cache.png',
                                                        'thumb': 'clear local torrent cache.png',
                                                        'icon': 'clear local torrent cache.png'}}),
        (g.lang(30023), "clear_history", {"art": {'poster': 'clear search history.png',
                                                  'thumb': 'clear search history.png',
                                                  'icon': 'clear search history.png'}}),
        (g.lang(30026), "rebuild_database", {"art": {'poster': 'rebuild database.png',
                                                     'thumb': 'rebuild database.png',
                                                     'icon': 'rebuild database.png'}}),
        (g.lang(30024), "wipe_addon_data", {"art": {'poster': 'wipe addon data.png',
                                                    'thumb': 'wipe addon data.png',
                                                    'icon': 'wipe addon data.png'}}),
    ]

    for name, url, image in TOOLS_ITEMS:
        g.add_directory_item(
            name,
            action=url,
            menu_item=image,
            is_folder=False
        )
    g.close_directory(g.CONTENT_MENU)

@route('')
def LIST_MENU(payload, params):
    for item in MENU_ITEMS:
        g.add_directory_item(
            item.get("name"),
            action=item.get("action"),
            action_args=item.get("args"),
            menu_item=item.get("menu_item"),
        )
    g.close_directory(g.CONTENT_MENU)
    # return g.draw_items(
    #     [g.allocate_item(name, url, True, image) for name, url, image in MENU_ITEMS],
    #     contentType=g.get_setting("contenttype.menu"),
    # )


set_browser(_BROWSER)
_add_last_watched()
add_watchlist(MENU_ITEMS)
router_process(g.PATH[1:], g.REQUEST_PARAMS)
if g.PARAM_STRING == '':
    WATCHLIST_WATCHED_UPDATE('', {'modal': 'false'})
