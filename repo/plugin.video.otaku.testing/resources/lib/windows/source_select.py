import pickle
import xbmcgui

from resources.lib.ui import control, database
from resources.lib.windows.base_window import BaseWindow
from resources.lib.windows.download_manager import Manager
from resources.lib.windows.resolver import Resolver
from resources.lib import OtakuBrowser


class SourceSelect(BaseWindow):
    def __init__(self, xml_file, location, actionArgs=None, sources=None, rescrape=None):
        super().__init__(xml_file, location, actionArgs=actionArgs)
        self.actionArgs = actionArgs
        self.sources = sources
        self.displayed_sources = []  # List to maintain displayed sources
        self.showing_uncached = False  # Track whether uncached sources are being shown
        self.rescrape = rescrape
        self.position = -1
        self.canceled = False
        self.display_list = None
        self.stream_link = None

        episode = actionArgs.get('episode')
        if episode:
            anime_init = OtakuBrowser.get_anime_init(actionArgs.get('mal_id'))
            episode = int(episode)
            try:
                self.setProperty('item.info.season', str(anime_init[0][episode - 1]['info']['season']))
                self.setProperty('item.info.episode', str(anime_init[0][episode - 1]['info']['episode']))
                self.setProperty('item.info.plot', anime_init[0][episode - 1]['info']['plot'])
                self.setProperty('item.info.aired', anime_init[0][episode - 1]['info'].get('aired'))
                self.setProperty('item.art.thumb', anime_init[0][episode - 1]['image']['thumb'])
                self.setProperty('item.art.poster', anime_init[0][episode - 1]['image']['poster'])
            except IndexError:
                self.setProperty('item.info.season', '-1')
                self.setProperty('item.info.episode', '-1')

            try:
                year, month, day = anime_init[0][episode - 1]['info'].get('aired', '0000-00-00').split('-')
                self.setProperty('item.info.year', year)
            except ValueError:
                pass
        else:
            show = database.get_show(actionArgs.get('mal_id'))
            if show:
                kodi_meta = pickle.loads(show.get('kodi_meta'))
                self.setProperty('item.info.plot', kodi_meta.get('plot'))
                self.setProperty('item.info.rating', str(kodi_meta.get('rating', {}).get('score')))
                self.setProperty('item.info.aired', kodi_meta.get('start_date'))
                self.setProperty('item.art.thumb', kodi_meta.get('poster'))
                try:
                    self.setProperty('item.info.year', kodi_meta.get('start_date').split('-')[0])
                except AttributeError:
                    pass

    def onInit(self):
        self.display_list = self.getControl(1000)
        # Initially populate with only cached sources
        cached_sources = [source for source in self.sources if source.get('cached') is not False]
        if cached_sources:
            self.populate_sources(cached_sources)
            self.getControl(15).setLabel("View Uncached")
            self.showing_uncached = False
        else:
            uncached_sources = [source for source in self.sources if source.get('cached') is False]
            self.populate_sources(uncached_sources)
            self.getControl(15).setLabel("View Cached")
            self.showing_uncached = True
        self.setFocusId(1000)

    def populate_sources(self, sources):
        self.display_list.reset()
        self.displayed_sources = sources  # Update the displayed sources list
        menu_items = []
        for i in sources:
            if not i:
                continue
            menu_item = xbmcgui.ListItem('%s' % i['release_title'], offscreen=False)
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

    def doModal(self):
        super(SourceSelect, self).doModal()
        return self.stream_link

    def handle_action(self, action_id):
        # Implement the logic for handling the action here
        # For now, you can just log the action_id
        control.log(f"Action handled: {action_id}")

    def onClick(self, controlId):
        if controlId == 15:  # View Uncached button
            if self.showing_uncached:
                cached_sources = [source for source in self.sources if source.get('cached') is not False]
                self.populate_sources(cached_sources)
                self.getControl(15).setLabel("View Uncached")
                self.showing_uncached = False
            else:
                uncached_sources = [source for source in self.sources if source.get('cached') is False]
                self.populate_sources(uncached_sources)
                self.getControl(15).setLabel("View Cached")
                self.showing_uncached = True
        elif controlId == 1000:
            # No need to call handle_action(7) here since onAction already handles it
            pass

    def onAction(self, action):
        actionID = action.getId()

        if actionID in [92, 10]:
            # BACKSPACE / ESCAPE
            control.playList.clear()
            self.stream_link = False
            self.close()

        if actionID in [7, 100] and self.getFocusId() == 1000:
            self.position = self.display_list.getSelectedPosition()
            self.resolve_item()

        if actionID == 117:
            context = control.context_menu(
                [
                    "Play",
                    "Download",
                    "File Select"
                ]
            )
            self.position = self.display_list.getSelectedPosition()
            if context == 0:  # Play
                self.resolve_item()
            elif context == 1:  # Download
                if self.displayed_sources[self.position]['debrid_provider'] == 'Local-Debrid' or self.displayed_sources[self.position]['debrid_provider'] == '':
                    control.notify(control.ADDON_NAME, "Please Select A Debrid File")
                elif self.displayed_sources[self.position]['debrid_provider'] == 'EasyDebrid':
                    control.notify(control.ADDON_NAME, "EasyDebrid does not support Downloads")
                else:
                    self.close()
                    source = [self.displayed_sources[self.display_list.getSelectedPosition()]]
                    self.actionArgs['play'] = False
                    if control.getSetting('general.dialog') == '5':
                        return_data = Resolver('resolver_az.xml', control.ADDON_PATH, actionArgs=self.actionArgs, source_select=True).doModal(source, {}, False)
                    else:
                        return_data = Resolver('resolver.xml', control.ADDON_PATH, actionArgs=self.actionArgs, source_select=True).doModal(source, {}, False)
                    if isinstance(return_data, dict):
                        Manager().download_file(return_data['link'])

            elif context == 2:  # File Selection
                if not self.displayed_sources[self.position]['debrid_provider']:
                    control.notify(control.ADDON_NAME, "Please Select A Debrid File")
                else:
                    self.resolve_item(True)

    def resolve_item(self, pack_select=False):
        if control.getBool('general.autotrynext') and not pack_select:
            sources = self.displayed_sources[self.position:]
        else:
            sources = [self.displayed_sources[self.position]]
        if self.rescrape:
            selected_source = self.displayed_sources[self.position]
            selected_source['name'] = selected_source['release_title']
        self.actionArgs['close'] = self.close
        if control.getSetting('general.dialog') == '5':
            self.stream_link = Resolver('resolver_az.xml', control.ADDON_PATH, actionArgs=self.actionArgs, source_select=True).doModal(sources, {}, pack_select)
        else:
            self.stream_link = Resolver('resolver.xml', control.ADDON_PATH, actionArgs=self.actionArgs, source_select=True).doModal(sources, {}, pack_select)
        if isinstance(self.stream_link, dict):
            self.close()
