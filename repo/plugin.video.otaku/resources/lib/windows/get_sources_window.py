import threading

from resources.lib.ui import control
from resources.lib.windows.base_window import BaseWindow


class GetSources(BaseWindow):
    def __init__(self, xml_file, xml_location, actionArgs=None):
        super().__init__(xml_file, xml_location, actionArgs=actionArgs)

        control.closeBusyDialog()
        self.setProperty('process_started', 'false')
        self.setProperty('progress', '0')

        self.silent = actionArgs.get('silent')
        self.canceled = False
        self.return_data = []
        self.args = actionArgs
        self.progress = 0
        self.torrents_qual_len = [0, 0, 0, 0, 0]
        self.embeds_qual_len = [0, 0, 0, 0, 0]
        self.torrentSources = []
        self.torrentCacheSources = []
        self.embedSources = []
        self.cloud_files = []
        self.local_files = []
        self.remainingProviders = []
        self.remaining_providers_list = []

    def onInit(self):
        threading.Thread(target=self.getSources, args=[self.args]).start()

    def doModal(self):
        if self.silent:
            self.getSources(self.args)
        else:
            super(GetSources, self).doModal()
        return self.return_data

    def getSources(self, args):
        self.setProperty('process_started', 'true')
        if not self.silent:
            self.update_properties("4K: %s | 1080: %s | 720: %s | SD: %s| EQ: %s" % (
                control.colorstr(self.torrents_qual_len[0] + self.embeds_qual_len[0]),
                control.colorstr(self.torrents_qual_len[1] + self.embeds_qual_len[1]),
                control.colorstr(self.torrents_qual_len[2] + self.embeds_qual_len[2]),
                control.colorstr(self.torrents_qual_len[3] + self.embeds_qual_len[3]),
                control.colorstr(self.torrents_qual_len[4] + self.embeds_qual_len[4])
            ))
        self.close()

    def onAction(self, action):
        actionID = action.getId()

        if actionID in [92, 10]:
            # BACKSPACE / ESCAPE
            self.canceled = True

    def update_properties(self, text):
        self.setProperty('notification_text', str(text))
        self.setProperty('4k_sources', str(self.torrents_qual_len[0] + self.embeds_qual_len[0]))
        self.setProperty('1080p_sources', str(self.torrents_qual_len[1] + self.embeds_qual_len[1]))
        self.setProperty('720p_sources', str(self.torrents_qual_len[2] + self.embeds_qual_len[2]))
        self.setProperty('SD_sources', str(self.torrents_qual_len[3] + self.embeds_qual_len[3]))
        self.setProperty('EQ_sources', str(self.torrents_qual_len[4] + self.embeds_qual_len[4]))

        self.setProperty('total_torrents', str(len(self.torrentSources)))
        self.setProperty('cached_torrents', str(len(self.torrentCacheSources)))
        self.setProperty('hosters_sources', str(len(self.embedSources)))
        self.setProperty('cloud_sources', str(len(self.cloud_files)))
        self.setProperty('local_sources', str(len(self.local_files)))

        self.setProperty("remaining_providers_count", str((len(self.remainingProviders))))

        self.remaining_providers_list = self.getControl(2000)
        self.remaining_providers_list.reset()
        self.remaining_providers_list.addItems(self.remainingProviders)
        self.setProperty("remaining_providers_list", control.colorstr(' | ').join([i.upper() for i in self.remainingProviders]))
        self.setProperty('progress', str(self.progress))
