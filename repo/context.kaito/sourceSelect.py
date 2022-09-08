import sys
import xbmc

if __name__ == '__main__':
    item = sys.listitem
    message = item.getLabel()
    path = item.getPath()

    matches = ['play/', 'play_movie', 'play_gogo', 'get_sources']

    if any(x in path for x in matches):
        path = path + '&source_select=true'

    xbmc.executebuiltin('PlayMedia(%s)' % path)
