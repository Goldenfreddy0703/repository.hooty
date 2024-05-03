import json
from six.moves import urllib_parse
from resources.lib.ui import client, database


class MALSYNC:
    def __init__(self):
        self.baseUrl = 'https://api.malsync.moe/'

    def _json_request(self, url):
        if url.startswith('/'):
            url = urllib_parse.urljoin(self.baseUrl, url)

        response = database.get(
            client.request,
            72,
            url,
            error=True,
            output='extended',
            timeout=30
        )
        data = {}
        if response and int(response[1]) < 300 and 'request failed!' not in response[0]:
            data = json.loads(response[0])
        return data

    def get_slugs(self, anilist_id, site=''):
        slugs = []
        if site in ['9anime', 'Gogoanime', 'Zoro']:
            url = '/mal/anime/anilist:{0}'.format(anilist_id)
            resp = self._json_request(url)['Sites'].get(site)
            if resp:
                for key in resp.keys():
                    slugs.append(resp[key].get('url'))

        return slugs
