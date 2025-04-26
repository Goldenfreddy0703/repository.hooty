# -*- coding: utf-8 -*-

import xbmcgui

from resources.lib import Main
from resources.lib.ui import control
from resources.lib.windows.anichart_window import BaseWindow
from resources.lib import OtakuBrowser, WatchlistIntegration

BROWSER = OtakuBrowser.BROWSER


class Anichart(BaseWindow):

    def __init__(self, xml_file, location, get_anime=None, anime_items=None, calendar=None):
        super().__init__(xml_file, location)
        self.get_anime = get_anime
        self.anime_items = anime_items
        self.position = -1
        self.display_list = None
        self.last_action_time = 0
        self.anime_path = ''
        self.anime_items = calendar if calendar is not None else anime_items

    def onInit(self):
        self.display_list = self.getControl(1000)
        menu_items = []

        for idx, i in enumerate(self.anime_items):
            if not i:
                continue

            menu_item = control.menuItem(label='%s' % i['release_title'])
            for info in list(i.keys()):
                try:
                    value = i[info]
                    if isinstance(value, list):
                        value = [str(k) for k in value]
                        value = ' '.join(sorted(value))
                    menu_item.setProperty(info, str(value).replace('_', ' '))
                except UnicodeEncodeError:
                    menu_item.setProperty(info, i[info])

            menu_items.append(menu_item)
            self.display_list.addItem(menu_item)

        self.setFocusId(1000)

    def doModal(self):
        super().doModal()
        return self.anime_path

    def onDoubleClick(self, controlId):
        # immediate activate on double-click
        self.handle_action(controlId)

    def onAction(self, action):
        actionID = action.getId()
        # back navigation
        if actionID in [xbmcgui.ACTION_NAV_BACK,
                        xbmcgui.ACTION_BACKSPACE,
                        xbmcgui.ACTION_PREVIOUS_MENU]:
            self.close()
        # single-click activate
        elif actionID == xbmcgui.ACTION_SELECT_ITEM:
            self.handle_action(actionID)

        # rest of your existing context‐menu code…
        if actionID == 117:
            context_menu_options = []
            if control.getBool('context.otaku.testing.findrecommendations'):
                context_menu_options.append("Find Recommendations")
            if control.getBool('context.otaku.testing.findrelations'):
                context_menu_options.append("Find Relations")
            if control.getBool('context.otaku.testing.getwatchorder'):
                context_menu_options.append("Get Watch Order")
            if control.getBool('context.otaku.testing.deletefromdatabase'):
                context_menu_options.append("Delete From Database")
            if control.getBool('context.otaku.testing.watchlist'):
                context_menu_options.append("WatchList Manager")

            context = control.context_menu(context_menu_options)
            # if user cancels (context == -1), just return
            if context < 0:
                return

            self.position = self.display_list.getSelectedPosition()
            anime = self.anime_items[self.position]['id']
            page = 1

            choice = context_menu_options[context]
            if choice == "Find Recommendations":
                control.draw_items(BROWSER.get_recommendations(anime, page), 'tvshows')
                self.close()
            elif choice == "Find Relations":
                control.draw_items(BROWSER.get_relations(anime), 'tvshows')
                self.close()
            elif choice == "Get Watch Order":
                control.draw_items(BROWSER.get_watch_order(anime), 'tvshows')
                self.close()
            elif choice == "Delete From Database":
                payload = f"some_path/{anime}/0"
                params = {}
                Main.DELETE_ANIME_DATABASE(payload, params)
            elif choice == "WatchList Manager":
                payload = f"some_path/{anime}/0"
                params = {}
                WatchlistIntegration.CONTEXT_MENU(payload, params)

    def handle_action(self, actionID) -> None:
        # only act when focus is on our list
        if self.getFocusId() != 1000:
            return

        self.position = self.display_list.getSelectedPosition()
        anime = self.anime_items[self.position]['id']
        url = f"animes/{anime}/"
        self.anime_path = control.addon_url(url)


        new_payload, new_params = control.get_payload_params(self.anime_path)
        if 'animes/' in new_payload:
            control.progressDialog.create(control.ADDON_NAME, "Loading..")
            try:
                x = new_payload.split('animes/', 1)[1]
                Main.ANIMES_PAGE(x, new_params)
            finally:
                control.progressDialog.close()
        elif 'airing_calendar' in new_payload:
            Main.AIRING_CALENDAR(new_payload.rsplit('airing_calendar', 0)[0], new_params)
        self.close()
