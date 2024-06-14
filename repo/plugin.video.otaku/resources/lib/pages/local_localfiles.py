import os
import re
import json

from functools import partial
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.ui import source_utils, client, control

PATH = control.getSetting('download.location')


class sources(BrowserBase):

    def get_sources(self, query, anilist_id, episode):
        filenames = os.listdir(PATH)
        clean_filenames = [re.sub(r'\[.*?]\s*', '', i) for i in filenames]
        filenames_query = ','.join(clean_filenames)
        r = client.request('https://armkai.vercel.app/api/fuzzypacks', params={"dict": filenames_query, "match": query})
        resp = json.loads(r)
        match_files = []
        for i in resp:
            if source_utils.is_file_ext_valid(clean_filenames[i]) and episode not in clean_filenames[i].rsplit('-', 1)[1]:
                continue
            match_files.append(filenames[i])
        mapfunc = partial(self.process_local_search, episode=episode)
        all_results = list(map(mapfunc, match_files))
        return all_results

    def process_local_search(self, f, episode):
        source = {
            'release_title': f,
            'hash': os.path.join(PATH, f),
            'type': 'local',
            'quality': source_utils.getQuality(f),
            'debrid_provider': 'local_files',
            'provider': 'Local',
            'episode_re': episode,
            'size': self._get_size(os.path.getsize(os.path.join(PATH, f))),
            'info': source_utils.getInfo(f),
            'lang': source_utils.getAudio_lang(f)
        }
        return source

    @staticmethod
    def get_title_clean(title):
        title = title.replace('(', '')
        title = title.replace(')', '')
        title = title.replace('-', '')
        title = '{} '.format(title)
        return title