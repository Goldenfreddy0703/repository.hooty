import sys
import xbmc
from lib.plugin import viewitems, try_encode, try_decode


BASIC_MOVIE = {
    'tmdb_type': 'movie',
    'tmdb_id': lambda: sys.listitem.getUniqueID('tmdb'),
    'imdb_id': lambda: sys.listitem.getUniqueID('imdb'),
    'query': lambda: sys.listitem.getVideoInfoTag().getTitle() or sys.listitem.getLabel(),
    'year': lambda: sys.listitem.getVideoInfoTag().getYear()
}


BASIC_TVSHOW = {
    'tmdb_type': 'tv',
    'tmdb_id': lambda: sys.listitem.getUniqueID('tmdb'),
    'imdb_id': lambda: sys.listitem.getUniqueID('imdb'),
    'query': lambda: sys.listitem.getVideoInfoTag().getTitle() or sys.listitem.getLabel(),
    'year': lambda: sys.listitem.getVideoInfoTag().getYear()
}


BASIC_EPISODE = {
    'tmdb_type': 'tv',
    'query': lambda: sys.listitem.getVideoInfoTag().getTVShowTitle(),
    'season': lambda: sys.listitem.getVideoInfoTag().getSeason(),
    'episode': lambda: sys.listitem.getVideoInfoTag().getEpisode(),
    'episode_year': lambda: sys.listitem.getVideoInfoTag().getYear()
}


ROUTE = {
    'play_using': {
        'movie': {
            'play': 'movie',
            'tmdb_id': lambda: sys.listitem.getUniqueID('tmdb'),
            'imdb_id': lambda: sys.listitem.getUniqueID('imdb'),
            'query': lambda: sys.listitem.getVideoInfoTag().getTitle() or sys.listitem.getLabel(),
            'year': lambda: sys.listitem.getVideoInfoTag().getYear(),
            'ignore_default': 'true'
        },
        'episode': {
            'play': 'tv',
            'query': lambda: sys.listitem.getVideoInfoTag().getTVShowTitle(),
            'season': lambda: sys.listitem.getVideoInfoTag().getSeason(),
            'episode': lambda: sys.listitem.getVideoInfoTag().getEpisode(),
            'episode_year': lambda: sys.listitem.getVideoInfoTag().getYear(),
            'ignore_default': 'true'
        }
    },
    'sync_trakt': {
        'movie': BASIC_MOVIE,
        'tvshow': BASIC_TVSHOW,
        'episode': BASIC_EPISODE
    },
    'related_lists': {
        'movie': BASIC_MOVIE,
        'tvshow': BASIC_TVSHOW,
        'episode': BASIC_EPISODE
    },
    'refresh_details': {
        'movie': BASIC_MOVIE,
        'tvshow': BASIC_TVSHOW,
        'episode': BASIC_EPISODE
    },
    'manage_artwork': {
        'movie': BASIC_MOVIE,
        'tvshow': BASIC_TVSHOW,
        'episode': BASIC_EPISODE
    },
    'add_to_library': {
        'movie': BASIC_MOVIE,
        'tvshow': BASIC_TVSHOW,
        'episode': BASIC_EPISODE
    }
}


def run_script(*args, **kwargs):
    path = 'plugin.video.themoviedb.helper'
    for i in args:
        if not i:
            continue
        path = u'{},{}'.format(path, i)
    for k, v in viewitems(kwargs):
        if not v:
            continue
        path = u'{},{}={}'.format(path, k, try_decode(v))
    path = u'RunScript({})'.format(path)
    xbmc.executebuiltin(try_encode(try_decode(path)))


def run_context(info):
    dbtype = sys.listitem.getVideoInfoTag().getMediaType()
    params = {k: v() if callable(v) else v for k, v in viewitems(ROUTE.get(info, {}).get(dbtype, {}))}
    if not params:
        return
    run_script(info, **params)
