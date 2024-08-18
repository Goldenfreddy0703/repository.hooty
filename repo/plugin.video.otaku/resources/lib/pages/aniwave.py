import json
import pickle
import re
import six

from bs4 import BeautifulSoup, SoupStrainer
from six.moves import urllib_parse
from resources.lib.ui import control, database
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.indexers.malsync import MALSYNC


class sources(BrowserBase):
    _BASE_URL = 'https://aniwave.to/' if control.getSetting('provider.aniwavealt') == 'false' else 'https://aniwave.vc/'
    keys = json.loads(control.getSetting('keys.aniwave'))

    def get_sources(self, anilist_id, episode, get_backup):
        show = database.get_show(anilist_id)
        kodi_meta = pickle.loads(show.get('kodi_meta'))
        title = kodi_meta.get('name')
        title = self._clean_title(title)

        all_results = []
        srcs = ['sub', 'softsub', 'dub']
        if control.getSetting('general.source') == 'Sub':
            srcs.remove('dub')
        elif control.getSetting('general.source') == 'Dub':
            srcs.remove('sub')
            srcs.remove('softsub')

        items = MALSYNC().get_slugs(anilist_id=anilist_id, site='9anime')
        if not items:
            headers = {'Referer': self._BASE_URL}
            params = {'keyword': title}
            r = database.get(
                self._get_request,
                8,
                self._BASE_URL + 'ajax/anime/search',
                data=params,
                headers=headers,
                XHR=True
            )
            if not r and ':' in title:
                title = title.split(':')[0]
                params.update({'keyword': title})
                r = database.get(
                    self._get_request,
                    8,
                    self._BASE_URL + 'ajax/anime/search',
                    data=params,
                    headers=headers,
                    XHR=True
                )
            if not r:
                return all_results

            r = json.loads(r)
            r = BeautifulSoup(r.get('html') or r.get('result', {}).get('html'), "html.parser")
            sitems = r.find_all('a', {'class': 'item'})
            if sitems:
                if title[-1].isdigit():
                    items = [urllib_parse.urljoin(self._BASE_URL, x.get('href'))
                             for x in sitems
                             if title.lower() in x.find('div', {'class': 'name'}).get('data-jp').lower()]
                else:
                    items = [urllib_parse.urljoin(self._BASE_URL, x.get('href'))
                             for x in sitems
                             if (title.lower() + '  ') in (x.find('div', {'class': 'name'}).get('data-jp').lower() + '  ')]

        if items:
            slug = items[0]
            all_results = self._process_aw(slug, title=title, episode=episode, langs=srcs)

        return all_results

    def _process_aw(self, slug, title, episode, langs):
        sources = []
        headers = {'Referer': self._BASE_URL}
        r = database.get(
            self._get_request, 8,
            slug, headers=headers
        )
        sid = re.search(r'id="watch-main.+?data-id="([^"]+)', r)
        if not sid:
            return sources

        sid = sid.group(1)
        vrf = self.generate_vrf(sid)
        params = {'vrf': vrf}
        r = database.get(
            self._get_request, 8,
            '{0}ajax/episode/list/{1}'.format(self._BASE_URL, sid),
            headers=headers, data=params,
            XHR=True
        )
        res = json.loads(r).get('result')
        try:
            elink = SoupStrainer('div', {'class': re.compile('^episodes')})
            ediv = BeautifulSoup(res, "html.parser", parse_only=elink)
            items = ediv.find_all('a')
            e_id = [x.get('data-ids') for x in items if x.get('data-num') == episode]
            if e_id:
                e_id = e_id[0]
                vrf = self.generate_vrf(e_id)
                params = {'vrf': vrf}
                r = database.get(
                    self._get_request, 8,
                    '{0}ajax/server/list/{1}'.format(self._BASE_URL, e_id),
                    data=params, headers=headers,
                    XHR=True
                )
                eres = json.loads(r).get('result')
                scrapes = 0
                for lang in langs:
                    elink = SoupStrainer('div', {'data-type': lang})
                    sdiv = BeautifulSoup(eres, "html.parser", parse_only=elink)
                    srcs = sdiv.find_all('li')
                    for src in srcs:
                        edata_id = src.get('data-link-id')
                        edata_name = src.text
                        if edata_name.lower() in control.enabled_embeds():
                            if scrapes == 3:
                                control.sleep(5000)
                                scrapes = 0
                            vrf = self.generate_vrf(edata_id)
                            params = {'vrf': vrf}
                            r = self._get_request(
                                '{0}ajax/server/{1}'.format(self._BASE_URL, edata_id),
                                data=params,
                                headers=headers,
                                XHR=True
                            )
                            scrapes += 1
                            resp = json.loads(r).get('result')
                            slink = self.decrypt_vrf(resp.get('url'))

                            skip = {}
                            if resp.get('skip_data'):
                                skip_data = json.loads(self.decrypt_vrf(resp.get('skip_data')))
                                intro = skip_data.get('intro')
                                if intro:
                                    skip.update({'intro': {'start': intro[0], 'end': intro[1]}})
                                outro = skip_data.get('outro')
                                if outro:
                                    skip.update({'outro': {'start': outro[0], 'end': outro[1]}})

                            source = {
                                'release_title': '{0} - Ep {1}'.format(title, episode),
                                'hash': slink,
                                'type': 'embed',
                                'quality': 'EQ',
                                'debrid_provider': '',
                                'provider': 'aniwave',
                                'size': 'NA',
                                'info': [lang, edata_name],
                                'lang': 2 if lang == 'dub' else 0,
                                'skip': skip
                            }
                            sources.append(source)
        except:
            import traceback
            traceback.print_exc()
            pass
        return sources

    def generate_vrf(self, content_id):
        vrf = control.vrf_shift(content_id, "AP6GeR8H0lwUz1", "UAz8Gwl10P6ReH")
        vrf = control.arc4(six.b("ItFKjuWokn4ZpB"), six.b(vrf))
        vrf = control.serialize_text(vrf)
        vrf = control.arc4(six.b("fOyt97QWFB3"), six.b(vrf))
        vrf = control.serialize_text(vrf)
        vrf = control.vrf_shift(vrf, "1majSlPQd2M5", "da1l2jSmP5QM")
        vrf = control.vrf_shift(vrf, "CPYvHj09Au3", "0jHA9CPYu3v")
        vrf = vrf[::-1]
        vrf = control.arc4(six.b("736y1uTJpBLUX"), six.b(vrf))
        vrf = control.serialize_text(vrf)
        vrf = control.serialize_text(vrf)
        return vrf

    def decrypt_vrf(self, text):
        text = control.deserialize_text(text)
        text = control.deserialize_text(six.ensure_str(text))
        text = control.arc4(six.b("736y1uTJpBLUX"), text)
        text = text[::-1]
        text = control.vrf_shift(text, "0jHA9CPYu3v", "CPYvHj09Au3")
        text = control.vrf_shift(text, "da1l2jSmP5QM", "1majSlPQd2M5")
        text = control.deserialize_text(text)
        text = control.arc4(six.b("fOyt97QWFB3"), text)
        text = control.deserialize_text(text)
        text = control.arc4(six.b("ItFKjuWokn4ZpB"), text)
        text = control.vrf_shift(text, "UAz8Gwl10P6ReH", "AP6GeR8H0lwUz1")
        return text
