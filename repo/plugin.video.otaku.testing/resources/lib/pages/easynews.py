# Easynews episode/movie search — results resolve as hoster + Easynews provider.
import pickle
import re

from resources.lib.debrid import easynews as easynews_debrid
from resources.lib.ui import database, source_utils, control
from resources.lib.ui.BrowserBase import BrowserBase


def _simplify_title(q):
    if not q:
        return ''
    s = q.split('|')[0].strip()
    if s.startswith('(') and ')' in s:
        s = s[1:s.index(')')]
    return re.sub(r'\s+', ' ', s).strip()


class Sources(BrowserBase):
    def get_sources(self, query, mal_id, episode, status, media_type, season=None, part=None):
        if not control.easynews_enabled():
            return {'cached': [], 'uncached': []}

        title = _simplify_title(query)
        if media_type == 'movie':
            search_q = self._movie_query(mal_id, title)
        else:
            ez_ep = str(episode).zfill(2) if episode is not None else '01'
            sz = str(season).zfill(2) if season else '01'
            search_q = f'{title} S{sz}E{ez_ep}'

        if not search_q.strip():
            return {'cached': [], 'uncached': []}

        rows = easynews_debrid.Easynews().search(search_q)

        if not rows:
            return {'cached': [], 'uncached': []}

        names = [r['name'] for r in rows]
        match_idx = source_utils.get_fuzzy_match(query, names)
        if not match_idx:
            match_idx = list(range(min(20, len(rows))))
        else:
            match_idx = match_idx[:30]
        cached = []
        for i in match_idx:
            row = rows[i]
            name = row['name']
            url_dl = row['url_dl']
            raw = row.get('rawSize') or 0
            src = {
                'release_title': name,
                'hash': url_dl,
                'type': 'hoster',
                'quality': source_utils.getQuality(name),
                'debrid_provider': 'Easynews',
                'provider': 'easynews',
                'episode_re': str(episode).zfill(2) if episode is not None else '01',
                'size': source_utils.get_size(raw),
                'byte_size': int(raw),
                'info': source_utils.getInfo(name),
                'lang': source_utils.getAudio_lang(name),
                'channel': source_utils.getAudio_channel(name),
                'sub': source_utils.getSubtitle_lang(name),
                'cached': True,
                'seeders': 0,
            }
            cached.append(src)
        return {'cached': cached, 'uncached': []}

    @staticmethod
    def _movie_query(mal_id, title):
        try:
            row = database.get_show(mal_id)
            if row and row.get('kodi_meta'):
                meta = pickle.loads(row['kodi_meta'])
                year = meta.get('year') or meta.get('start_date', '')[:4]
                if year:
                    return f'{title} {year}'
        except Exception:
            pass
        return title
