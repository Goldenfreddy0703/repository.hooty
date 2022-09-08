# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmc

from tools import get_current_list_item_action_args, url_quoted_action_args

if __name__ == "__main__":
    action_args = get_current_list_item_action_args()
    action_args['media_type'] = "season"
    action_args.pop("season", None)
    action_args['trakt_id'] = action_args.get("trakt_season_id")
    action_args.pop("trakt_season_id", None)

    trakt_id = action_args.get("trakt_id")
    if trakt_id:
        path = "plugin://plugin.video.seren/?action=seasonEpisodes&action_args={}".format(
            url_quoted_action_args(action_args)
        )

        xbmc.log(
            "context.seren: Browse Season ({})".format(action_args["trakt_id"]),
            xbmc.LOGINFO,
        )
        xbmc.executebuiltin("ActivateWindow(Videos,{},return)".format(path))
    else:
        xbmc.log(
            "context.seren: Browse Season:  No trakt_season_id in action_args: ({})".format(
                get_current_list_item_action_args()
            ),
            xbmc.LOGERROR
        )
