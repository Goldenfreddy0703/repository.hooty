import json
import pickle
import random
from functools import partial

from resources.lib.ui import client, database, utils


class SIMKLAPI:
    def __init__(self):
        self.ClientID = "5178a709b7942f1f5077b737b752eea0f6dee684d0e044fa5acee8822a0cbe9b"
        self.baseUrl = "https://api.simkl.com/"
        self.imagePath = "https://simkl.net/episodes/%s_w.jpg"
        self.art = {}
        self.request_response = None
        self.threads = []

    def _to_url(self, url=''):
        if url.startswith("/"):
            url = url[1:]

        return "%s/%s" % (self.baseUrl[:-1], url)

    def _json_request(self, url, data=''):
        response = database.get(client.request, 4, url, params=data)
        response = json.loads(response)
        return response

    def _parse_episode_view(self, res, anilist_id, poster, fanart, eps_watched, filter_lang, update_time):
        url = "%s/%s/" % (anilist_id, res['episode'])
        if isinstance(fanart, list):
            fanart = random.choice(fanart)
        if filter_lang:
            url += filter_lang

        name = 'Ep. %d (%s)' % (res['episode'], res.get('title'))

        if res['img'] is not None:
            image = self.imagePath % res['img']
        else:
            show_meta = database.get_show_meta(anilist_id)
            if show_meta:
                thumbs = pickle.loads(show_meta.get('art')).get('thumb')
                if thumbs:
                    image = random.choice(thumbs)
                else:
                    image = fanart or poster
            else:
                image = fanart or poster

        info = {}
        info['plot'] = res['description']
        info['title'] = res['title']
        info['season'] = 1
        info['episode'] = res['episode']
        try:
            if int(eps_watched) >= res['episode']:
                info['playcount'] = 1
        except:
            pass
        try:
            info['aired'] = res['date'][:10]
        except:
            pass
        info['tvshowtitle'] = pickle.loads(database.get_show(anilist_id)['kodi_meta'])['title_userPreferred']
        info['mediatype'] = 'episode'
        parsed = utils.allocate_item(name, "play/" + str(url), False, image, info, fanart, poster)
        database._update_episode(anilist_id, 1, res['episode'], '', update_time, parsed)
        return parsed

    def _process_episode_view(self, anilist_id, json_resp, filter_lang, base_plugin_url, page):
        from datetime import date
        update_time = date.today().isoformat()
        kodi_meta = pickle.loads(database.get_show(anilist_id)['kodi_meta'])
        show_meta = database.get_show_meta(anilist_id)
        if show_meta:
            kodi_meta.update(pickle.loads(show_meta.get('art')))
        fanart = kodi_meta.get('fanart')
        poster = kodi_meta.get('poster')
        eps_watched = kodi_meta.get('eps_watched')
        json_resp = [x for x in json_resp if x['type'] == 'episode']
        mapfunc = partial(self._parse_episode_view, anilist_id=anilist_id, poster=poster, fanart=fanart, eps_watched=eps_watched, filter_lang=filter_lang, update_time=update_time)
        all_results = list(map(mapfunc, json_resp))

        return all_results

    def get_anime(self, anilist_id, filter_lang):
        show = database.get_show(anilist_id)
        # show_meta = database.get_show_meta(anilist_id)

        if show['simkl_id']:
            return (self.get_episodes(anilist_id, filter_lang), 'episodes')

        # show_meta = show_meta['meta_ids']
        mal_id = show['mal_id']

        if not mal_id:
            mal_id = self.get_mal_id(anilist_id)
            database.add_mapping_id(anilist_id, 'mal_id', str(mal_id))

        simkl_id = str(self.get_anime_id(mal_id))
        database.add_mapping_id(anilist_id, 'simkl_id', simkl_id)

        return (self.get_episodes(anilist_id, filter_lang), 'episodes')

    def _get_episodes(self, anilist_id):
        simkl_id = database.get_show(anilist_id)['simkl_id']
        data = {
            'extended': 'full',
        }
        url = self._to_url("anime/episodes/%s" % str(simkl_id))
        json_resp = self._json_request(url, data)
        return json_resp

    def get_episodes(self, anilist_id, filter_lang=None, page=1):
        episodes = database.get(self._get_episodes, 6, anilist_id)
        return self._process_episode_view(anilist_id, episodes, filter_lang, "animes_page/%s/%%d" % anilist_id, page)

    def get_anime_search(self, q):
        data = {
            "q": q,
            "client_id": self.ClientID
        }
        json_resp = self._json_request("https://api.simkl.com/search/anime", data)
        if not json_resp:
            return []

        anime_id = json_resp[0]['ids']['simkl_id']
        return anime_id

    def get_anime_id(self, mal_id):
        data = {
            "mal": mal_id,
            "client_id": self.ClientID,
        }
        url = self._to_url("search/id")
        json_resp = self._json_request(url, data)
        if not json_resp:
            return []

        anime_id = json_resp[0]['ids'].get('simkl')
        return anime_id

    def get_mal_id(self, anilist_id):
        arm_resp = self._json_request("https://arm2.vercel.app/api/search?type=anilist&id={}".format(anilist_id))
        mal_id = arm_resp["mal"]
        return mal_id
