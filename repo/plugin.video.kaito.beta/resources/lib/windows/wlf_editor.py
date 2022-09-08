# -*- coding: utf-8 -*-

from builtins import str
import time
from resources.lib.ui.globals import g
from resources.lib.windows.base_window import BaseWindow
from resources.lib.windows.resolver import Resolver
from resources.lib.WatchlistFlavor import WatchlistFlavor
from resources.lib.ui import database
import xbmcgui

class WatchlistFlavorEditor(BaseWindow):

    def __init__(self, xml_file, location, actionArgs=None, sources=None, anilist_id=None, rescrape=None, **kwargs):
        super(WatchlistFlavorEditor, self).__init__(xml_file, location, actionArgs=actionArgs)
        self.actionArgs = actionArgs
        self.sources = sources
        self.anilist_id = anilist_id
        self.rescrape = rescrape
        self.position = -1
        self.canceled = False
        self.anime_list_entry = {}
        self.editor_list = None
        self.flavors_list = None
        self.anime_item = None
        self.status = None
        self.eps_watched = None
        self.score = None
        self.last_action = 0
        g.close_busy_dialog()

    def onInit(self):
        self.editor_list = self.getControl(2001)
        self.flavors_list = self.getControl(2000)

        if g.anilist_enabled():
            menu_item = xbmcgui.ListItem(label='%s' % 'AniList')
            menu_item.setProperty('username', g.get_setting('anilist.username'))
            self.flavors_list.addItem(menu_item)

            self.anime_list_entry['anilist'] = WatchlistFlavor.watchlist_anime_entry_request('anilist', 235)

        if g.kitsu_enabled():
            menu_item = xbmcgui.ListItem(label='%s' % 'Kitsu')
            menu_item.setProperty('username', g.get_setting('kitsu.username'))
            self.flavors_list.addItem(menu_item)

            self.anime_list_entry['kitsu'] = WatchlistFlavor.watchlist_anime_entry_request('kitsu', 235)

        if g.myanimelist_enabled():
            menu_item = xbmcgui.ListItem(label='%s' % 'MAL')
            menu_item.setProperty('username', g.get_setting('mal.username'))
            self.flavors_list.addItem(menu_item)

            self.anime_list_entry['mal'] = WatchlistFlavor.watchlist_anime_entry_request('mal', 235)

        selected_flavor_item = self.flavors_list.getSelectedItem()
        self.selected_flavor = (selected_flavor_item.getLabel()).lower()
        for _id, value in list(self.anime_list_entry[self.selected_flavor].items()):
            item = xbmcgui.ListItem(label='%s' % _id)
            item.setProperty(_id, str(value))
            self.editor_list.addItem(item)

        self.setFocusId(2000)

    def doModal(self):
        super(WatchlistFlavorEditor, self).doModal()
        self.clearProperties()
        return
  
    def flip_flavor(self):
        self.editor_list.reset()
        selected_flavor_item = self.flavors_list.getSelectedItem()
        self.selected_flavor = (selected_flavor_item.getLabel()).lower()
        for _id, value in list(self.anime_list_entry[self.selected_flavor].items()):
            item = xbmcgui.ListItem(label='%s' % _id)
            item.setProperty(_id, str(value))
            self.editor_list.addItem(item)

    def edit_anime(self):
        self.anime_item = self.editor_list.getSelectedItem()
        self.status = self.anime_item.getProperty('status')
        self.eps_watched = self.anime_item.getProperty('eps_watched')
        self.score = self.anime_item.getProperty('score')

        if self.status:
            self.flip_status()

        if self.eps_watched:
            self.edit_eps_watched()

        if self.score:
            self.flip_score()

    def flip_status(self):
        status_dict = {
            'anilist': {
                'Planning': 'Current',
                'Current': 'Completed',
                'Completed': 'Rewatching',
                'Rewatching': 'Paused',
                'Paused': 'Dropped',
                'Dropped': 'Planning'
                },
            'kitsu': {
                'Planned': 'Current',
                'Current': 'Completed',
                'Completed': 'On_Hold',
                'On_Hold': 'Dropped',
                'Dropped': 'Planned'
            },
            'myanimelist': {
                'Plan_To_Watch': 'Watching',
                'Watching': 'Completed',
                'Completed': 'On_Hold',
                'On_Hold': 'Dropped',
                'Dropped': 'Plan_To_Watch'
                }
            }

##        if status == 'Plan to Watch':
##            new_status = 'Watching'
##
##        if status == 'Watching':
##            new_status = 'Completed'
##
##        if status == 'Completed':
##            new_status = 'On-Hold'
##
##        if status =='On-Hold':
##            new_status = 'Dropped'
##
##        if status == 'Dropped':
##            new_status = 'Plan to Watch'

        try:
            new_status = status_dict[self.selected_flavor][self.status]
            self.anime_item.setProperty('status', new_status)
            self.status = new_status
        except:
            pass

    def edit_eps_watched(self):
        episodes_watched = xbmcgui.Dialog().numeric(0, 'Enter episodes watched')
        if not episodes_watched:
            episodes_watched = self.eps_watched
        self.anime_item.setProperty('eps_watched', str(episodes_watched))
        self.eps_watched = episodes_watched

    def flip_score(self):

        if self.score == 'null' or '0':
            new_score = '1'

        if self.score != 'null' and 1 <= int(self.score) < 10:
            new_score = int(self.score) + 1

        if self.score == '10':
            new_score = '0'

        self.anime_item.setProperty('score', str(new_score))
        self.score = new_score

    def onClick(self, control_id):

        self.handle_action(7)

    def handle_action(self, action):

        focus_id = self.getFocusId()

        if (action == 4 or action == 3 or action == 7) and focus_id == 2000:
            # UP/ DOWN
            self.flip_flavor()

        if action == 92 or action == 10:
            # BACKSPACE / ESCAPE
            self.close()

        if action == 7:
            if focus_id == 2001:
                self.edit_anime()
            if focus_id == 1002:
                xbmcgui.Dialog().textviewer('dsds', 'dsds')
            if focus_id == 1003:
                self.close()
##            if focus_id == 3001:
##                self.flip_mutliple_providers('enabled', provider_type='hosters')
##            if focus_id == 3002:
##                self.flip_mutliple_providers('enabled', provider_type='torrent')
##            if focus_id == 3003:
##                self.flip_mutliple_providers('disabled', provider_type='hosters')
##            if focus_id == 3004:
##                self.flip_mutliple_providers('disabled', provider_type='torrent')
##            if focus_id == 3005:
##                self.flip_mutliple_providers('enabled')
##            if focus_id == 3006:
##                self.flip_mutliple_providers('disabled')
##            if focus_id == 3007:
##                self.flip_mutliple_providers('enabled', package_name=self.package_list.getSelectedItem().getLabel())
##            if focus_id == 3008:
##                self.flip_mutliple_providers('disabled', package_name=self.package_list.getSelectedItem().getLabel())
##            if focus_id == 3009:
##                tools.showBusyDialog()
##
##                self.providers_class.install_package(None)
##                self.packages = database.get_provider_packages()
##                self.fill_packages()
##                try:
##                    current_package = self.package_list.getSelectedItem().getLabel()
##                    self.fill_providers(current_package)
##                except:
##                    self.provider_list.reset()
##                    pass
##                tools.closeBusyDialog()
##                self.setFocus(self.package_list)
##            if focus_id == 3010:
##                try: package = self.package_list.getSelectedItem().getLabel()
##                except:
##                    return
##                tools.showBusyDialog()
##                confirm = tools.showDialog.yesno(tools.addonName, tools.lang(40255) % package)
##                if not confirm:
##                    tools.closeBusyDialog()
##                    return
##
##                self.providers_class.uninstall_package(package=self.package_list.getSelectedItem().getLabel(),
##                                                       silent=True)
##                self.packages = database.get_provider_packages()
##                self.fill_packages()
##                self.fill_providers()
##                tools.closeBusyDialog()
##                self.setFocus(self.package_list)
            pass

        if action == 0:
            pass

    def onAction(self, action):
        action = action.getId()

        if action == 7:
            return

        self.handle_action(action)