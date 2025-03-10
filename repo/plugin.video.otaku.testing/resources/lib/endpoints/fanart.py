import json
from resources.lib.ui import client, control, database

api_info = database.get_info('Fanart-TV')
api_key = api_info['api_key']
baseUrl = "https://webservice.fanart.tv/v3"
lang = ['en', 'ja', '']
headers = {'Api-Key': api_key}
language = ["ja", 'en'][control.getInt("titlelanguage")]


def getArt(meta_ids, mtype):
    art = {}
    if mid := meta_ids.get('themoviedb_id') if mtype == 'movies' else meta_ids.get('thetvdb_id'):
        response = client.request(f'{baseUrl}/{mtype}/{mid}', headers=headers)
        res = json.loads(response) if response else {}
        if res:
            if mtype == 'movies':
                if res.get('moviebackground'):
                    items = [item.get('url') for item in res['moviebackground'] if item.get('lang') in lang]
                    art['fanart'] = items
                if res.get('moviethumb'):
                    items = [item.get('url') for item in res['moviethumb'] if item.get('lang') in lang]
                    art['thumb'] = items
            else:
                if res.get('showbackground'):
                    items = [item.get('url') for item in res['showbackground'] if item.get('lang') in lang]
                    art['fanart'] = items
                if res.get('tvthumb'):
                    items = [item.get('url') for item in res['tvthumb'] if item.get('lang') in lang]
                    art['thumb'] = items

            if res.get('clearart'):
                items = [item.get('url') for item in res['clearart'] if item.get('lang') in lang]
                art['clearart'] = items
            elif res.get('hdclearart'):
                items = [item.get('url') for item in res['hdclearart'] if item.get('lang') in lang]
                art['clearart'] = items
            elif res.get('hdmovieclearart'):
                items = [item.get('url') for item in res['hdmovieclearart'] if item.get('lang') in lang]
                art['clearart'] = items

            if res.get('clearlogo'):
                items = sorted([item for item in res['clearlogo'] if item.get('lang') in lang], key=lambda x: int(x['id']))
                logos = []
                try:
                    logos.append(next(x['url'] for x in items if x['lang'] == language))
                except StopIteration:
                    pass
                if not logos:
                    try:
                        logos.append(next(x['url'] for x in items))
                    except StopIteration:
                        pass
                art['clearlogo'] = logos
            elif res.get('hdtvlogo'):
                items = sorted([item for item in res['hdtvlogo'] if item.get('lang') in lang], key=lambda x: int(x['id']))
                logos = []
                try:
                    logos.append(next(x['url'] for x in items if x['lang'] == language))
                except StopIteration:
                    pass
                if not logos:
                    try:
                        logos.append(next(x['url'] for x in items))
                    except StopIteration:
                        pass
                art['clearlogo'] = logos
            elif res.get('hdmovielogo'):
                items = sorted([item for item in res['hdmovielogo'] if item.get('lang') in lang], key=lambda x: int(x['id']))
                logos = []
                try:
                    logos.append(next(x['url'] for x in items if x['lang'] == language))
                except StopIteration:
                    pass
                if not logos:
                    try:
                        logos.append(next(x['url'] for x in items))
                    except StopIteration:
                        pass
                art['clearlogo'] = logos
    return art
