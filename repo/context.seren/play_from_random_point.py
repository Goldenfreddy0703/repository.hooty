# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmc

from tools import (
    get_current_list_item_path,
    get_current_list_item_action_args,
    action_replace,
)

if __name__ == "__main__":
    action_args = get_current_list_item_action_args()
    path = get_current_list_item_path()
    path = action_replace(
        path,
        {
            "showSeasons": "playFromRandomPoint",
            "smartPlay": "playFromRandomPoint",
            "flatEpisodes": "playFromRandomPoint",
            "playbackResume": "playFromRandomPoint",
        },
    )

    xbmc.log(
        "context.seren: Play from Random Episode ({})".format(action_args["trakt_id"]),
        xbmc.LOGINFO,
    )
    xbmc.executebuiltin("RunPlugin({})".format(path))
