import base64
import itertools
import json
import pickle
import re
import urllib.parse
from functools import partial

from bs4 import BeautifulSoup
from resources.lib.ui import control, database, client
from resources.lib.ui.BrowserBase import BrowserBase


class Sources(BrowserBase):
    _BASE_URL = 'https://animixplay.st/' if control.getBool('provider.animixalt') else 'https://animixplay.name/'

    def get_sources(self, mal_id, episode):
        show = database.get_show(mal_id)
        kodi_meta = pickle.loads(show.get('kodi_meta'))
        srcs = ['sub', 'dub']
        if control.getSetting('general.source') == 'Sub':
            srcs.remove('dub')
        elif control.getSetting('general.source') == 'Dub':
            srcs.remove('sub')
        # title = kodi_meta.get('ename') or kodi_meta.get('name')
        title = kodi_meta.get('name')
        title = self._clean_title(title)
        all_results = []
        headers = {'Origin': self._BASE_URL[:-1],
                   'Referer': self._BASE_URL}
        r = database.get(
            client.request,
            8,
            self._BASE_URL + 'api/search',
            XHR=True,
            post={'qfast': title},
            headers=headers
        )
        if r:
            soup = BeautifulSoup(json.loads(r).get('result'), 'html.parser')
            items = soup.find_all('a')
            slugs = []

            for item in items:
                ititle = item.find('p', {'class': 'name'})
                if ititle:
                    ititle = ititle.text.strip()
                    if 'sub' in srcs:
                        if self.clean_embed_title(ititle) == self.clean_embed_title(title):
                            slugs.append(item.get('href'))
                    if 'dub' in srcs:
                        if self.clean_embed_title(ititle) == self.clean_embed_title(title) + 'dub':
                            slugs.append(item.get('href'))
            if not slugs:
                if len(items) > 0:
                    slugs = [items[0].get('href')]
            if slugs:
                slugs = list(slugs.keys()) if isinstance(slugs, dict) else slugs
                mapfunc = partial(self._process_animixplay, title=title, episode=episode)
                all_results = list(map(mapfunc, slugs))
                all_results = list(itertools.chain(*all_results))
        return all_results

    def _process_animixplay(self, slug, title, episode):
        sources = []
        lang = 3 if slug[-3:] == 'dub' else 2
        slug_url = urllib.parse.urljoin(self._BASE_URL, slug)
        r = database.get(client.request, 8, slug_url, referer=self._BASE_URL)
        eplist = re.search(r'<div\s*id="epslistplace".+?>([^<]+)', r)
        if eplist:
            eplist = json.loads(eplist.group(1).strip())
            ep = str(int(episode) - 1)
            if ep in eplist.keys():
                referer = 'https://bunnycdn.to/'
                esurl = "https://bunnycdn.to/api/play_int?id=cW9" + (base64.b64encode((eplist.get(ep).split('id=')[-1] + "LTXs3GrU8we9O").encode('latin-1'))).decode('latin-1')
                epage = database.get(client.request, 8, esurl, referer=self._BASE_URL)
                src = re.search(r'<source.+?src="([^"]+)', epage)
                if src:
                    # embeds_list = self.embeds()
                    # if 'bunny' in embeds_list:
                    #     server = 'bunny'
                    server = 'bunny'
                    source = {
                        'release_title': '{0} Ep{1}'.format(title, episode),
                        'hash': src.group(1) + '|Referer={0}&Origin={1}&User-Agent=iPad'.format(referer, referer[:-1]),
                        'type': 'direct',
                        'quality': 2,
                        'debrid_provider': '',
                        'provider': 'animix',
                        'size': 'NA',
                        'seeders': 0,
                        'byte_size': 0,
                        'info': [server + (' SUB' if lang == 2 else ' DUB')],
                        'lang': lang,
                        'channel': 3,
                        'sub': 1
                    }

                    sources.append(source)

        return sources
