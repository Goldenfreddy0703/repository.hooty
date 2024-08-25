import json
import pickle
import re

from resources.lib.ui import database, source_utils
from resources.lib.ui.BrowserBase import BrowserBase


class sources(BrowserBase):
    _BASE_URL = 'https://www.animelatinohd.com/'
    _API_URL = 'https://web.animelatinohd.com/'
    BID = 'w51kDCy70VSuxmn7Usaie'

    def get_sources(self, anilist_id, episode, get_backup):
        show = database.get_show(anilist_id)
        kodi_meta = pickle.loads(show.get('kodi_meta'))
        title = kodi_meta.get('name')
        title = self._clean_title(title)
        headers = {'Referer': self._BASE_URL}

        res = database.get(
            self._get_request,
            168,
            self._BASE_URL,
            headers=headers
        )
        r = re.search(r'"buildId":"([^"]+)', res)
        if r:
            self.BID = r.group(1)

        headers.update({'Origin': self._BASE_URL[:-1]})
        params = {'search': title}
        res = database.get(
            self._get_request,
            8,
            self._API_URL + 'api/anime/search',
            data=params,
            headers=headers
        )
        try:
            items = self.al_decode(json.loads(res).get('data'))
        except:
            items = []

        if not items and ':' in title:
            title = title.split(':')[0]
            params = {'search': title}
            res = database.get(
                self._get_request,
                8,
                self._BASE_URL,
                data=params,
                headers=headers
            )
            try:
                items = self.al_decode(json.loads(res).get('data'))
            except:
                items = []

        all_results = []
        if items:
            if title[-1].isdigit():
                items = [x for x in items if title.lower() in x.get('name').lower()]
            else:
                items = [x for x in items if (title.lower() + '  ') in (x.get('name').lower() + '  ')]
            if items:
                slug = items[0].get('slug')
                all_results = self._process_al(slug, title=title, episode=episode)

        return all_results

    def _process_al(self, slug, title, episode):
        sources = []
        headers = {'Referer': self._BASE_URL, 'x-nextjs-data': 1}
        url = '{0}_next/data/{1}/anime/{2}.json'.format(
            self._BASE_URL,
            self.BID,
            slug
        )
        params = {'slug': slug}
        res = database.get(
            self._get_request,
            8,
            url,
            data=params,
            headers=headers
        )

        try:
            items = self.al_decode(json.loads(res).get('pageProps').get('data')).get('episodes')
        except:
            items = []
        e_id = [x.get('number') for x in items if x.get('number') == int(episode)]
        if e_id:
            url = '{0}_next/data/{1}/ver/{2}/{3}.json'.format(
                self._BASE_URL,
                self.BID,
                slug,
                e_id[0]
            )
            params.update({'number': e_id[0]})
            res = self._get_request(url, data=params, headers=headers)
            try:
                items = self.al_decode(json.loads(res).get('pageProps').get('data')).get('players')
            except:
                items = []
            try:
                headers.pop('x-nextjs-data')
                for item in items:
                    for src in item:
                        lang = 'SUB' if src.get('languaje') == '0' else 'DUB'
                        sid = src.get('id')
                        surl = '{0}video/{1}'.format(self._API_URL, self.al_encode(sid))
                        slink = self._get_redirect_url(surl, headers=headers)
                        if slink:
                            source = {
                                'release_title': '{0} - Ep {1}'.format(title, episode),
                                'hash': slink + '|Referer={}'.format(self._BASE_URL),
                                'type': 'embed',
                                'quality': 'EQ',
                                'debrid_provider': '',
                                'provider': 'animelatino',
                                'size': 'NA',
                                'info': [lang, source_utils.get_embedhost(slink)],
                                'lang': 2 if lang == 'DUB' else 0
                            }
                            sources.append(source)
            except:
                pass

        return sources

    def al_decode(self, data):
        from resources.lib.ui import pyaes
        tkey = 'l7z8rIhQDXIH6pl66ZEQgPkNwkDlilgdOHMMWkxkzzE='
        t = json.loads(self._bdecode(data))
        ct = self._bdecode(t.get('value'), True)
        iv = self._bdecode(t.get('iv'), True)
        key = self._bdecode(tkey, True)
        decryptor = pyaes.Decrypter(pyaes.AESModeOfOperationCBC(key, iv))
        ddata = decryptor.feed(ct)
        ddata += decryptor.feed()
        return json.loads(ddata.decode('utf-8'))

    def al_encode(self, sid):
        import os
        import hashlib
        import hmac
        from resources.lib.ui import pyaes
        tkey = 'l7z8rIhQDXIH6pl66ZEQgPkNwkDlilgdOHMMWkxkzzE='
        key = self._bdecode(tkey, True)
        iv = os.urandom(16)
        encryptor = pyaes.Encrypter(pyaes.AESModeOfOperationCBC(key, iv))
        edata = encryptor.feed(str(sid))
        edata += encryptor.feed()
        et = self._bencode(edata)
        eiv = self._bencode(iv)
        mac = hmac.new(key, msg=(eiv + et).encode(), digestmod=hashlib.sha256).hexdigest()
        params = {
            'iv': eiv,
            'value': et,
            'mac': mac
        }
        return self._bencode(json.dumps(params))
