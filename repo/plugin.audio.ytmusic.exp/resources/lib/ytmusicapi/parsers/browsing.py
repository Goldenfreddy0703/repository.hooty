from typing import List, Dict
from .utils import *
from .songs import *
from ytmusicapi.helpers import i18n


class Parser:
    def __init__(self, language):
        self.lang = language

    def parse_home(self, rows):
        items = []
        for row in rows:
            contents = []
            if CAROUSEL[0] in row:
                results = nav(row, CAROUSEL)
            elif 'musicImmersiveCarouselShelfRenderer' in row:
                results = row['musicImmersiveCarouselShelfRenderer']
            else:
                continue
            for result in results['contents']:
                data = nav(result, [MTRIR], True)
                content = None
                if data:
                    page_type = nav(data, TITLE + NAVIGATION_BROWSE + PAGE_TYPE, True)
                    if page_type is None:  # song
                        content = parse_song(data)
                    elif page_type == "MUSIC_PAGE_TYPE_ALBUM":
                        content = parse_album(data)
                    elif page_type == "MUSIC_PAGE_TYPE_ARTIST":
                        content = parse_related_artist(data)
                    elif page_type == "MUSIC_PAGE_TYPE_PLAYLIST":
                        content = parse_playlist(data)
                else:
                    data = nav(result, [MRLIR])
                    columns = [
                        get_flex_column_item(data, i) for i in range(0, len(data['flexColumns']))
                    ]
                    content = {
                        'title': nav(columns[0], TEXT_RUN_TEXT),
                        'videoId': nav(columns[0], TEXT_RUN + NAVIGATION_VIDEO_ID),
                        'thumbnails': nav(data, THUMBNAILS)
                    }
                    content.update(parse_song_runs(nav(columns[1], TEXT_RUNS)))
                    if len(columns) > 2 and columns[2] is not None:
                        content['album'] = {
                            'title': nav(columns[2], TEXT_RUN_TEXT),
                            'browseId': nav(columns[2], TEXT_RUN + NAVIGATION_BROWSE_ID)
                        }

                contents.append(content)

            items.append({'title': nav(results, CAROUSEL_TITLE + ['text']), 'contents': contents})
        return items

    @i18n
    def parse_search_results(self, results, resultType=None, category=None):
        search_results = []
        default_offset = (not resultType) * 2
        for result in results:
            data = result[MRLIR]
            search_result = {'category': category}
            if not resultType:
                resultType = get_item_text(data, 1).lower()
                result_types = ['artist', 'playlist', 'song', 'video', 'station']
                result_types_local = [
                    _('artist'), _('playlist'),
                    _('song'), _('video'),
                    _('station')
                ]
                # default to album since it's labeled with multiple values ('Single', 'EP', etc.)
                if resultType not in result_types_local:
                    resultType = 'album'
                else:
                    resultType = result_types[result_types_local.index(resultType)]

            search_result['resultType'] = resultType

            if resultType != 'artist':
                search_result['title'] = get_item_text(data, 0)

            if resultType == 'artist':
                search_result['artist'] = get_item_text(data, 0)
                parse_menu_playlists(data, search_result)

            elif resultType == 'album':
                search_result['type'] = get_item_text(data, 1)

            elif resultType == 'playlist':
                flex_item = get_flex_column_item(data, 1)['text']['runs']
                has_author = len(flex_item) == default_offset + 3
                search_result['itemCount'] = nav(
                    flex_item, [default_offset + has_author * 2, 'text']).split(' ')[0]
                search_result['author'] = None if not has_author else nav(
                    flex_item, [default_offset, 'text'])

            elif resultType == 'station':
                search_result['videoId'] = nav(data, NAVIGATION_VIDEO_ID)
                search_result['playlistId'] = nav(data, NAVIGATION_PLAYLIST_ID)

            elif resultType == 'song':
                search_result['album'] = None
                if 'menu' in data:
                    toggle_menu = find_object_by_key(nav(data, MENU_ITEMS), TOGGLE_MENU)
                    if toggle_menu:
                        search_result['feedbackTokens'] = parse_song_menu_tokens(toggle_menu)

            elif resultType == 'video':
                search_result['views'] = None

            elif resultType == 'upload':
                browse_id = nav(data, NAVIGATION_BROWSE_ID, True)
                if not browse_id:  # song result
                    flex_items = [
                        nav(get_flex_column_item(data, i), ['text', 'runs'], True)
                        for i in range(2)
                    ]
                    if flex_items[0]:
                        search_result['videoId'] = nav(flex_items[0][0], NAVIGATION_VIDEO_ID, True)
                        search_result['playlistId'] = nav(flex_items[0][0], NAVIGATION_PLAYLIST_ID,
                                                          True)
                    if flex_items[1]:
                        search_result.update(parse_song_runs(flex_items[1]))
                    search_result['resultType'] = 'song'

                else:  # artist or album result
                    search_result['browseId'] = browse_id
                    if 'artist' in search_result['browseId']:
                        search_result['resultType'] = 'artist'
                    else:
                        flex_item2 = get_flex_column_item(data, 1)
                        runs = [
                            run['text'] for i, run in enumerate(flex_item2['text']['runs'])
                            if i % 2 == 0
                        ]
                        if len(runs) > 1:
                            search_result['artist'] = runs[1]
                        if len(runs) > 2:  # date may be missing
                            search_result['releaseDate'] = runs[2]
                        search_result['resultType'] = 'album'

            if resultType in ['song', 'video']:
                search_result['videoId'] = nav(
                    data, PLAY_BUTTON + ['playNavigationEndpoint', 'watchEndpoint', 'videoId'],
                    True)

            if resultType in ['song', 'video', 'album']:
                search_result['duration'] = None
                search_result['year'] = None
                has_offset = resultType == 'album' or (default_offset
                                                       and bool(search_result['videoId']))
                flex_item = get_flex_column_item(data, 1)
                runs = flex_item['text']['runs'][2 * has_offset:]
                song_info = parse_song_runs(runs)
                search_result.update(song_info)

            if resultType in ['artist', 'album', 'playlist']:
                search_result['browseId'] = nav(data, NAVIGATION_BROWSE_ID, True)
                if not search_result['browseId']:
                    continue

            if resultType in ['song', 'album']:
                search_result['isExplicit'] = nav(data, BADGE_LABEL, True) is not None

            search_result['thumbnails'] = nav(data, THUMBNAILS, True)
            search_results.append(search_result)

        return search_results

    @i18n
    def parse_artist_contents(self, results: List) -> Dict:
        categories = ['albums', 'singles', 'videos', 'playlists', 'related']
        categories_local = [_('albums'), _('singles'), _('videos'), _('playlists'), _('related')]
        categories_parser = [
            parse_album, parse_single, parse_video, parse_playlist, parse_related_artist
        ]
        artist = {}
        for i, category in enumerate(categories):
            data = [
                r['musicCarouselShelfRenderer'] for r in results
                if 'musicCarouselShelfRenderer' in r
                and nav(r, CAROUSEL + CAROUSEL_TITLE)['text'].lower() == categories_local[i]
            ]
            if len(data) > 0:
                artist[category] = {'browseId': None, 'results': []}
                if 'navigationEndpoint' in nav(data[0], CAROUSEL_TITLE):
                    artist[category]['browseId'] = nav(data[0],
                                                       CAROUSEL_TITLE + NAVIGATION_BROWSE_ID)
                    if category in ['albums', 'singles', 'playlists']:
                        artist[category]['params'] = nav(
                            data[0],
                            CAROUSEL_TITLE)['navigationEndpoint']['browseEndpoint']['params']

                artist[category]['results'] = parse_content_list(data[0]['contents'],
                                                                 categories_parser[i])

        return artist


def parse_content_list(results, parse_func, key=MTRIR):
    contents = []
    for result in results:
        contents.append(parse_func(result[key]))

    return contents


def parse_album(result):
    return {
        'title': nav(result, TITLE_TEXT),
        'year': nav(result, SUBTITLE2, True),
        'browseId': nav(result, TITLE + NAVIGATION_BROWSE_ID),
        'thumbnails': nav(result, THUMBNAIL_RENDERER)
    }


def parse_single(result):
    return {
        'title': nav(result, TITLE_TEXT),
        'year': nav(result, SUBTITLE, True),
        'browseId': nav(result, TITLE + NAVIGATION_BROWSE_ID),
        'thumbnails': nav(result, THUMBNAIL_RENDERER)
    }


def parse_song(result):
    song = {
        'title': nav(result, TITLE_TEXT),
        'videoId': nav(result, NAVIGATION_VIDEO_ID),
        'playlistId': nav(result, NAVIGATION_PLAYLIST_ID, True),
        'thumbnails': nav(result, THUMBNAIL_RENDERER)
    }
    song.update(parse_song_runs(result['subtitle']['runs']))
    return song


def parse_video(result):
    runs = result['subtitle']['runs']
    artists_len = get_dot_separator_index(runs)
    video = {
        'title': nav(result, TITLE_TEXT),
        'videoId': nav(result, NAVIGATION_VIDEO_ID),
        'artists': parse_song_artists_runs(runs[:artists_len]),
        'playlistId': nav(result, NAVIGATION_PLAYLIST_ID, True),
        'thumbnails': nav(result, THUMBNAIL_RENDERER, True)
    }
    video['views'] = runs[-1]['text'].split(' ')[0]
    return video


def parse_playlist(data):
    playlist = {
        'title': nav(data, TITLE_TEXT),
        'playlistId': nav(data, TITLE + NAVIGATION_BROWSE_ID)[2:],
        'thumbnails': nav(data, THUMBNAIL_RENDERER)
    }
    subtitle = data['subtitle']
    if 'runs' in subtitle:
        playlist['description'] = "".join([run['text'] for run in subtitle['runs']])
        if len(subtitle['runs']) == 3 and re.search(r'\d+ ', nav(data, SUBTITLE2)):
            playlist['count'] = nav(data, SUBTITLE2).split(' ')[0]
            playlist['author'] = parse_song_artists_runs(subtitle['runs'][:1])

    return playlist


def parse_related_artist(data):
    subscribers = nav(data, SUBTITLE, True)
    if subscribers:
        subscribers = subscribers.split(' ')[0]
    return {
        'title': nav(data, TITLE_TEXT),
        'browseId': nav(data, TITLE + NAVIGATION_BROWSE_ID),
        'subscribers': subscribers,
        'thumbnails': nav(data, THUMBNAIL_RENDERER),
    }
