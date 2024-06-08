import time

from resources.lib.ui import control, database
from resources.lib.WatchlistFlavor import WatchlistFlavor


def refresh_apis():
    rd_token = control.getSetting('rd.auth')
    dl_token = control.getSetting('dl.auth')
    kitsu_token = control.getSetting('kitsu.token')
    mal_token = control.getSetting('mal.token')

    try:
        if rd_token != '':
            rd_expiry = int(float(control.getSetting('rd.expiry')))
            if time.time() > (rd_expiry - (10 * 60)):
                from resources.lib.debrid import real_debrid
                real_debrid.RealDebrid().refreshToken()
    except:
        pass

    try:
        if dl_token != '':
            dl_expiry = int(float(control.getSetting('dl.expiry')))
            if time.time() > (dl_expiry - (10 * 60)):
                from resources.lib.debrid import debrid_link
                debrid_link.DebridLink().refreshToken()
    except:
        pass

    try:
        if kitsu_token != '':
            kitsu_expiry = int(float(control.getSetting('kitsu.expiry')))
            if time.time() > (kitsu_expiry - (10 * 60)):
                from resources.lib.WatchlistFlavor import Kitsu
                Kitsu.KitsuWLF().refresh_token()
    except:
        pass

    try:
        if mal_token != '':
            mal_expiry = int(float(control.getSetting('mal.expiry')))
            if time.time() > (mal_expiry - (10 * 60)):
                from resources.lib.WatchlistFlavor import MyAnimeList
                MyAnimeList.MyAnimeListWLF().refresh_token()
    except:
        pass


def sync_watchlist():

    flavor = WatchlistFlavor.get_update_flavor()
    if flavor and control.getSetting('watchlist.player') == 'true':
        control.setSetting('watchlist.player', 'false')
        flavor.save_completed()
    elif flavor:
        flavor.save_completed()
        control.notify(control.ADDON_NAME, 'Completed Sync [B]{}[/B]'.format(flavor.flavor_name))
    else:
        control.ok_dialog(control.ADDON_NAME, "No Watchlist Enabled or Not Logged In")


def run_maintenance():

    # tools.log('Performing Maintenance')
    # ADD COMMON HOUSE KEEPING ITEMS HERE #

    # Refresh API tokens
    refresh_apis()

    # Sync Watchlist
    if control.getSetting('update.time') == '' or time.time() > int(control.getSetting('update.time')) + 2_592_000:
        flavor = WatchlistFlavor.get_update_flavor()
        if flavor:
            flavor.save_completed()

    # Setup Search Database
    database.build_searchdb()
