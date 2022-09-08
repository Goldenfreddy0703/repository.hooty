# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmc

from tools import get_current_list_item_action_args, url_quoted_action_args

if __name__ == "__main__":
    action_args = get_current_list_item_action_args()
    action_args.pop("season", None)
    action_args.pop("trakt_season_id", None)
    if action_args.get("mediatype") != "tvshow":
        action_args['trakt_id'] = action_args.get("trakt_show_id")
    action_args.pop("trakt_show_id", None)
    action_args['mediatype'] = "tvshow"

    trakt_id = action_args.get("trakt_id")
    if trakt_id:
        path = "plugin://plugin.video.seren/?action=showSeasons&action_args={}".format(
            url_quoted_action_args(action_args)
        )

        xbmc.log(
            "context.seren: Browse Show ({})".format(trakt_id), xbmc.LOGINFO
        )
        xbmc.executebuiltin("ActivateWindow(Videos,{},return)".format(path))
    else:
        xbmc.log(
            "context.seren: Browse Show:  No trakt_show_id in action_args: ({})".format(
                get_current_list_item_action_args()
            ),
            xbmc.LOGERROR
        )
