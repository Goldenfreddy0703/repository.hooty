# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import xbmc

from tools import get_current_list_item_action_args, url_quoted_action_args

if __name__ == "__main__":
    action_args = get_current_list_item_action_args()

    path = "plugin://plugin.video.seren/?action=traktManager&action_args={}".format(
        url_quoted_action_args(action_args)
    )

    xbmc.log(
        "context.seren: Trakt Manager ({})".format(action_args.get("trakt_id")),
        xbmc.LOGINFO,
    )

    xbmc.executebuiltin("RunPlugin({})".format(path))
