import sys
import xbmc

if __name__ == '__main__':

    item = sys.listitem

    path = item.getPath()
    plugin = 'plugin://plugin.video.otaku'
    path = path.split(plugin, 1)[1]
    path = path.rsplit('/')[-1]

    xbmc.executebuiltin('RunPlugin("%s/watchlist_logout/%s")' % (plugin, path))
