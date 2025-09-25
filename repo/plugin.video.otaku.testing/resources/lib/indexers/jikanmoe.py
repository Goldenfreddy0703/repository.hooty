import pickle
import datetime
import time
import json
import random

from functools import partial
from resources.lib.ui import utils, database, client, control
from resources.lib import indexers


class JikanAPI:
    def __init__(self):
        self.baseUrl = "https://api.jikan.moe/v4"

    def get_anime_info(self, mal_id):
        response = client.request(f'{self.baseUrl}/anime/{mal_id}')
        if response:
            return json.loads(response)['data']

    def get_episode_meta(self, mal_id):
        res_data = []
        url = f'{self.baseUrl}/anime/{mal_id}/episodes'
        response = client.request(url)
        if response:
            res = json.loads(response)
            if not res['pagination']['has_next_page']:
                res_data = res['data']
            else:
                res_data = res['data']
                for i in range(2, res['pagination']['last_visible_page'] + 1):
                    params = {
                        'page': i
                    }
                    response = client.request(url, params=params)
                    if response:
                        r = json.loads(response)
                        if not r['pagination']['has_next_page']:
                            res_data += r['data']
                            break
                        res_data += r['data']
                        if i % 3 == 0:
                            time.sleep(2)
        return res_data

    @staticmethod
    def parse_episode_view(res, mal_id, season, poster, fanart, clearart, clearlogo, eps_watched, update_time, tvshowtitle, dub_data, filler_data, episodes=None):
        kodi_meta = pickle.loads(database.get_show(mal_id)['kodi_meta'])
        episode = res['mal_id']
        url = f"{mal_id}/{episode}"
        title = res.get('title')
        if not title:
            title = res["episode"]
        image = res['images']['jpg']['image_url'] if res.get('images') else poster
        info = {
            'UniqueIDs': {
                'mal_id': str(mal_id),
                **database.get_mapping_ids(mal_id, 'mal_id')
            },
            'title': title,
            'season': season,
            'episode': episode,
            'plot': 'No plot available',
            'tvshowtitle': tvshowtitle,
            'mediatype': 'episode',
            'status': kodi_meta.get('status'),
            'genre': kodi_meta.get('genre'),
            'country': kodi_meta.get('country'),
            'cast': kodi_meta.get('cast'),
            'studio': kodi_meta.get('studio'),
            'mpaa': kodi_meta.get('mpaa'),
        }

        if eps_watched and int(eps_watched) >= episode:
            info['playcount'] = 1

        try:
            info['rating'] = {'score': float(res['score'])}
        except (KeyError, TypeError):
            pass

        try:
            info['aired'] = res['aired'][:10]
        except (KeyError, TypeError):
            pass

        try:
            filler = filler_data[episode - 1]
        except (IndexError, TypeError):
            filler = ''

        parsed = indexers.update_database(mal_id, update_time, res, url, image, info, season, episode, episodes, title, fanart, poster, clearart, clearlogo, dub_data, filler)
        return parsed

    def process_episode_view(self, mal_id, poster, fanart, clearart, clearlogo, eps_watched, tvshowtitle, dub_data, filler_data):
        update_time = datetime.date.today().isoformat()
        result = self.get_anime_info(mal_id)
        if not result:
            return []

        title_list = [name['title'] for name in result['titles']]
        season = utils.get_season(title_list, mal_id)

        result_ep = self.get_episode_meta(mal_id)
        # kodi_episodes = kodi_meta['episodes']
        # if kodi_episodes:
        #     control.print(f"Kodi Episodes: {kodi_episodes}, Jikan Episodes: {len(result_ep)}")
        #     if len(result_ep) != kodi_episodes:
        #         return []

        mapfunc = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, clearart=clearart, clearlogo=clearlogo, eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data)
        all_results = sorted(list(map(mapfunc, result_ep)), key=lambda x: x['info']['episode'])

        if control.getBool('override.meta.api') and control.getBool('override.meta.notify'):
            control.notify("Jikanmoe", f'{tvshowtitle} Added to Database', icon=poster)
        return all_results

    def append_episodes(self, mal_id, episodes, eps_watched, poster, fanart, clearart, clearlogo, tvshowtitle, filler_data=None, dub_data=None):
        update_time, diff = indexers.get_diff(episodes[-1])
        if diff > control.getInt('interface.check.updates'):
            result = self.get_episode_meta(mal_id)
            season = episodes[0]['season']
            mapfunc2 = partial(self.parse_episode_view, mal_id=mal_id, season=season, poster=poster, fanart=fanart, clearart=clearart, clearlogo=clearlogo, eps_watched=eps_watched, update_time=update_time, tvshowtitle=tvshowtitle, dub_data=dub_data, filler_data=filler_data, episodes=episodes)
            all_results = list(map(mapfunc2, result))
            if control.getBool('override.meta.api') and control.getBool('override.meta.notify'):
                control.notify("Jikanmoe", f'{tvshowtitle} Appended to Database', icon=poster)
        else:
            mapfunc1 = partial(indexers.parse_episodes, eps_watched=eps_watched, dub_data=dub_data)
            all_results = list(map(mapfunc1, episodes))
        return all_results

    def get_episodes(self, mal_id, show_meta):
        kodi_meta = pickle.loads(database.get_show(mal_id)['kodi_meta'])
        kodi_meta.update(pickle.loads(show_meta['art']))
        fanart = kodi_meta.get('fanart')
        poster = kodi_meta.get('poster')
        clearart = random.choice(kodi_meta['clearart']) if kodi_meta.get('clearart') else ''
        clearlogo = random.choice(kodi_meta['clearlogo']) if kodi_meta.get('clearlogo') else ''
        tvshowtitle = kodi_meta['title_userPreferred']
        if not (eps_watched := kodi_meta.get('eps_watched')) and control.settingids.watchlist_data:
            from resources.lib.WatchlistFlavor import WatchlistFlavor
            flavor = WatchlistFlavor.get_update_flavor()
            if flavor and flavor.flavor_name in control.enabled_watchlists():
                data = flavor.get_watchlist_anime_entry(mal_id)
                if data.get('eps_watched'):
                    eps_watched = kodi_meta['eps_watched'] = data['eps_watched']
                    database.update_kodi_meta(mal_id, kodi_meta)
        episodes = database.get_episode_list(mal_id)
        dub_data = indexers.process_dub(mal_id, kodi_meta['ename']) if control.getBool('jz.dub') else None
        if episodes:
            if kodi_meta['status'] not in ["FINISHED", "Finished Airing"]:
                from resources.lib.endpoints import anime_filler
                filler_data = anime_filler.get_data(kodi_meta['ename'])
                return self.append_episodes(mal_id, episodes, eps_watched, poster, fanart, clearart, clearlogo, tvshowtitle, filler_data, dub_data)
            return indexers.process_episodes(episodes, eps_watched, dub_data)

        if kodi_meta['episodes'] is None or kodi_meta['episodes'] > 99:
            from resources.lib.endpoints import anime_filler
            filler_data = anime_filler.get_data(kodi_meta['ename'])
        else:
            filler_data = None
        return self.process_episode_view(mal_id, poster, fanart, clearart, clearlogo, eps_watched, tvshowtitle, dub_data, filler_data)

    def get_anime(self, filter_type, page):
        perpage = 25
        params = {
            "limit": perpage,
            "page": page,
            "filter": filter_type
        }
        response = client.request(f'{self.baseUrl}/top/anime', params=params)
        if response:
            return json.loads(response)
