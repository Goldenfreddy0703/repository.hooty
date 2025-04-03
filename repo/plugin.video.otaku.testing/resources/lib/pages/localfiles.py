import os
import re
import json

from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.ui import source_utils, control, client

PATH = control.getSetting('folder.location')


class Sources(BrowserBase):
    def __init__(self):
        self.local_files = []

    def get_sources(self, query, mal_id, episode, season):
        filenames = []
        for root, dirs, files in os.walk(PATH):
            for file in files:
                if source_utils.is_file_ext_valid(file):
                    full_path = os.path.join(root, file)
                    filenames.append({
                        'name': file,
                        'path': full_path
                    })

        filtered_filenames = source_utils.filter_sources('local', filenames, season, episode)
        filtered_out_filenames = source_utils.filter_out_sources('local', filenames)
        filenames = filtered_filenames + filtered_out_filenames
        clean_filenames = [re.sub(r'\[.*?]\s*', '', i['name'].replace(',', '')) for i in filenames]
        filenames_query = ','.join(clean_filenames)
        response = client.request('https://armkai.vercel.app/api/fuzzypacks', params={"dict": filenames_query, "match": query})
        resp = json.loads(response) if response else []
        match_files = [filenames[i] for i in resp]

        for file_info in match_files:
            filename = re.sub(r'\[.*?]', '', file_info['name']).lower()

            if not source_utils.is_file_ext_valid(filename):
                continue

            full_path = file_info['path']
            file_size = os.path.getsize(full_path)

            self.local_files.append(
                {
                    'release_title': file_info['name'],
                    'hash': full_path,
                    'provider': 'Local',
                    'type': 'local',
                    'quality': source_utils.getQuality(file_info['name']),
                    'debrid_provider': 'Local-Debrid',
                    'episode': episode,
                    'size': source_utils.get_size(file_size),
                    'seeders': 0,
                    'byte_size': file_size,
                    'info': source_utils.getInfo(file_info['name']),
                    'lang': source_utils.getAudio_lang(file_info['name']),
                    'channel': source_utils.getAudio_channel(file_info['name']),
                    'sub': source_utils.getSubtitle_lang(file_info['name'])
                }
            )
        return self.local_files
