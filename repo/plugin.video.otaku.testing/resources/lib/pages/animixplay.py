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
                playbunny = 'https://play.bunnycdn.to/'
                esurl = '{0}hs/{1}'.format(playbunny, eplist.get(ep).split('/')[-1])
                epage = database.get(client.request, 8, esurl, referer=playbunny)
                ep_id = re.search(r'<div\s*id="mg-player"\s*data-id="([^"]+)', epage)
                if ep_id:
                    ep_url = '{0}hs/getSources?id={1}'.format(playbunny, ep_id.group(1))
                    ep_src = database.get(client.request, 8, ep_url, referer=playbunny)
                    try:
                        ep_src = json.loads(ep_src)
                    except:
                        return sources
                    src = ep_src.get('sources')
                    if src:
                        server = 'bunny'
                        skip = {}
                        if ep_src.get('intro'):
                            skip['intro'] = ep_src.get('intro')
                        if ep_src.get('outro'):
                            skip['outro'] = ep_src.get('outro')
                        source = {
                            'release_title': '{0} Ep{1}'.format(title, episode),
                            'hash': src + '|Referer={0}&Origin={1}&User-Agent=iPad'.format(playbunny, playbunny[:-1]),
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
                            'sub': 1,
                            'skip': skip
                        }
                        sources.append(source)

        return sources
