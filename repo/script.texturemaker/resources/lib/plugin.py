# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import os
import sys
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
import json
from PIL import Image

ADDON = xbmcaddon.Addon('script.texturemaker')
ADDONPATH = ADDON.getAddonInfo('path')
ADDONDATA = 'special://profile/addon_data/script.texturemaker/'
COLORDEFS = '{}/resources/colors/colors.json'.format(ADDONPATH)


def load_colors(filename=None, meta=None):
    filename = 'special://skin/{}'.format(filename) if filename else COLORDEFS
    filename = xbmcvfs.translatePath(filename)
    if os.path.exists(filename):
        with open(filename, 'r') as file:
            meta = json.load(file) or meta
    return meta if meta else load_colors(meta={"ffffffff": "ffffffff"})


class Plugin(object):
    def __init__(self):
        self.handle = int(sys.argv[1])
        self.paramstring = sys.argv[2][1:]
        self.colors = load_colors(self.paramstring)
        self.save_dir = '{}/colors'.format(ADDONDATA)

    def run(self):
        if not os.path.exists(xbmcvfs.translatePath(self.save_dir)):
            os.makedirs(xbmcvfs.translatePath(self.save_dir))

        for k, v in self.colors.items():
            rrggbb = '#{}'.format(k[2:])
            swatch = xbmcvfs.translatePath('{}/{}.png'.format(self.save_dir, k))

            if not os.path.exists(swatch):
                img = Image.new('RGB', (16, 16), rrggbb)
                img.save(swatch)

            xbmcplugin.addDirectoryItem(
                handle=self.handle,
                url=swatch,
                listitem=xbmcgui.ListItem(label=k, label2=v, path=swatch),
                isFolder=False)

        xbmcplugin.endOfDirectory(self.handle)
