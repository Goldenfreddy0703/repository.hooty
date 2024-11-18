import base64
import codecs
import json
import pickle
import re
import six

from bs4 import BeautifulSoup, SoupStrainer
from six.moves import urllib_parse
from resources.lib.ui import control, database
from resources.lib.ui.BrowserBase import BrowserBase


class sources(BrowserBase):
    _BASE_URL = 'https://aniwave.se/'
    EKEY = "ysJhV6U27FVIjjuk"
    DKEY = "hlPeNwkncH0fq9so"
    CHAR_SUBST_OFFSETS = (-3, 3, -4, 2, -2, 5, 4, 5)
    # KEYS = json.loads(control.getSetting('keys.aniwave'))

    def get_sources(self, anilist_id, episode, get_backup):
        show = database.get_show(anilist_id)
        kodi_meta = pickle.loads(show.get('kodi_meta'))
        title = kodi_meta.get('name')
        title = self._clean_title(title)

        all_results = []
        items = []
        srcs = ['sub', 'dub']
        if control.getSetting('general.source') == 'Sub':
            srcs.remove('dub')
        elif control.getSetting('general.source') == 'Dub':
            srcs.remove('sub')

        headers = {'Referer': self._BASE_URL}
        params = {'keyword': title}
        r = database.get(
            self._get_request,
            8,
            self._BASE_URL + 'filter',
            data=params,
            headers=headers,
            XHR=True
        )
        if not r:
            return all_results

        mlink = SoupStrainer('div', {'class': 'ani items'})
        soup = BeautifulSoup(r, "html.parser", parse_only=mlink)
        sitems = soup.find_all('div', {'class': 'item'})
        if sitems:
            items = [urllib_parse.urljoin(self._BASE_URL, x.find('a', {'class': 'name'}).get('href'))
                     for x in sitems
                     if self.clean_title(title) == self.clean_title(x.find('a', {'class': 'name'}).get('data-jp'))]
            if not items:
                items = [urllib_parse.urljoin(self._BASE_URL, x.find('a', {'class': 'name'}).get('href'))
                         for x in sitems
                         if self.clean_title(title + 'dub') == self.clean_title(x.find('a', {'class': 'name'}).get('data-jp'))]

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
                        if self.clean_title(edata_name) in control.enabled_embeds():
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
                            skip = {}
                            if resp.get('skip_data'):
                                skip_data = json.loads(self.decrypt_vrf(resp.get('skip_data')))
                                intro = skip_data.get('intro')
                                if intro:
                                    skip.update({'intro': {'start': intro[0], 'end': intro[1]}})
                                outro = skip_data.get('outro')
                                if outro:
                                    skip.update({'outro': {'start': outro[0], 'end': outro[1]}})
                            slink = self.decrypt_vrf(resp.get('url'))
                            source = {
                                'release_title': '{0} - Ep {1}'.format(title, episode),
                                'hash': slink,
                                'type': 'embed',
                                'quality': 'EQ',
                                'debrid_provider': '',
                                'provider': 'aniwave',
                                'size': 'NA',
                                'info': [lang, edata_name],
                                'lang': 2 if lang == 'dub' else 0
                            }
                            if skip:
                                source.update({'skip': skip})
                            sources.append(source)
        except:
            pass
        return sources

    # def generate_vrf(self, content_id, keys=KEYS):
    #     vrf = control.vrf_shift(content_id, keys[0], keys[1])
    #     vrf = control.arc4(six.b(keys[2]), six.b(vrf))
    #     vrf = control.serialize_text(vrf)
    #     vrf = control.arc4(six.b(keys[3]), six.b(vrf))
    #     vrf = control.serialize_text(vrf)
    #     vrf = control.vrf_shift(vrf, keys[4], keys[5])
    #     vrf = control.vrf_shift(vrf, keys[6], keys[7])
    #     vrf = vrf[::-1]
    #     vrf = control.arc4(six.b(keys[8]), six.b(vrf))
    #     vrf = control.serialize_text(vrf)
    #     vrf = control.serialize_text(vrf)
    #     return vrf

    # def decrypt_vrf(self, text, keys=KEYS):
    #     text = control.deserialize_text(text)
    #     text = control.deserialize_text(six.ensure_str(text))
    #     text = control.arc4(six.b(keys[8]), text)
    #     text = text[::-1]
    #     text = control.vrf_shift(text, keys[7], keys[6])
    #     text = control.vrf_shift(text, keys[5], keys[4])
    #     text = control.deserialize_text(text)
    #     text = control.arc4(six.b(keys[3]), text)
    #     text = control.deserialize_text(text)
    #     text = control.arc4(six.b(keys[2]), text)
    #     text = control.vrf_shift(text, keys[1], keys[0])
    #     return text

    @staticmethod
    def vrf_shift(t, offsets=CHAR_SUBST_OFFSETS):
        o = ''
        for s in range(len(t)):
            o += chr(ord(t[s]) + offsets[s % 8])
        return o

    def generate_vrf(self, content_id, key=EKEY):
        vrf = control.arc4(six.b(key), six.b(urllib_parse.quote(content_id)))
        vrf = six.ensure_str(base64.urlsafe_b64encode(six.b(vrf)))
        vrf = six.ensure_str(base64.b64encode(six.b(vrf)))
        vrf = self.vrf_shift(vrf)
        vrf = six.ensure_str(base64.b64encode(six.b(vrf)))
        vrf = codecs.encode(vrf, 'rot_13')
        return vrf.replace('/', '_').replace('+', '-')

    @staticmethod
    def decrypt_vrf(text, key=DKEY):
        data = control.arc4(six.b(key), base64.urlsafe_b64decode(six.b(text)))
        data = urllib_parse.unquote(data)
        return data

    @staticmethod
    def clean_title(text):
        return re.sub(r'\W', '', text).lower()
