from resources.lib.ui import client, database
import json


class TVDBAPI:
    def __init__(self):
        self.apiKey = {'apikey': 'edae60dc-1b44-4bac-8db7-65c0aaf5258b'}
        self.headers = {'User-Agent': 'TheTVDB v.4 TV Scraper for Kodi'}
        self.baseUrl = 'https://api4.thetvdb.com/v4/'
        self.art = {}
        self.request_response = None
        self.threads = []

    def get_token(self):
        res = client.request(
            self.baseUrl + 'login',
            headers=self.headers,
            post=self.apiKey,
            jpost=True
        )
        data = json.loads(res)
        return data['data'].get('token')

    def get_request(self, url):
        token = database.get(self.get_token, 24)
        self.headers.update({'Authorization': 'Bearer {0}'.format(token)})
        url = self.baseUrl + url

        response = client.request(url, headers=self.headers)
        if response:
            response = json.loads(response).get('data')
            self.request_response = response
            return response
        else:
            return None

    def get_imdb_id(self, tvdb_id):
        imdb_id = None
        url = 'series/{}/extended'.format(tvdb_id)
        data = self.get_request(url)
        if data:
            imdb_id = [x.get('id') for x in data['remoteIds'] if x.get('type') == 2]
        return imdb_id[0] if imdb_id else None

    def get_seasons(self, tvdb_id):
        url = 'seasons/{}/extended'.format(tvdb_id)
        data = self.get_request(url)
        return data
