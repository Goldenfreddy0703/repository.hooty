import xbmcaddon
import xbmc

properties = [
    "context.otaku.findrecommendations",
    "context.otaku.findrelations",
    "context.otaku.getwatchorder",
    "context.otaku.rescrape",
    "context.otaku.sourceselect",
    "context.otaku.logout",
    'context.otaku.deletefromdatabase',
    'context.otaku.watchlist',
    'context.otaku.markedaswatched',
    'context.otaku.fanartselect'
]

if xbmc.getCondVisibility('System.AddonIsEnabled(%s)' % 'plugin.video.otaku'):
    ADDON = xbmcaddon.Addon('plugin.video.otaku')
    for prop in properties:
        xbmc.executebuiltin(f"SetProperty({prop},{ADDON.getSetting(prop)},home)")
