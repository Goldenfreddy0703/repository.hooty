import sys, xbmc
import urllib.parse
import json

if __name__ == '__main__':

    item = sys.listitem

    path = item.getPath()
    plugin = 'plugin://plugin.video.kaito/'
    path = path.split(plugin, 1)[1]
    params = urllib.parse.parse_qs(path.lstrip('?/'))
    action_args = params['action_args'][0]
    action_args = json.loads(urllib.parse.unquote(action_args))
    anilist_id = action_args['anilist_id']
    action_path = "plugin://plugin.video.kaito?action=find_similar&action_args=%s" % params['action_args'][0]

    xbmc.executebuiltin('ActivateWindow(Videos,%s,return)'
                        % action_path)
