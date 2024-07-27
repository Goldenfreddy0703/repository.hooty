import xbmcaddon
import xbmc

properties = [
    "context.otaku.findrecommendations",
    "context.otaku.findrelations",
    "context.otaku.getwatchorder",
    "context.otaku.rescrape",
    "context.otaku.sourceselect",
    "context.otaku.watchlist",
    "context.otaku.deletefromdatabase",
    "context.otaku.logout",
    "context.otaku.markedaswatched"
]

if xbmc.getCondVisibility('System.HasAddon(%s)' % 'plugin.video.otaku'):
    ADDON = xbmcaddon.Addon('plugin.video.otaku')
    for prop in properties:
        xbmc.executebuiltin("SetProperty({},{},home)".format(prop, ADDON.getSetting(prop)))
