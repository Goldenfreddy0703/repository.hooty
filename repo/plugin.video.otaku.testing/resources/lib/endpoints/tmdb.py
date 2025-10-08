from resources.lib.ui import client, database

api_info = database.get_info('TMDB')
apiKey = api_info['api_key']
baseUrl = "https://api.themoviedb.org/3/"
thumbPath = "https://image.tmdb.org/t/p/w500"
backgroundPath = "https://image.tmdb.org/t/p/original"


def getArt(meta_ids, mtype):
    art = {}
    mid = meta_ids.get('themoviedb_id')
    if mid is None:
        tvdb = meta_ids.get('thetvdb_id')
        if tvdb:
            params = {
                'external_source': 'tvdb_id',
                "api_key": apiKey
            }
            response = client.get(f'{baseUrl}find/{tvdb}', params=params)
            res = response.json() if response else {}
            res = res.get('tv_results')
            if res:
                mid = res[0].get('id')

    if mid:
        params = {
            'include_image_language': 'en,ja,null',
            "api_key": apiKey
        }
        response = client.get(f'{baseUrl}{mtype[0:5]}/{mid}/images', params=params)
        res = response.json() if response else {}

        if res:
            if res.get('backdrops'):
                items = []
                items2 = []
                for item in res['backdrops']:
                    if item.get('file_path'):
                        items.append(backgroundPath + item['file_path'])
                        items2.append(thumbPath + item['file_path'])
                art['fanart'] = items
                art['thumb'] = items2

            if res.get('logos'):
                items = [backgroundPath + item["file_path"] for item in res['logos'] if item.get('file_path')]
                art['clearart'] = items
    return art


def get_episode_titles(tmdb_id, season_number, episode_number):
    params = {
        'include_image_language': 'en,ja,null',
        "api_key": apiKey
    }
    response = client.get(f'{baseUrl}tv/{tmdb_id}/season/{season_number}/episode/{episode_number}/translations', params=params)
    res = response.json() if response else {}

    # Extract all 'name' fields from translations
    names = []
    translations = res.get('translations', [])
    for t in translations:
        data = t.get('data', {})
        name = data.get('name')
        if name:
            names.append(name)
    return names
