# -*- coding: utf-8 -*-
"""
    Added by umbrelladev 10-6-22
    Redisigned by Goldenfreddy0703 2-5-23
"""
from resources.lib.windows.base import BaseDialog


class TextViewerXML(BaseDialog):

    def __init__(self, *args, **kwargs):
        BaseDialog.__init__(self, args)
        self.window_id = 2060
        self.heading = kwargs.get('heading')
        self.text = kwargs.get('text')
        self.text_2 = kwargs.get('text_2')

    def run(self):
        self.doModal()
        self.clearProperties()

    def onInit(self):
        self.set_properties()
        self.setFocusId(self.window_id)

    def onAction(self, action):
        if action in self.closing_actions or action in self.selection_actions:
            self.close()

    def set_properties(self):
        self.setProperty('otaku.text_2', self.text_2)
        self.setProperty('otaku.text', self.text)
        self.setProperty('otaku.heading', self.heading)
