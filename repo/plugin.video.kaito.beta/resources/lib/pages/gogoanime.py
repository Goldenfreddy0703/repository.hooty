# -*- coding: utf-8 -*-
from builtins import map
from builtins import str
import json
import bs4 as bs
import re
import itertools
from functools import partial
from ..ui import source_utils
from resources.lib.database.cache import use_cache
from resources.lib.ui.globals import g
from ..ui.BrowserBase import BrowserBase
from ..debrid import real_debrid, all_debrid
from ..ui import database
import requests
import threading
import copy

class sources(BrowserBase):
    def get_sources(self, anilist_id, episode, get_backup):
        slugs = get_backup(anilist_id, 'Gogoanime')
        if not slugs:
            return []
        slugs = list(slugs.keys())
        mapfunc = partial(self._process_gogo, show_id=anilist_id, episode=episode)
        all_results = list(map(mapfunc, slugs))
        all_results = list(itertools.chain(*all_results))
        return all_results

    def _process_gogo(self, slug, show_id, episode):
        url = "https://gogoanime.vc/%s-episode-%s" % (slug, episode)
        title = (slug.replace('-', ' ')).title()
        result = requests.get(url).text
        soup = bs.BeautifulSoup(result, 'html.parser')
        sources = []

        for element in soup.select('.anime_muti_link > ul > li'):
            server = element.get('class')[0]
            link = element.a.get('data-video')
            type_ = None
            # type_ = 'hoster'

            # if server == 'streamtape':
            #     type_ = 'embed'

            if server == 'xstreamcdn':
                type_ = 'embed'

            elif server == 'vidcdn':
                type_ = 'embed'
                link = 'https:' + link

            if not type_:
                continue

            source = {
                'release_title': title,
                'hash': link,
                'type': type_,
                'quality': 'NA',
                'debrid_provider': '',
                'provider': 'gogo',
                'size': 'NA',
                'info': source_utils.getInfo(slug),
                'lang': source_utils.getAudio_lang(title)
                }
            sources.append(source)

        return sources

    def get_latest(self):
        url = 'https://ajax.gogocdn.net/ajax/page-recent-release.html?page=1&type=1'
        return self._process_latest_view(url)

    def get_latest_dub(self):
        url = 'https://ajax.gogocdn.net/ajax/page-recent-release.html?page=1&type=2'
        return self._process_latest_view(url)

    @use_cache(0.125)
    def __get_request(self, url):
        result = requests.get(url).text
        return result

    def _process_latest_view(self, url):
        result = self.__get_request(url)
        soup = bs.BeautifulSoup(result, 'html.parser')
        animes = soup.find_all('div', {'class': 'img'})
        all_results = list(map(self._parse_latest_view, animes))
        g.close_directory(g.CONTENT_EPISODE)
        # return all_results

    def _parse_latest_view(self, res):
        res = res.a
        info = {}
        slug, episode = (res['href'][1:]).rsplit('-episode-', 1)
        name = '%s - Ep. %s' % (res['title'], episode)
        image = res.img['src']
        info['title'] = name
        info['mediatype'] = 'episode'

        art = {
            'poster': image,
            'fanart': image,
            'thumb': image,
        }

        menu_item = {
            'art': art,
            'info': info
        }

        g.add_directory_item(
            name,
            action='play_gogo',
            action_args={"slug": slug, "_episode": episode, "mediatype": "episode"},
            menu_item=menu_item,
            is_playable=True
        )
        # return g.allocate_item(name, "play_gogo/" + str(url), False, image, info, is_playable=True)