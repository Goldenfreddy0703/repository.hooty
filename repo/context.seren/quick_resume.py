# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmc

from tools import (
    get_current_list_item_path,
    get_current_list_item_action_args,
    action_replace,
)

if __name__ == "__main__":
    path = get_current_list_item_path()
    path = action_replace(
        path,
        {
            "showSeasons": "forceResumeShow",
            "flatEpisodes": "forceResumeShow",
        },
    )

    action_args = get_current_list_item_action_args()
    xbmc.log(
        "context.seren: Quick Resume Show ({})".format(action_args.get("trakt_id")),
        xbmc.LOGDEBUG,
    )
    xbmc.executebuiltin("RunPlugin({})".format(path))
