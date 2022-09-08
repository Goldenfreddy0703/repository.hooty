import sys
import xbmc
try:
    from urllib.parse import urlencode  # Py3
except ImportError:
    from urllib import urlencode
_addonlogname = '[plugin.video.themoviedb.helper]\n'

PLUGINPATH = u'plugin://plugin.video.themoviedb.helper/'


def kodi_log(value, level=0):
    try:
        if isinstance(value, list):
            v = ''
            for i in value:
                v = u'{} {}'.format(v, i) if v else u'{}'.format(i)
            value = v
        if isinstance(value, bytes):
            value = value.decode('utf-8')
        logvalue = u'{0}{1}'.format(_addonlogname, value)
        if sys.version_info < (3, 0):
            logvalue = logvalue.encode('utf-8', 'ignore')
        if level == 1:
            xbmc.log(logvalue, level=xbmc.LOGINFO)
        else:
            xbmc.log(logvalue, level=xbmc.LOGDEBUG)
    except Exception as exc:
        xbmc.log(u'Logging Error: {}'.format(exc), level=xbmc.LOGINFO)


def viewitems(obj, **kwargs):
    """  from future
    Function for iterating over dictionary items with the same set-like
    behaviour on Py2.7 as on Py3.

    Passes kwargs to method."""
    func = getattr(obj, "viewitems", None)
    if not func:
        func = obj.items
    return func(**kwargs)


def try_encode(string, encoding='utf-8'):
    """helper to encode strings for PY 2 """
    if sys.version_info.major == 3:
        return string
    try:
        return string.encode(encoding)
    except Exception:
        return string


def try_decode(string, encoding='utf-8', errors=None):
    """helper to decode strings for PY 2 """
    if sys.version_info.major == 3:
        return string
    try:
        return string.decode(encoding, errors) if errors else string.decode(encoding)
    except Exception:
        return string


def urlencode_params(*args, **kwargs):
    """ helper to assist with difference in urllib modules in PY2/3 """
    params = dict()
    for k, v in viewitems(kwargs):
        params[try_encode(k)] = try_encode(v)
    return urlencode(params)


def encode_url(path=None, **kwargs):
    path = path or PLUGINPATH
    paramstring = '?{}'.format(urlencode_params(**kwargs)) if kwargs else ''
    return '{}{}'.format(path, paramstring)
