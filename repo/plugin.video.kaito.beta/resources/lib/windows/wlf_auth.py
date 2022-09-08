# -*- coding: utf-8 -*-

from builtins import object
import time
from resources.lib.ui.globals import g
from resources.lib.windows.base_window import BaseWindow
from resources.lib.windows.resolver import Resolver
from resources.lib.ui import database
import xbmcgui

class WatchlistFlavorAuth(BaseWindow):

    def __init__(self, xml_file, location, flavor=None, sources=None, **kwargs):
        super(WatchlistFlavorAuth, self).__init__(xml_file, location)
        self.flavor = flavor
        self.sources = sources
        self.position = -1
        self.last_action = 0
        g.close_busy_dialog()
        self.authorized = False

    def onInit(self):
        self.setFocusId(1000)

    def doModal(self):
        super(WatchlistFlavorAuth, self).doModal()
        return self.authorized

    def onClick(self, controlId):

        if controlId == 1000:
            self.handle_action(7)

    def handle_action(self, actionID):
        if (time.time() - self.last_action) < .5:
            return

        if actionID == 7 and self.getFocusId() == 1002:
            self.set_settings()

        if actionID == 7 and self.getFocusId() == 1003:
            self.close()

        if actionID == 92 or id == 10:
            self.close()

        self.last_action = time.time()

    def onAction(self, action):
        actionID = action.getId()

        if actionID in [7, 92, 10]:
            self.handle_action(actionID)

    def set_settings(self):
        res = {}
        if self.flavor == 'anilist':
            res['token'] = self.getControl(1000).getText()
        else:
            res['authvar'] = self.getControl(1000).getText()

        for _id, value in list(res.items()):
            g.set_setting('%s.%s' % (self.flavor, _id), value)

        self.authorized = True
        self.close()

class AltWatchlistFlavorAuth(object):
    def __init__(self, flavor=None):
        self.flavor = flavor
        self.authorized = False

    def set_settings(self):
        res = {}
        dialog = xbmcgui.Dialog()
        if self.flavor == 'anilist':
            dialog.textviewer(g.ADDON_NAME + ': AniList',
                              '{}\n{}\n{}'.format(g.lang(40105),
                                                  g.lang(40106).replace('below', 'in the input dialog that will popup once you close this'),
                                                  g.lang(40110)))

            res['token'] = dialog.input('Enter AniList token', type=xbmcgui.INPUT_ALPHANUM)
        else:
            dialog.textviewer(g.ADDON_NAME + ': MyAnimeList',
                              '{}\n{}\n{}'.format(g.lang(40100),
                                                  g.lang(40101).replace('below', 'in the input dialog that will popup once you close this'),
                                                  g.lang(40110)))

            res['authvar'] = dialog.input('Enter MAL auth url', type=xbmcgui.INPUT_ALPHANUM)

        try:
            for _id, value in list(res.items()):
                if not value:
                    raise Exception

                g.set_setting('%s.%s' % (self.flavor, _id), value)
                self.authorized = True
        except:
            pass

        return self.authorized