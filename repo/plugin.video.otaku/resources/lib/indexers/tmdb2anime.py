import json
from six.moves import urllib_parse
from resources.lib.ui import client, database


class TMDB2ANIME:
    def __init__(self):
        self.baseUrl = 'https://tmdb2anilist.slidemovies.org/'

    def _json_request(self, url, params=None):
        if url.startswith('/'):
            url = urllib_parse.urljoin(self.baseUrl, url)

        response = database.get(
            client.request,
            4,
            url,
            params=params,
            error=True,
            output='extended',
            timeout=30
        )
        data = {}
        if response and int(response[1]) < 300 and 'request failed!' not in response[0]:
            data = json.loads(response[0])
        return data

    def get_ids(self, tmdb_id, season=None):
        params = {'id': tmdb_id}
        if season is None:
            url = '/movie/'
        else:
            url = '/tv/'
            params.update({'s': season})

        return self._json_request(url, params)
