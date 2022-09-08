# -*- coding: utf-8 -*-
from __future__ import absolute_import
import ast
from resources.lib.ui.globals import g
from .ui.router import route
from .WatchlistFlavor import WatchlistFlavor
from .ui import database
from resources.lib.database.anilist_sync import shows
import xbmcgui

_BROWSER = None
def set_browser(browser):
    global _BROWSER
    _BROWSER = browser

def get_anilist_res(mal_id):
    title_lang = g.get_setting("titlelanguage")
    from .AniListBrowser import AniListBrowser
    return AniListBrowser(title_lang).get_mal_to_anilist(mal_id)

def get_auth_dialog(flavor):
    import sys
    from resources.lib.windows import wlf_auth

    platform = sys.platform

    if 'linux' in platform:
        auth = wlf_auth.AltWatchlistFlavorAuth(flavor).set_settings()
    else:
        auth = wlf_auth.WatchlistFlavorAuth(*('wlf_auth_%s.xml' % flavor, g.ADDON_DATA_PATH),
                                        flavor=flavor).doModal()

    if auth:
        return WatchlistFlavor.login_request(flavor)
    else:
        return

@route('watchlist_login_anilist')
def WL_LOGIN_ANILIST(payload, params):
    return get_auth_dialog("anilist")

@route('watchlist_login_mal')
def WL_LOGIN_MAL(payload, params):
    return get_auth_dialog("mal")

@route('watchlist_login_kitsu')
def WL_LOGIN_KITSU(payload, params):
    return WatchlistFlavor.login_request("kitsu")

@route('watchlist_login')
def WL_LOGIN(payload, params):
    import xbmcgui
    xbmcgui.Dialog().textviewer('dsds', str(params))

    # if params:
    #     return get_auth_dialog(payload)
        
    # return WatchlistFlavor.login_request(payload)

@route('watchlist_logout')
def WL_LOGOUT(payload, params):
    action_args = params.get('action_args')
    flavor = action_args["flavor"]
    return WatchlistFlavor.logout_request(flavor)

@route('watchlist')
def WATCHLIST(payload, params):
    flavor = params.get("action_args")["flavor"]
    WatchlistFlavor.watchlist_request(flavor)

@route('watchlist_status_type')
def WATCHLIST_STATUS_TYPE(payload, params):
    action_args = params.get('action_args')
    flavor = action_args["flavor"]
    status = action_args["status"]
    WatchlistFlavor.watchlist_status_request(flavor, status)

@route('watchlist_status_type_pages')
def WATCHLIST_STATUS_TYPE_PAGES(payload, params):
    action_args = params.get('action_args')
    flavor = action_args["flavor"]
    status = action_args["status"]
    offset = action_args["offset"]
    page = action_args["page"]
    WatchlistFlavor.watchlist_status_request_pages(flavor, status, offset, int(page))

@route('watchlist_watched_update')
def WATCHLIST_WATCHED_UPDATE(payload, params):
    flavor = g.watchlist_to_update()
    if flavor:
        if flavor.lower() == 'mal':
            watchlist_data = WatchlistFlavor.get_watchlist(flavor)
            anime_list_key = ('data', 'Page', 'media')
            id_watched = {}
            variables = {
                'page': g.PAGE,
                'idMal': []
            }
            for x in watchlist_data['data']:
                variables['idMal'].append(x['node']['id'])
                id_watched[str(x['node']['id'])] = x['list_status']['num_episodes_watched']
            shows.AnilistSyncDatabase().extract_trakt_page(
                "https://graphql.anilist.co", query_path="anime/specificidmal", variables=variables, dict_key=anime_list_key, page=1, cached=0
            )
            for x in id_watched:
                if int(id_watched[x]) > 0:
                    database.add_mapping_id_mal(int(x), 'watched_episodes', int(id_watched[x]))
                    if database.get_show_mal(int(x)) is not None:
                        database.mark_episodes_watched(database.get_show_mal(int(x))['anilist_id'], 1, 1, int(id_watched[x]))
                        database.mark_episodes_watched(database.get_show_mal(int(x))['anilist_id'], 0, int(id_watched[x]) + 1, 1000)
            if params['modal'] == 'true':
                ok = xbmcgui.Dialog().ok("Updated Watchlist", "Show/Episode Markers Updated")
        elif flavor.lower() == 'anilist':
            watchlist_data = WatchlistFlavor.get_watchlist(flavor)
            id_watched = {}
            anime_list_key = ('data', 'Page', 'media')
            variables = {
                'page': g.PAGE,
                'id': []
            }
            for x in watchlist_data:
                for y in x:
                    for z in x[y]:
                        id_watched[z["media"]["id"]] = z["progress"]
                        variables['id'].append(z["media"]["id"])
            shows.AnilistSyncDatabase().extract_trakt_page(
                "https://graphql.anilist.co", query_path="anime/specificidani", variables=variables, dict_key=anime_list_key, page=1, cached=0
            )

            for x in id_watched:
                if id_watched[x] > 0:
                    database.add_mapping_id(int(x), 'watched_episodes', id_watched[x])
                    database.mark_episodes_watched(int(x), 1, 1, id_watched[x])
                    database.mark_episodes_watched(int(x), 0, id_watched[x] + 1, 1000)
            if params['modal'] == 'true':
                ok = xbmcgui.Dialog().ok("Updated Watchlist", "Show/Episode Markers Updated")
        elif flavor.lower() == 'kitsu':
            mappings, watched_eps = WatchlistFlavor.get_watchlist(flavor)
            anime_list_key = ('data', 'Page', 'media')
            variables = {
                'page': g.PAGE,
                'idMal': list(mappings.values())
            }
            shows.AnilistSyncDatabase().extract_trakt_page(
                "https://graphql.anilist.co", query_path="anime/specificidmal", variables=variables, dict_key=anime_list_key, page=1, cached=0
            )
            for x in watched_eps:
                if int(watched_eps[x]) > 0:
                    database.add_mapping_id_mal(int(mappings[x]), 'watched_episodes', int(watched_eps[x]))
                    database.mark_episodes_watched(database.get_show_mal(int(mappings[x]))['anilist_id'], 1, 1, int(watched_eps[x]))
                    database.mark_episodes_watched(database.get_show_mal(int(mappings[x]))['anilist_id'], 0, int(watched_eps[x]) + 1, 1000)
            if params['modal'] == 'true':
                ok = xbmcgui.Dialog().ok("Updated Watchlist", "Show/Episode Markers Updated")

        else:
            ok = xbmcgui.Dialog().ok("Updated Watchlist", "Watchlist Not Supported")

@route('watchlist_query/*')
def WATCHLIST_QUERY(payload, params):
    anilist_id, mal_id, eps_watched = payload.rsplit("/")
    show_meta = database.get_show(anilist_id)

    if not show_meta:
        from .AniListBrowser import AniListBrowser
        show_meta = AniListBrowser().get_anilist(anilist_id)

    kodi_meta = ast.literal_eval(show_meta['kodi_meta'])
    kodi_meta['eps_watched'] = eps_watched
    database.update_kodi_meta(anilist_id, kodi_meta)

    anime_general, content_type = _BROWSER.get_anime_init(anilist_id)
    return g.draw_items(anime_general, content_type)

@route('watchlist_to_ep/*')
def WATCHLIST_TO_EP(payload, params):
    mal_id, kitsu_id, eps_watched = payload.rsplit("/")

    if not mal_id:
        return []

    show_meta = database.get_show_mal(mal_id)

    if not show_meta:
        show_meta = get_anilist_res(mal_id)

    anilist_id = show_meta['anilist_id']
    kodi_meta = ast.literal_eval(show_meta['kodi_meta'])
    kodi_meta['eps_watched'] = eps_watched
    database.update_kodi_meta(anilist_id, kodi_meta)

    if kitsu_id:
        if not show_meta['kitsu_id']:
            database.add_mapping_id(anilist_id, 'kitsu_id', kitsu_id)

    anime_general, content_type = _BROWSER.get_anime_init(anilist_id)
    return g.draw_items(anime_general, content_type)

@route('watchlist_to_movie/*')
def WATCHLIST_QUERY(payload, params):
    if params:
        anilist_id = params['anilist_id']
        show_meta = database.get_show(anilist_id)

        if not show_meta:
            from .AniListBrowser import AniListBrowser
            show_meta = AniListBrowser().get_anilist(anilist_id)
    else:
        mal_id = payload
        show_meta = database.get_show_mal(mal_id)

        if not show_meta:
            show_meta = get_anilist_res(mal_id)

        anilist_id = show_meta['anilist_id']

    sources = _BROWSER.get_sources(anilist_id, '1', None, 'movie')
    _mock_args = {'anilist_id': anilist_id}
    from resources.lib.windows.source_select import SourceSelect

    link = SourceSelect(*('source_select.xml', g.ADDON_DATA_PATH),
                        actionArgs=_mock_args, sources=sources).doModal()

    from .ui import player

    player.play_source(link)

def watchlist_update(anilist_id, episode):
    flavor = WatchlistFlavor.get_update_flavor()
    if not flavor:
        return

    return WatchlistFlavor.watchlist_update_request(anilist_id, episode)

def add_watchlist(items):
    flavors = WatchlistFlavor.get_enabled_watchlists()
    if not flavors:
        return

    for flavor in flavors:
        items.insert(0, {
            "name": "%s's %s" % (flavor.username, flavor.title),
            "action": "watchlist",
            "args": {"flavor": flavor.flavor_name},
            "menu_item": {"art": {"poster": flavor.image,
                                  "thumb": flavor.image,
                                  "icon": flavor.image}},
        })
