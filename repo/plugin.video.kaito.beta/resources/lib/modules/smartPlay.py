# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

import random
import sys

import xbmc
import xbmcgui

from resources.lib.ui.globals import g
from resources.lib.ui import control
from resources.lib.modules.list_builder import ListBuilder


class SmartPlay:
    """
    Provides smart operations for playback
    """
    def __init__(self, item_information):
        self.list_builder = ListBuilder()
        # if "info" not in item_information:
        #     item_information = tools.get_item_information(item_information)
        self.item_information = item_information

        # if not isinstance(self.item_information, dict):
        #     raise TypeError("Item Information is not a dictionary")

        # self.show_trakt_id = self.item_information.get("trakt_show_id")
        # if not self.show_trakt_id and "action_args" in self.item_information:
        #     self.show_trakt_id = self._extract_show_id_from_args(
        #         self.item_information["action_args"]
        #     )

        # self.display_style = g.get_int_setting("smartplay.displaystyle")
        # self.trakt_api = TraktAPI()

    def build_playlist(self, season_id=None, minimum_episode=None):
        """
        Uses available information to add relevant episodes to the current playlist
        :param season_id: Trakt ID of season to build
        :type season_id: int
        :param minimum_episode: Minimum episodes to add from
        :type minimum_episode: int
        :return:
        :rtype:
        """
        # if season_id is None:
        #     season_id = self.item_information["info"]["trakt_season_id"]

        # if minimum_episode is None:
        #     minimum_episode = int(self.item_information["info"]["episode"]) + 1

        minimum_episode = int(self.item_information["episode"]) + 1

        anilist_id = self.item_information['anilist_id']
        indexer = self.item_information.get('indexer', 'trakt')
        _item_information = control.get_item_information(anilist_id)
        simkl_id = _item_information["simkl_id"]
        trakt_id = _item_information["trakt_id"]
        tmdb_id = _item_information["tmdb_id"]

        try:
            if indexer == 'trakt':
                episodes = self.list_builder.episode_list_builder(
                    anilist_id,
                    trakt_id,
                    minimum_episode=minimum_episode,
                    smart_play=True,
                    hide_unaired=True,
                    no_paging=True,
                )
            elif indexer == 'tmdb':
                episodes = self.list_builder.episode_alt_list_builder(
                    anilist_id,
                    minimum_episode=minimum_episode,
                    smart_play=True,
                    hide_unaired=True,
                    no_paging=True,
                )
            elif indexer == 'simkl':
                episodes = self.list_builder.episode_alt_list_builder(
                    anilist_id,
                    minimum_episode=minimum_episode,
                    smart_play=True,
                    hide_unaired=True,
                    no_paging=True,
                )

            [
                g.PLAYLIST.add(url=i[0], listitem=i[1])
                for i in episodes
            ]
        except TypeError:
            g.log(
                "Unable to add more episodes to the playlist, they may not be available for the requested season",
                "warning",
            )
            return