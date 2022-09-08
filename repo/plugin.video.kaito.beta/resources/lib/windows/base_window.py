# -*- coding: utf-8 -*-
from builtins import str
__metaclass__ = type

import os

from resources.lib.ui.globals import g
from resources.lib.ui import control
import ast
import xbmcgui

class BaseWindow(xbmcgui.WindowXMLDialog):

    def __init__(self, xml_file, location, actionArgs=None):

        try:
            super(BaseWindow, self).__init__(xml_file, location)
        except:
            xbmcgui.WindowXMLDialog().__init__()

        g.close_busy_dialog()
        self.canceled = False

        self.setProperty('texture.white', os.path.join(g.IMAGES_PATH, 'white.png'))
        self.setProperty('kaito.logo', os.path.join(g.IMAGES_PATH, 'trans-crow.png'))
        self.setProperty('kaito.fanart', g.DEFAULT_FANART)
        self.setProperty('settings.color', 'deepskyblue')
        self.setProperty('test.pattern', os.path.join(g.IMAGES_PATH, 'test_pattern.png'))
        self.setProperty('skin.dir', g.ADDON_DATA_PATH)

        if actionArgs is None:
            return

        if actionArgs.get('anilist_id'):
            self.item_information = control.get_item_information(actionArgs["anilist_id"])
        elif actionArgs.get('playnext'):
            self.item_information = actionArgs
            self.setProperty('item.info.%s' % 'tvshowtitle', self.item_information.get('tvshowtitle'))
            self.setProperty('item.info.%s' % 'episode', str(self.item_information.get('episode')))
            self.setProperty('item.info.%s' % 'aired', self.item_information.get('aired'))
            self.setProperty('item.info.%s' % 'rating', str(round(self.item_information.get('rating'), 2)))
            self.setProperty('item.info.%s' % 'season', str(self.item_information.get('season')))
        else:
            self.item_information = {}

        #for id, value in self.item_information['ids'].items():
        self.setProperty('item.ids.%s_id' % 1, str('gh'))

        try:
            for i in self.item_information['art'].keys():
                self.setProperty('item.art.{}'.format(i), g.UNICODE(self.item_information['art'][i]))
        except:
            pass

        #for i in self.item_information['art'].keys():
        # self.setProperty('item.art.%s' % 'thumb', self.item_information.get('thumb'))
        # self.setProperty('item.art.%s' % 'poster', self.item_information.get('poster'))
        # self.setProperty('item.art.%s' % 'fanart', self.item_information.get('fanart'))
        self.setProperty('item.info.%s' % 'title', self.item_information.get('name'))

        #self.item_information['info'] = tools.clean_air_dates(self.item_information['info'])

        #year, month, day = self.item_information['info'].get('aired', '0000-00-00').split('-')

        self.setProperty('item.info.aired.year', '2018')
        self.setProperty('item.info.aired.month', '01')
        self.setProperty('item.info.aired.day', '01')

        try:
            if 'aired' in self.item_information['info']:
                aired_date = self.item_information['info']['aired']
                aired_date = tools.datetime_workaround(aired_date)
                aired_date = aired_date.strftime(tools.get_region('dateshort'))
                self.item_information['info']['aired'] = aired_date
                
            if 'premiered' in self.item_information['info']:
                premiered = self.item_information['info']['premiered']
                premiered = tools.datetime_workaround(premiered)
                premiered = premiered.strftime(tools.get_region('dateshort'))
                self.item_information['info']['premiered'] = premiered
        except:
            pass

        value = 'TBA'
        try:
            self.setProperty('item.info.%s' % 1, str('fdf'))
        except UnicodeEncodeError:
            self.setProperty('item.info.%s' % 1, 'fdf')
