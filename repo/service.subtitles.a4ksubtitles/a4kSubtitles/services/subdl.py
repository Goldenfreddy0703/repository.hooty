# -*- coding: utf-8 -*-

def build_search_requests(core, service_name, meta):
    apikey = core.kodi.get_setting(service_name, 'apikey')

    if not apikey:
        core.kodi.notification('SubDL requires API Key! Enter it in the addon Settings->Accounts or disable the service.')
        core.logger.error('%s - API Key is missing' % service_name)
        return []

    lang_ids = core.utils.get_lang_ids(meta.languages, core.kodi.xbmc.ISO_639_1)
    params = {
        'languages': ','.join(lang_ids),
        'type': 'movie' if not meta.is_tvshow else 'tv',
    }
    headers = {
        'Authorization': 'Bearer %s' % apikey
    }

    if meta.is_tvshow:
        params.update({
            'film_name': meta.tvshow,
            'file_name': meta.filename_without_ext,
            'season': meta.season,
            'episode': meta.episode,
        })

        if meta.tvshow_year:
            params['year'] = meta.tvshow_year
    else:
        params.update({
            'imdb_id': meta.imdb_id,
            'year': meta.year,
        })

    request = {
        'method': 'GET',
        'url': 'https://api.subdl.com/api/v2/subtitles/search',
        'params': params,
        'headers': headers
    }

    return [request]

def parse_search_response(core, service_name, meta, response):
    try:
        results = core.json.loads(response.text)
    except Exception as exc:
        core.logger.error('%s - %s' % (service_name, exc))
        return []

    if 'error' in results:
        error = results['error']
        core.logger.error('%s - %s' % (service_name, error.get('message', error) if isinstance(error, dict) else error))
        return []

    subtitles = results.get('subtitles', [])
    core.logger.debug('%s - Found %d subtitles' % (service_name, len(subtitles)))

    service = core.services[service_name]
    lang_ids = core.utils.get_lang_ids(meta.languages, core.kodi.xbmc.ISO_639_1)

    def map_result(result):
        filename = result['release_name']
        lang_code = result['language'].lower()
        lang = meta.languages[lang_ids.index(lang_code)] if lang_code in lang_ids else lang_code

        return {
            'service_name': service_name,
            'service': service.display_name,
            'lang': lang,
            'name': filename,
            'rating': 0,
            'lang_code': lang_code,
            'sync': 'false',
            'impaired': 'true' if result['hi'] else 'false',
            'color': 'springgreen',
            'action_args': {
                'url': result['url'],
                'lang': lang,
                'filename': filename,
            }
        }

    return list(map(map_result, subtitles))

def build_download_request(core, service_name, args):
    request = {
        'method': 'GET',
        'url': 'https://dl.subdl.com' + args['url'],
        'stream': True
    }

    core.logger.debug('%s - Downloading %s' % (service_name, args['filename']))

    return request
