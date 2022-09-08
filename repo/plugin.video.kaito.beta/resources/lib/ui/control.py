# -*- coding: utf-8 -*-
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
import re
import os
import hashlib
import collections
import threading
import sys
import json
import datetime
import time
import xbmc
import xbmcvfs
import xbmcaddon
import xbmcplugin
import xbmcgui
from . import http
import urllib.parse
from urllib.parse import quote

from resources.lib.third_party import pytz, tzlocal

try:
    import StorageServer
except:
    import storageserverdummy as StorageServer

try:
    HANDLE=int(sys.argv[1])
except:
    HANDLE = '1'

PYTHON3 = True if sys.version_info.major == 3 else False

addonInfo = xbmcaddon.Addon().getAddonInfo
ADDON_NAME = addonInfo('id')
__settings__ = xbmcaddon.Addon(ADDON_NAME)
__language__ = __settings__.getLocalizedString
CACHE = StorageServer.StorageServer("%s.animeinfo" % ADDON_NAME, 24)
addonInfo = __settings__.getAddonInfo


kodiGui = xbmcgui
showDialog = xbmcgui.Dialog()
dialogWindow = kodiGui.WindowDialog
xmlWindow = kodiGui.WindowXMLDialog
condVisibility = xbmc.getCondVisibility
menuItem = xbmcgui.ListItem
execute = xbmc.executebuiltin

progressDialog = xbmcgui.DialogProgress()
kodi = xbmc

playList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
player = xbmc.Player

try:
    # Try to get Python 3 versions
    from urllib.parse import (
        parse_qsl,
        urlencode,
        quote_plus,
        parse_qs,
        quote,
        unquote,
        urlparse,
        urljoin,
    )
except ImportError:
    # Fall back on future.backports to ensure we get unicode compatible PY3 versions in PY2
    from future.backports.urllib.parse import (
        parse_qsl,
        urlencode,
        quote_plus,
        parse_qs,
        quote,
        unquote,
        urlparse,
        urljoin,
    )

try:
    basestring = basestring  # noqa # pylint: disable=undefined-variable
    unicode = unicode  # noqa # pylint: disable=undefined-variable
    xrange = xrange  # noqa # pylint: disable=undefined-variable
except NameError:
    basestring = str
    unicode = str
    xrange = range

SORT_TOKENS = [
    "a ",
    "das ",
    "de ",
    "der ",
    "die ",
    "een ",
    "el ",
    "het ",
    "i ",
    "il ",
    "l'",
    "la ",
    "le ",
    "les ",
    "o ",
    "the ",
]
SORT_TOKEN_REGEX = re.compile(r"|".join(r"^{}".format(i) for i in SORT_TOKENS), re.IGNORECASE)

youtube_url = "plugin://plugin.video.youtube/play/?video_id={}"

def decode_py2(value):
    if not PYTHON3 and isinstance(value, basestring):
        return encode_py2(value).decode("utf-8")
    return value

def encode_py2(value):
    if not value:
        return value
    if not PYTHON3 and isinstance(value, unicode):
        return value.encode("utf-8")
    return value

def closeBusyDialog():
    if condVisibility('Window.IsActive(busydialog)'):
        execute('Dialog.Close(busydialog)')
    if condVisibility('Window.IsActive(busydialognocancel)'):
        execute('Dialog.Close(busydialognocancel)')

def try_release_lock(lock):
    if lock.locked():
        lock.release()

def real_debrid_enabled():
    if getSetting('rd.auth') != '' and getSetting('realdebrid.enabled') == 'true':
        return True
    else:
        return False

def all_debrid_enabled():
    if getSetting('alldebrid.apikey') != '' and getSetting('alldebrid.enabled') == 'true':
        return True
    else:
        return False

def premiumize_enabled():
    if getSetting('premiumize.token') != '' and getSetting('premiumize.enabled') == 'true':
        return True
    else:
        return False

def copy2clip(txt):
    """
    Takes a text string and attempts to copy it to the clipboard of the device
    :param txt: Text to send to clipboard
    :type txt: str
    :return: None
    :rtype: None
    """
    import subprocess

    platform = sys.platform
    if platform == "win32":
        try:
            cmd = "echo " + txt.strip() + "|clip"
            return subprocess.check_call(cmd, shell=True)
        except:
            pass
    elif platform == "linux2":
        try:
            from subprocess import Popen, PIPE

            p = Popen(["xsel", "-pi"], stdin=PIPE)
            p.communicate(input=txt)
        except:
            pass

def get_item_information(action_args):
    """
    Ease of use tool to retrieve items meta from TraktSyncDatabase based on action arguments
    :param action_args: action arguments received in call to Seren
    :type action_args: dict
    :return: Metadata for item
    :rtype: dict
    """
    if action_args is None:
        return None
    from resources.lib.database.anilist_sync import shows

    return shows.AnilistSyncDatabase().get_show(action_args)
    # item_information = {"action_args": action_args}
    # if action_args["mediatype"] == "tvshow":
    #     from resources.lib.database.trakt_sync import shows

    #     item_information.update(
    #         shows.TraktSyncDatabase().get_show(action_args["trakt_id"])
    #     )
    #     return item_information
    # elif action_args["mediatype"] == "season":
    #     from resources.lib.database.trakt_sync import shows

    #     item_information.update(
    #         shows.TraktSyncDatabase().get_season(
    #             action_args["trakt_id"], action_args["trakt_show_id"]
    #         )
    #     )
    #     return item_information
    # elif action_args["mediatype"] == "episode":
    #     from resources.lib.database.trakt_sync import shows

    #     item_information.update(
    #         shows.TraktSyncDatabase().get_episode(
    #             action_args["trakt_id"], action_args["trakt_show_id"]
    #         )
    #     )
    #     return item_information
    # elif action_args["mediatype"] == "movie":
    #     from resources.lib.database.trakt_sync import movies

    #     item_information.update(
    #         movies.TraktSyncDatabase().get_movie(action_args["trakt_id"])
    #     )
    #     return item_information

def get_item_information_mal(action_args):
    """
    Ease of use tool to retrieve items meta from TraktSyncDatabase based on action arguments
    :param action_args: action arguments received in call to Seren
    :type action_args: dict
    :return: Metadata for item
    :rtype: dict
    """
    if action_args is None:
        return None
    from resources.lib.database.anilist_sync import shows

    return shows.AnilistSyncDatabase().get_show_mal(action_args)

def deconstruct_action_args(action_args):
    """
    Attempts to create a dictionary from the calls action args
    :param action_args: potential url quoted, stringed dict
    :type action_args:  str
    :return: unquoted and loaded dictionary or str if not json
    :rtype: dict, str
    """
    action_args = unquote(action_args)
    try:
        return json.loads(action_args)
    except ValueError:
        return action_args

def construct_action_args(action_args):
    """
    Takes a json capable response, dumps and urlquotes it ready for URL appending
    :param action_args: Valid JSON
    :type action_args: list, dict
    :return: Url quoted response
    :rtype: str
    """
    return quote(json.dumps(action_args, sort_keys=True))

def extend_array(array1, array2):
    """
    Safe combining of two lists
    :param array1: List to combine
    :type array1: list
    :param array2: List to combine
    :type array2: list
    :return: Combined lists
    :rtype: list
    """
    result = []
    if array1 and isinstance(array1, list):
        result.extend(array1)
    if array2 and isinstance(array2, list):
        result.extend(array2)
    return result

def smart_merge_dictionary(dictionary, merge_dict, keep_original=False, extend_array=True):
    """Method for merging large multi typed dictionaries, it has support for handling arrays.
    :param dictionary:Original dictionary to merge the second on into.
    :type dictionary:dict
    :param merge_dict:Dictionary that is used to merge into the original one.
    :type merge_dict:dict
    :param keep_original:Boolean that indicates if there are duplicated values to keep the original one.
    :type keep_original:bool
    :param extend_array:Boolean that indicates if we need to extend existing arrays with the enw values..
    :type extend_array:bool
    :return:Merged dictionary
    :rtype:dict
    """
    if not isinstance(dictionary, dict) or not isinstance(merge_dict, dict):
        return dictionary
    for new_key, new_value in merge_dict.items():
        original_value = dictionary.get(new_key, {})
        if isinstance(new_value, (dict, collections.Mapping)):
            if original_value is None:
                original_value = {}
            new_value = smart_merge_dictionary(original_value, new_value, keep_original)
        else:
            if original_value and keep_original:
                continue
            if extend_array and isinstance(original_value, (list, set)) and isinstance(
                    new_value, (list, set)
            ):
                original_value.extend(x for x in new_value if x not in original_value)
                try:
                    new_value = sorted(original_value)
                except TypeError:  # Sorting of complex array doesn't work.
                    new_value = original_value
                    pass
        if new_value:
            dictionary[new_key] = new_value
    return dictionary

def freeze_object(o):
    """
    Takes in a iterable object, freezes all dicts, tuples lists/sets
    :param o: Object to free
    :type o: dict/set/list/tuple
    :return: Hashable object
    :rtype: tuple, frozenset
    """
    if isinstance(o, dict):
        return frozenset({k: freeze_object(v) for k, v in o.items()}.items())

    if isinstance(o, (set, tuple, list)):
        return tuple([freeze_object(v) for v in o])

    return o

def md5_hash(value):
    """
    Returns MD5 hash of given value
    :param value: object to hash
    :type value: object
    :return: Hexdigest of hash
    :rtype: str
    """
    return hashlib.md5(unicode(value).encode("utf-8")).hexdigest()

def run_threaded(target_func, *args, **kwargs):
    """
    Ease of use method to spawn a new thread and run without joining
    :param target_func: function to run
    :type target_func: Any
    :param args: tuple of arguments to pass through to function
    :type args: (int) - > None
    :param kwargs: dictionary of kwargs to pass to function
    :type kwargs: (int) - > None
    :return: None
    :rtype: None
    """
    from threading import Thread

    thread = Thread(target=target_func, args=args, kwargs=kwargs)
    thread.start()

def get_clean_number(value):
    """
    De-strings stringed int/float and returns respective type
    :param value: Stringed value of an integer or float
    :type value: str
    :return: Converted int or float or None if value error
    :rtype: int, float, None
    """
    if isinstance(value, (int, float)):
        return value
    try:
        if "." in value:
            return float(value)
        else:
            return int(value.replace(",", ""))
    except ValueError:
        return None


def safe_round(x, y=0):
    """PY2 and PY3 equal rounding, its up to 15 digits behind the comma.
    :param x: value to round
    :type x: float
    :param y: decimals behind the comma
    :type y: int
    :return: rounded value
    :rtype: float
    """
    place = 10 ** y
    rounded = (int(x * place + 0.5 if x >= 0 else -0.5)) / place
    if rounded == int(rounded):
        rounded = int(rounded)
    return rounded

def validate_path(path):
    """Returns the translated path.
    :param path:Path to format
    :type path:str
    :return:Translated path
    :rtype:str
    """
    if hasattr(xbmcvfs, "validatePath"):
        path = xbmcvfs.validatePath(path)  # pylint: disable=no-member
    else:
        path = xbmc.validatePath(path)  # pylint: disable=no-member
    return path

def translate_path(path):
    """Validates the path against the running platform and ouputs the clean path.
    :param path:Path to be verified
    :type path:str
    :return:Verified and cleaned path
    :rtype:str
    """
    if hasattr(xbmcvfs, "translatePath"):
        path = xbmcvfs.translatePath(path)  # pylint: disable=no-member
    else:
        path = xbmc.translatePath(path)  # pylint: disable=no-member
    return path

def create_multiline_message(line1=None, line2=None, line3=None, *lines):
    """Creates a message from the supplied lines
    :param line1:Line 1
    :type line1:str
    :param line2:Line 2
    :type line2:str
    :param line3: Line3
    :type line3:str
    :param lines:List of additional lines
    :type lines:list[str]
    :return:New message wit the combined lines
    :rtype:str
    """
    result = []
    if line1:
        result.append(line1)
    if line2:
        result.append(line2)
    if line3:
        result.append(line3)
    if lines:
        result.extend(l for l in lines if l)
    return "\n".join(result)

def parse_datetime(string_date, format_string="%Y-%m-%d", date_only=True):
    """
    Attempts to pass over provided string and return a date or datetime object
    :param string_date: String to parse
    :type string_date: str
    :param format_string: Format of str
    :type format_string: str
    :param date_only: Whether to return a date only object or not
    :type date_only: bool
    :return: datetime.datetime or datetime.date object
    :rtype: object
    """
    if not string_date:
        return None

    # Don't use datetime.datetime.strptime()
    # Workaround for python bug caching of strptime in datetime module.
    # Don't just try to detect TypeError because it breaks meta handler lambda calls occasionally, particularly
    # with unix style threading.
    if date_only:
        res = datetime.datetime(*(time.strptime(string_date, format_string)[0:6])).date()
    else:
        res = datetime.datetime(*(time.strptime(string_date, format_string)[0:6]))

    return res

def ignore_ascii(text):
    text = text.encode('ascii','ignore').decode("utf-8")
    return text

def italic_string(text):
    """
    Ease of use method to return a italic like ready string for display in Kodi
    :param text: Text to display in italics
    :type text: str
    :return: Formatted string
    :rtype: str
    """

    return "[I]{}[/I]".format(text)

def validate_date(date_string):
    """Validates the path and returns only the date portion, if it invalidates it just returns none.
    :param date_string:string value with a supposed date.
    :type date_string:str
    :return:formatted datetime or none
    :rtype:str
    """
    from resources.lib.ui.globals import g

    result = None
    if not date_string:
        return date_string

    try:
        result = parse_datetime(date_string, g.DATE_FORMAT, False)
    except ValueError:
        pass

    if not result:
        try:
            result = parse_datetime(date_string, g.DATE_TIME_FORMAT_ZULU, False)
        except ValueError:
            pass

    if not result:
        try:
            result = parse_datetime(date_string, g.DATE_TIME_FORMAT, False)
        except ValueError:
            pass

    if not result:
        try:
            result = parse_datetime(date_string, "%d %b %Y", False)
        except ValueError:
            pass

    if result and result.year > 1900:
        return g.UNICODE(result.strftime(g.DATE_TIME_FORMAT))
    return None

def utc_to_local(utc_string):
    """
    Converts a UTC style datetime string to the localtimezone
    :param utc_string: UTC datetime string
    :return: localized datetime string
    """
    from resources.lib.ui.globals import g

    if utc_string is None:
        return None

    utc_string = validate_date(utc_string)

    if not utc_string:
        return None

    utc_timezone = pytz.timezone('UTC')
    local_tz = tzlocal.get_localzone()  # If this fails we should get UTC back

    utc = parse_datetime(utc_string, g.DATE_TIME_FORMAT, False)
    utc = utc_timezone.localize(utc)
    local_time = utc.astimezone(local_tz)
    g.log("Original utc_string: {}  local_time: {}".format(utc_string, local_time.strftime(g.DATE_TIME_FORMAT)), "debug")
    return local_time.strftime(g.DATE_TIME_FORMAT)

def filter_dictionary(dictionary, *keys):
    """Filters the dictionary with the supplied args
    :param dictionary:Dictionary to filter
    :type dictionary:dict
    :param keys:Keys to filter on
    :type keys:any
    :return:Filtered dictionary
    :rtype:dict
    """
    if not dictionary:
        return None

    return {k: v for k, v in dictionary.items() if any(k.startswith(x) for x in keys)}

def safe_dict_get(dictionary, *path):
    """Safely get the value from a given path taken into account taht the path can be none.
    :param dictionary:Dictionary to take the path from
    :type dictionary:dict
    :param path:Collection of items we try to get form the dict.
    :type path:str
    :return:The value for that given path
    :rtype:any
    """
    if len(path) == 0:
        return dictionary
    current_path = path[0]
    if dictionary is None or not isinstance(dictionary, dict):
        return None

    result = dictionary.get(current_path)
    if isinstance(result, dict):
        return safe_dict_get(result, *path[1:])
    else:
        return dictionary.get(current_path)

def refresh():
    return xbmc.executebuiltin('Container.Refresh')

def settingsMenu():
    return xbmcaddon.Addon().openSettings()

def getSetting(key):
    return __settings__.getSetting(key)

def setSetting(id, value):
    return __settings__.setSetting(id=id, value=value)

def cache(funct, *args):
    return CACHE.cacheFunction(funct, *args)

def clear_cache():
    return CACHE.delete("%")

def lang(x):
    text = __language__(x)
    return decode_py2(text)

def addon_url(url=''):
    return "plugin://%s/%s" % (ADDON_NAME, url)

def get_plugin_url():
    addon_base = addon_url()
    assert sys.argv[0].startswith(addon_base), "something bad happened in here"
    return sys.argv[0][len(addon_base):]

def get_plugin_params():
    return dict(urllib.parse.parse_qsl(sys.argv[2].replace('?', '')))

def keyboard(text):
    keyboard = xbmc.Keyboard("", text, False)
    keyboard.doModal()
    if keyboard.isConfirmed():
        return keyboard.getText()
    return None

def closeAllDialogs():
    execute('Dialog.Close(all,true)')

def ok_dialog(title, text):
    return xbmcgui.Dialog().ok(title, text)

def yesno_dialog(title, text, nolabel=None, yeslabel=None):
    return xbmcgui.Dialog().yesno(title, text, nolabel=nolabel, yeslabel=yeslabel)

def multiselect_dialog(title, _list):
    if isinstance(_list, list):
        return xbmcgui.Dialog().multiselect(title, _list)
    return None