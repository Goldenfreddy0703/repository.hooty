import re
import pickle
import base64

from functools import partial
from bs4 import BeautifulSoup
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.ui import database, source_utils, client, control
from resources.lib.debrid import Debrid
from resources.lib.indexers.simkl import SIMKLAPI
from resources.lib.endpoints import anidb


class Sources(BrowserBase):
    _BASE_URL = 'https://animetosho.org'

    def __init__(self):
        self.sources = []
        self.cached = []
        self.uncached = []
        self.anidb_id = None
        self.anidb_ep_id = None
        self.paging = control.getInt('animetosho.paging')

    def get_sources(self, show, mal_id, episode, status, media_type):
        if media_type == "movie":
            return self.get_movie_sources(show, mal_id)

        if 'part' in show.lower() or 'cour' in show.lower():
            part_match = re.search(r'(?:part|cour) ?(\d+)', show.lower())
            if part_match:
                part = int(part_match.group(1).strip())
            else:
                part = None
        else:
            part = None

        # If the part could not be determined from the query, try to get it from the MAL mappings.
        if part is None:
            mal_mapping = database.get_mappings(mal_id, 'mal_id')
            if mal_mapping and 'thetvdb_part' in mal_mapping:
                part = mal_mapping['thetvdb_part']

        episode_sources = self.get_episode_sources(show, mal_id, episode, part, status)
        show_sources = self.get_show_sources(show, mal_id, episode, part)
        self.sources = episode_sources + show_sources

        self.append_cache_uncached_noduplicates()
        return {'cached': self.cached, 'uncached': self.uncached}

    def get_episode_sources(self, show, mal_id, episode, part, status):
        # Retrieve anidb info for the show and episode
        show_meta = database.get_show_meta(mal_id)
        if show_meta:
            meta_ids = pickle.loads(show_meta['meta_ids'])
            self.anidb_id = meta_ids.get('anidb_id')
            if not self.anidb_id:
                ids = SIMKLAPI().get_mapping_ids('mal', mal_id)
                if ids:
                    self.anidb_id = meta_ids['anidb_id'] = ids['anidb']
                    database.update_show_meta(mal_id, meta_ids, pickle.loads(show_meta['art']))
        if self.anidb_id:
            episode_meta = database.get_episode(mal_id, episode)
            if episode_meta:
                self.anidb_ep_id = episode_meta.get('anidb_ep_id')
            if not self.anidb_ep_id:
                anidb_meta = anidb.get_episode_meta(self.anidb_id)
                anidb_meta = {x: v for x, v in anidb_meta.items() if x.isdigit()}
                for anidb_ep in anidb_meta:
                    database.update_episode_column(mal_id, anidb_ep, 'anidb_ep_id', anidb_meta[anidb_ep]['anidb_id'])

        animetosho_sources = []

        season = database.get_episode(mal_id)['season']
        season_zfill = str(season).zfill(2)
        episode_zfill = episode.zfill(2)
        # Build a query incorporating the episode and season info.
        query = f'{show} "- {episode_zfill}"'
        query += f'|"S{season_zfill}E{episode_zfill}"'

        params = {
            'q': self._sphinx_clean(query),
            'qx': 1,
            's': 'downloads',
            'o': 'desc'
        }
        if self.anidb_id:
            params['aids'] = self.anidb_id

        animetosho_sources += self.process_animetosho_episodes(f'{self._BASE_URL}/search', params, mal_id, episode_zfill, season_zfill, part)

        # For finished series, include batch/complete series results.
        if status in ["FINISHED", "Finished Airing"]:
            batch_terms = ["Batch", "Complete Series"]
            episodes_info = pickle.loads(database.get_show(mal_id)['kodi_meta'])['episodes']
            episode_formats = []
            if episodes_info:
                episode_formats = [f'01-{episode_zfill}', f'01~{episode_zfill}', f'01 - {episode_zfill}', f'01 ~ {episode_zfill}']
            batch_query = f'{show} ("' + '"|"'.join(batch_terms + episode_formats) + '")'
            params = {
                'q': self._sphinx_clean(batch_query),
                'qx': 1,
                's': 'seeders',
                'o': 'desc'
            }
            if self.anidb_id:
                params['aids'] = self.anidb_id
            animetosho_sources += self.process_animetosho_episodes(f'{self._BASE_URL}/search', params, mal_id, episode_zfill, season_zfill, part)

        # Additional query without explicit sorting.
        params = {
            'q': self._sphinx_clean(query),
            'qx': 1
        }
        if self.anidb_id:
            params['aids'] = self.anidb_id
        animetosho_sources += self.process_animetosho_episodes(f'{self._BASE_URL}/search', params, mal_id, episode_zfill, season_zfill, part)

        # If the show includes a season number, try additional variations.
        if 'season' in show.lower():
            show_variations = re.split(r'season\s*\d+', show.lower())
            cleaned_variations = [self._sphinx_clean(var.strip() + ')') for var in show_variations if var.strip()]
            params = {
                'q': '|'.join(cleaned_variations),
                'qx': 1
            }
            if self.anidb_id:
                params['aids'] = self.anidb_id
            animetosho_sources += self.process_animetosho_episodes(f'{self._BASE_URL}/search', params, mal_id, episode_zfill, season_zfill, part)
        return animetosho_sources

    def get_show_sources(self, show, mal_id, episode, part):
        season = database.get_episode(mal_id)['season']
        season_zfill = str(season).zfill(2)
        episode_zfill = episode.zfill(2)

        # For shows, we can use process_animetosho_episodes
        show_meta = database.get_show_meta(mal_id)
        if show_meta:
            meta_ids = pickle.loads(show_meta['meta_ids'])
            self.anidb_id = meta_ids.get('anidb_id')
            if not self.anidb_id:
                ids = SIMKLAPI().get_mapping_ids('mal', mal_id)
                if ids:
                    self.anidb_id = meta_ids['anidb_id'] = ids['anidb']
                    database.update_show_meta(mal_id, meta_ids, pickle.loads(show_meta['art']))

        query = self._clean_title(show)
        params = {
            'q': self._sphinx_clean(query),
            'qx': 1,
            's': 'seeders',
            'o': 'desc'
        }
        if self.anidb_id:
            params['aids'] = self.anidb_id

        animetosho_sources = self.process_animetosho_episodes(f'{self._BASE_URL}/search', params, mal_id, episode_zfill, season_zfill, part)
        return animetosho_sources

    def get_movie_sources(self, show, mal_id):
        # For movies we now use process_animetosho_movie
        show_meta = database.get_show_meta(mal_id)
        if show_meta:
            meta_ids = pickle.loads(show_meta['meta_ids'])
            self.anidb_id = meta_ids.get('anidb_id')
            if not self.anidb_id:
                ids = SIMKLAPI().get_mapping_ids('mal', mal_id)
                if ids:
                    self.anidb_id = meta_ids['anidb_id'] = ids['anidb']
                    database.update_show_meta(mal_id, meta_ids, pickle.loads(show_meta['art']))

        query = self._clean_title(show)
        params = {
            'q': self._sphinx_clean(query),
            'qx': 1,
            's': 'seeders',
            'o': 'desc'
        }
        if self.anidb_id:
            params['aids'] = self.anidb_id

        self.sources = self.process_animetosho_movie(f'{self._BASE_URL}/search', params, mal_id)
        self.append_cache_uncached_noduplicates()
        return {'cached': self.cached, 'uncached': self.uncached}

    def process_animetosho_episodes(self, url, params, mal_id, episode, season, part):
        response = client.request(url, params=params)
        if response:
            html = response
            soup = BeautifulSoup(html, "html.parser")
            soup_all = soup.find('div', id='content').find_all('div', class_='home_list_entry')
            rex = r'(magnet:)+[^"]*'
            list_ = []
            for entry in soup_all:
                list_item = {
                    'name': entry.find('div', class_='link').a.text,
                    'magnet': entry.find('a', {'href': re.compile(rex)}).get('href'),
                    'size': entry.find('div', class_='size').text,
                    'downloads': 0,
                    'torrent': entry.find('a', class_='dllink').get('href')
                }
                try:
                    list_item['seeders'] = int(re.match(r'Seeders: (\d+)', entry.find('span', {'title': re.compile(r'Seeders')}).get('title')).group(1))
                except AttributeError:
                    list_item['seeders'] = -1

                try:
                    list_item['hash'] = re.match(r'https://animetosho.org/storage/torrent/([^/]+)', list_item['torrent']).group(1)
                except AttributeError:
                    try:
                        hash_32 = re.search(r'btih:(\w+)&tr=http', list_item['magnet']).group(1)
                        list_item['hash'] = base64.b16encode(base64.b32decode(hash_32)).decode().lower()
                    except AttributeError:
                        continue

                list_.append(list_item)

            filtered_list = source_utils.filter_sources('animetosho', list_, mal_id, int(season), int(episode), part, anidb_id=self.anidb_id)

            cache_list, uncashed_list_ = Debrid().torrentCacheCheck(filtered_list)
            cache_list = sorted(cache_list, key=lambda k: k['downloads'], reverse=True)

            uncashed_list = [i for i in uncashed_list_ if i['seeders'] != 0]
            uncashed_list = sorted(uncashed_list, key=lambda k: k['seeders'], reverse=True)

            mapfunc = partial(self.parse_animetosho_view, episode=episode)
            all_results = list(map(mapfunc, cache_list))
            if control.settingids.showuncached:
                mapfunc2 = partial(self.parse_animetosho_view, episode=episode, cached=False)
                all_results += list(map(mapfunc2, uncashed_list))
            return all_results
        return []

    def process_animetosho_movie(self, url, params):
        response = client.request(url, params=params)
        if response:
            html = response
            soup = BeautifulSoup(html, "html.parser")
            # Assuming the movie results use the same container as episodes:
            soup_all = soup.find('div', id='content').find_all('div', class_='home_list_entry')
            rex = r'(magnet:)+[^"]*'
            list_ = []
            for entry in soup_all:
                list_item = {
                    'name': entry.find('div', class_='link').a.text,
                    'magnet': entry.find('a', {'href': re.compile(rex)}).get('href'),
                    'size': entry.find('div', class_='size').text,
                    'downloads': 0,
                    'torrent': entry.find('a', class_='dllink').get('href')
                }
                try:
                    list_item['seeders'] = int(re.match(r'Seeders: (\d+)', entry.find('span', {'title': re.compile(r'Seeders')}).get('title')).group(1))
                except AttributeError:
                    list_item['seeders'] = -1

                try:
                    list_item['hash'] = re.match(r'https://animetosho.org/storage/torrent/([^/]+)', list_item['torrent']).group(1)
                except AttributeError:
                    try:
                        hash_32 = re.search(r'btih:(\w+)&tr=http', list_item['magnet']).group(1)
                        list_item['hash'] = base64.b16encode(base64.b32decode(hash_32)).decode().lower()
                    except AttributeError:
                        continue

                list_.append(list_item)

            # For movies we don't filter by season/episode
            filtered_list = source_utils.filter_sources('animetosho', list_)
            cache_list, uncashed_list_ = Debrid().torrentCacheCheck(filtered_list)
            cache_list = sorted(cache_list, key=lambda k: k['downloads'], reverse=True)
            uncashed_list = sorted([i for i in uncashed_list_ if i['seeders'] != 0], key=lambda k: k['seeders'], reverse=True)

            mapfunc = partial(self.parse_animetosho_view, episode="1")
            all_results = list(map(mapfunc, cache_list))
            if control.settingids.showuncached:
                mapfunc2 = partial(self.parse_animetosho_view, episode="1", cached=False)
                all_results += list(map(mapfunc2, uncashed_list))
            return all_results
        return []

    @staticmethod
    def parse_animetosho_view(res, episode, cached=True):
        source = {
            'release_title': res['name'],
            'hash': res['hash'],
            'type': 'torrent',
            'quality': source_utils.getQuality(res['name']),
            'debrid_provider': res.get('debrid_provider'),
            'provider': 'animetosho',
            'episode_re': episode,
            'size': res['size'],
            'info': source_utils.getInfo(res['name']),
            'byte_size': 0,
            'lang': source_utils.getAudio_lang(res['name']),
            'channel': source_utils.getAudio_channel(res['name']),
            'sub': source_utils.getSubtitle_lang(res['name']),
            'cached': cached,
            'seeders': res['seeders'],
        }

        if source.get('debrid_provider', '').lower() == 'easydebrid':
            source['type'] = 'hoster'

        match = re.match(r'(\d+).(\d+) (\w+)', res['size'])
        if match:
            source['byte_size'] = source_utils.convert_to_bytes(float(f'{match.group(1)}.{match.group(2)}'), match.group(3))
        if not cached:
            source['magnet'] = res['magnet']
            source['type'] += ' (uncached)'

        return source

    def append_cache_uncached_noduplicates(self):
        unique = {}
        for source in self.sources:
            key = source.get('hash')
            if not key:
                continue
            if key in unique:
                current = unique[key]
                if source.get('seeders', -1) > current.get('seeders', -1):
                    unique[key] = source
                elif (source.get('seeders', -1) == current.get('seeders', -1) and
                      source.get('byte_size', 0) > current.get('byte_size', 0)):
                    unique[key] = source
            else:
                unique[key] = source

        self.cached = []
        self.uncached = []
        for source in unique.values():
            if source['cached']:
                self.cached.append(source)
            else:
                self.uncached.append(source)
