import xbmcaddon
import xbmc

properties = [
    "context.otaku.testing.findrecommendations",
    "context.otaku.testing.findrelations",
    "context.otaku.testing.getwatchorder",
    "context.otaku.testing.rescrape",
    "context.otaku.testing.sourceselect",
    "context.otaku.testing.logout",
    'context.otaku.testing.deletefromdatabase',
    'context.otaku.testing.watchlist',
    'context.otaku.testing.markedaswatched',
    'context.otaku.testing.fanartselect'
]

if xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % 'plugin.video.otaku.testing'):
    ADDON = xbmcaddon.Addon('plugin.video.otaku.testing')
    for prop in properties:
        xbmc.executebuiltin(f"SetProperty({prop},{ADDON.getSetting(prop)},home)")
