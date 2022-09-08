# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmc

from tools import get_current_list_item_action_args

if __name__ == "__main__":
    action_args = get_current_list_item_action_args()

    trakt_id = action_args.get("trakt_id")
    if trakt_id:
        path = "plugin://plugin.video.seren/?action={}&action_args={}".format(
            "showsRelated"
            if action_args.get("mediatype") == "tvshow"
            else "moviesRelated",
            trakt_id,
        )

        xbmc.log("context.seren: Find Similar ({})".format(trakt_id), xbmc.LOGDEBUG)
        xbmc.executebuiltin("ActivateWindow(Videos,{},return)".format(path))
    else:
        xbmc.log(
            "context.seren: Find Similar:  No trakt_id in action_args: ({})".format(
                action_args
            ),
            xbmc.LOGERROR,
        )
