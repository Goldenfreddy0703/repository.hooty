################################################################################
#      Copyright (C) 2019 drinfernoo                                           #
#                                                                              #
#  This Program is free software; you can redistribute it and/or modify        #
#  it under the terms of the GNU General Public License as published by        #
#  the Free Software Foundation; either version 2, or (at your option)         #
#  any later version.                                                          #
#                                                                              #
#  This Program is distributed in the hope that it will be useful,             #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of              #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the                #
#  GNU General Public License for more details.                                #
#                                                                              #
#  You should have received a copy of the GNU General Public License           #
#  along with XBMC; see the file COPYING.  If not, write to                    #
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.       #
#  http://www.gnu.org/copyleft/gpl.html                                        #
################################################################################

import xbmc
import xbmcgui

import glob
import os
import shutil
import time

from datetime import datetime
from datetime import timedelta

import sqlite3 as database

from resources.libs.common.config import CONFIG
from resources.libs.common import logging
from resources.libs.common import tools
from resources.libs import cache_registry
from resources.libs import dbwipe


def _include_flag(setting_id):
    return CONFIG.get_setting(setting_id) == 'true'


def _db_log(level, message):
    levels = {'failed': xbmc.LOGINFO, 'warning': xbmc.LOGWARNING}
    logging.log('[{0}] {1}'.format(level.capitalize(), message), level=levels.get(level, xbmc.LOGINFO))


# Folder caches, one list for both the size calculation and the wipe (Tier 2 Phase C).
# Sub-paths under addon_data, relative; SHARED ones exist in the profile's addon_data too.
_SHARED_SUBPATHS = (
    ('script.module.simple.downloader',),
    ('plugin.video.itv', 'Images'))
_ADDON_DATA_SUBPATHS = (
    ('script.extendedinfo', 'images'),
    ('script.extendedinfo', 'TheMovieDB'),
    ('script.extendedinfo', 'YouTube'),
    ('script.diamondinfo', 'images'),
    ('script.diamondinfo', 'TheMovieDB'),
    ('plugin.program.autocompletion', 'Google'),
    ('plugin.program.autocompletion', 'Bing'),
    ('plugin.video.openmeta', '.storage'))


def _folder_cache_paths(for_clear):
    """Return (profile addon_data, ordered folder-cache paths). for_clear=True is the wipe list, False the size list."""
    profile = os.path.join(CONFIG.PROFILE, 'addon_data')
    system = [
        os.path.join(CONFIG.HOME, 'cache'),
        os.path.join(CONFIG.HOME, 'temp'),
        os.path.join('/private/var/mobile/Library/Caches/AppleTV/Video/', 'Other'),
        os.path.join('/private/var/mobile/Library/Caches/AppleTV/Video/', 'LocalAndRental')]
    addon_shared = [os.path.join(CONFIG.ADDON_DATA, *p) for p in _SHARED_SUBPATHS]
    profile_shared = [os.path.join(profile, *p) for p in _SHARED_SUBPATHS]
    addon_rest = [os.path.join(CONFIG.ADDON_DATA, *p) for p in _ADDON_DATA_SUBPATHS]
    if for_clear:
        return profile, [profile, CONFIG.ADDON_DATA] + system + addon_shared + profile_shared + addon_rest
    paths = [CONFIG.ADDON_DATA] + system + addon_shared + addon_rest
    if profile != CONFIG.ADDON_DATA:
        paths += profile_shared + [profile]
    return profile, paths


# Kodi parks the add-on versions it is installing or replacing in addons/temp (uuid folders) and does not always
# tidy them up. Only entries untouched for a day are treated as leftovers, so a running install is never hit.
_INSTALL_TEMP_MAX_AGE = 24 * 60 * 60


def _stale_install_temp():
    """Immediate children of addons/temp that are older than a day (never the temp folder itself)."""
    root = os.path.join(CONFIG.ADDONS, 'temp')
    try:
        names = os.listdir(root)
    except OSError:
        return []
    cutoff = time.time() - _INSTALL_TEMP_MAX_AGE
    stale = []
    for name in names:
        path = os.path.join(root, name)
        try:
            if os.path.getmtime(path) < cutoff:
                stale.append(path)
        except OSError:
            pass
    return stale


def get_cache_size():
    from resources.libs.common import tools

    PROFILEADDONDATA, cachelist = _folder_cache_paths(for_clear=False)

    totalsize = 0

    for item in cachelist:
        if not os.path.exists(item):
            continue
        if item not in [CONFIG.ADDON_DATA, PROFILEADDONDATA]:
            totalsize = tools.get_size(item, totalsize)
        else:
            for root, dirs, files in os.walk(item):
                for d in dirs:
                    if 'cache' in d.lower() and d.lower() not in ['meta_cache']:
                        totalsize = tools.get_size(os.path.join(root, d), totalsize)

    for item in _stale_install_temp():
        try:
            totalsize += tools.get_size(item) if os.path.isdir(item) else os.path.getsize(item)
        except OSError:
            pass

    if CONFIG.get_setting('includevideo') == 'true':
        files = cache_registry.db_paths(CONFIG.ADDON_DATA, CONFIG.get_setting('includeall') == 'true', _include_flag)
        if len(files) > 0:
            for item in files:
                if not os.path.exists(item):
                    continue
                totalsize += os.path.getsize(item)
        else:
            logging.log("Clear Cache: Clear Video Cache Not Enabled")

    return totalsize


def clear_packages(over=None):
    from resources.libs.common import tools

    if os.path.exists(CONFIG.PACKAGES):
        try:
            for root, dirs, files in os.walk(CONFIG.PACKAGES):
                file_count = 0
                file_count += len(files)
                if file_count > 0:
                    size = tools.convert_size(tools.get_size(CONFIG.PACKAGES))
                    if over:
                        yes = 1
                    else:
                        dialog = xbmcgui.Dialog()
                    
                        yes = dialog.yesno("[COLOR {0}]Delete Package Files[/COLOR]".format(CONFIG.COLOR2), "[COLOR {0}]{1}[/COLOR] files found / [COLOR {2}]{3}[/COLOR] in size.".format(CONFIG.COLOR1, str(file_count),CONFIG.COLOR1, size) + '\n' + "Do you want to delete them?", nolabel='[B][COLOR red]Don\'t Clear[/COLOR][/B]', yeslabel='[B][COLOR springgreen]Clear Packages[/COLOR][/B]')
                    if yes:
                        for f in files:
                            os.unlink(os.path.join(root, f))
                        for d in dirs:
                            shutil.rmtree(os.path.join(root, d))
                        logging.log_notify(CONFIG.ADDONTITLE,
                                  '[COLOR {0}]Clear Packages: Success![/COLOR]'.format(CONFIG.COLOR2))
                else:
                    logging.log_notify(CONFIG.ADDONTITLE,
                              '[COLOR {0}]Clear Packages: None Found![/COLOR]'.format(CONFIG.COLOR2))
        except Exception as e:
            logging.log_notify(CONFIG.ADDONTITLE,
                      '[COLOR {0}]Clear Packages: Error![/COLOR]'.format(CONFIG.COLOR2))
            logging.log("Clear Packages Error: {0}".format(str(e)), level=xbmc.LOGERROR)
    else:
        logging.log_notify(CONFIG.ADDONTITLE,
                  '[COLOR {0}]Clear Packages: None Found![/COLOR]'.format(CONFIG.COLOR2))


def clear_packages_startup():
    from resources.libs.common import tools

    start = datetime.utcnow() - timedelta(minutes=3)
    file_count = 0
    cleanupsize = 0
    if os.path.exists(CONFIG.PACKAGES):
        pack = os.listdir(CONFIG.PACKAGES)
        pack.sort(key=lambda f: os.path.getmtime(os.path.join(CONFIG.PACKAGES, f)))
        try:
            for item in pack:
                file = os.path.join(CONFIG.PACKAGES, item)
                lastedit = datetime.utcfromtimestamp(os.path.getmtime(file))
                if lastedit <= start:
                    if os.path.isfile(file):
                        file_count += 1
                        cleanupsize += os.path.getsize(file)
                        os.unlink(file)
                    elif os.path.isdir(file):
                        cleanupsize += tools.get_size(file)
                        cleanfiles, cleanfold = tools.clean_house(file)
                        file_count += cleanfiles + cleanfold
                        try:
                            shutil.rmtree(file)
                        except Exception as e:
                            logging.log("Failed to remove {0}: {1}".format(file, str(e), xbmc.LOGERROR))
            if file_count > 0:
                logging.log_notify(CONFIG.ADDONTITLE,
                          '[COLOR {0}]Clear Packages: Success: {1}[/COLOR]'.format(CONFIG.COLOR2, tools.convert_size(cleanupsize)))
            else:
                logging.log_notify(CONFIG.ADDONTITLE,
                          '[COLOR {0}]Clear Packages: None Found![/COLOR]'.format(CONFIG.COLOR2))
        except Exception as e:
            logging.log_notify(CONFIG.ADDONTITLE,
                      '[COLOR {0}]Clear Packages: Error![/COLOR]'.format(CONFIG.COLOR2))
            logging.log("Clear Packages Error: {0}".format(str(e)), level=xbmc.LOGERROR)
    else:
        logging.log_notify(CONFIG.ADDONTITLE,
                  '[COLOR {0}]Clear Packages: None Found![/COLOR]'.format(CONFIG.COLOR2))


def clear_archive(over=False):
    dialog = xbmcgui.Dialog()

    if over or dialog.yesno(CONFIG.ADDONTITLE,
                        '[COLOR {0}]Would you like to clear the \'Archive_Cache\' folder?[/COLOR]'.format(CONFIG.COLOR2),
                        nolabel='[B][COLOR red]No, Cancel[/COLOR][/B]',
                        yeslabel='[B][COLOR springgreen]Yes Clear[/COLOR][/B]'):
        if os.path.exists(CONFIG.ARCHIVE_CACHE):
            from resources.libs.common import tools
            tools.clean_house(CONFIG.ARCHIVE_CACHE)


def clear_function_cache(over=False):
    dialog = xbmcgui.Dialog()

    if not over:
        if dialog.yesno(CONFIG.ADDONTITLE,
                            '[COLOR {0}]Would you like to clear resolver function caches?[/COLOR]'.format(CONFIG.COLOR2),
                            nolabel='[B][COLOR red]No, Cancel[/COLOR][/B]',
                            yeslabel='[B][COLOR springgreen]Clear Cache[/COLOR][/B]'):
            clear = True
    else:
        clear = True
        
    if clear:
        if xbmc.getCondVisibility('System.HasAddon(script.module.resolveurl)'):
                xbmc.executebuiltin('RunPlugin(plugin://script.module.resolveurl/?mode=reset_cache)')
        if xbmc.getCondVisibility('System.HasAddon(script.module.urlresolver)'):
            xbmc.executebuiltin('RunPlugin(plugin://script.module.urlresolver/?mode=reset_cache)')


def clear_cache(over=None):
    PROFILEADDONDATA, cachelist = _folder_cache_paths(for_clear=True)

    delfiles = 0
    excludes = ['meta_cache', 'archive_cache']
    for item in cachelist:
        if not os.path.exists(item):
            continue
        if item not in [CONFIG.ADDON_DATA, PROFILEADDONDATA]:
            for root, dirs, files in os.walk(item):
                dirs[:] = [d for d in dirs if d not in excludes]
                file_count = 0
                file_count += len(files)
                if file_count > 0:
                    for f in files:
                        if f not in CONFIG.LOGFILES:
                            try:
                                os.unlink(os.path.join(root, f))
                                logging.log("[Wiped] {0}".format(os.path.join(root, f)))
                                delfiles += 1
                            except OSError as e:
                                logging.log("[Failed] to wipe {0}: {1}".format(os.path.join(root, f), e), level=xbmc.LOGDEBUG)
                        else:
                            logging.log('Ignore Log File: {0}'.format(f))
                    for d in dirs:
                        try:
                            shutil.rmtree(os.path.join(root, d))
                            delfiles += 1
                            logging.log("[Success] cleared {0} files from {1}".format(str(file_count), os.path.join(item, d)),
                                        level=xbmc.LOGINFO)
                        except OSError:
                            logging.log("[Failed] to wipe cache in: {0}".format(os.path.join(item, d)),
                                        level=xbmc.LOGINFO)
        else:
            for root, dirs, files in os.walk(item):
                dirs[:] = [d for d in dirs if d not in excludes]
                for d in dirs:
                    if not str(d.lower()).find('cache') == -1:
                        try:
                            shutil.rmtree(os.path.join(root, d))
                            delfiles += 1
                            logging.log("[Success] wiped {0} ".format(os.path.join(root, d)))
                        except OSError:
                            logging.log("[Failed] to wipe cache in: {0}".format(os.path.join(item, d)))

    for item in _stale_install_temp():
        try:
            if os.path.isdir(item):
                shutil.rmtree(item)
            else:
                os.unlink(item)
            delfiles += 1
            logging.log("[Success] removed leftover install folder {0}".format(item), level=xbmc.LOGINFO)
        except OSError as e:
            logging.log("[Failed] to remove {0}: {1}".format(item, e), level=xbmc.LOGINFO)

    if CONFIG.get_setting('includevideo') == 'true' and over is None:
        files = cache_registry.db_paths(CONFIG.ADDON_DATA, CONFIG.get_setting('includeall') == 'true', _include_flag)
        if len(files) > 0:
            present = [item for item in files if os.path.exists(item)]
            rows = dict((item, dbwipe.count_rows(item) or 0) for item in present)
            total = sum(rows.values())
            if total > 0:
                names = [os.path.relpath(item, CONFIG.ADDON_DATA) for item in present if rows[item] > 0]
                per_addon = []
                for name in names:   # the dialog has room for one short line: "Seren (4), POV (3), ..."
                    addon_id = name.replace('\\', '/').split('/')[0]
                    if per_addon and per_addon[-1][0] == addon_id:
                        per_addon[-1][1] += 1
                    else:
                        per_addon.append([addon_id, 1])
                shown = ', '.join('{0} ({1})'.format(cache_registry.addon_title(a), n) for a, n in per_addon)
                if len(shown) > 90:
                    shown = shown[:87] + '...'
                logging.log("Clear Cache: emptying {0} cache database(s) holding {1} rows: {2}".format(len(names), total, shown))
            for item in present:
                deleted = dbwipe.wipe_db(item, log=_db_log)
                if deleted is not None:
                    delfiles += 1
                    logging.log("[Success] wiped {0} rows in {1}".format(deleted, item))
        else:
            logging.log("Clear Cache: Clear Video Cache Not Enabled")
    logging.log_notify(CONFIG.ADDONTITLE,
                       '[COLOR {0}]Clear Cache: Removed {1} Files[/COLOR]'.format(CONFIG.COLOR2, delfiles))


def old_thumbs():
    from resources.libs import db
    from resources.libs.common import tools

    dbfile = os.path.join(CONFIG.DATABASE, db.latest_db('Textures'))
    use = 30
    week = tools.get_date(days=-7)
    ids = []
    images = []
    size = 0
    if os.path.exists(dbfile):
        try:
            textdb = database.connect(dbfile, isolation_level=None)
            textexe = textdb.cursor()
        except Exception as e:
            logging.log("DB Connection Error: {0}".format(str(e)), level=xbmc.LOGERROR)
            return False
    else:
        logging.log('{0} not found.'.format(dbfile), level=xbmc.LOGERROR)
        return False
    textexe.execute("SELECT idtexture FROM sizes WHERE usecount < ? AND lastusetime < ?", (use, str(week)))
    found = textexe.fetchall()
    for rows in found:
        idfound = rows[0]
        ids.append(idfound)
        textexe.execute("SELECT cachedurl FROM texture WHERE id = ?", (idfound, ))
        found2 = textexe.fetchall()
        for rows2 in found2:
            images.append(rows2[0])
    logging.log("{0} total thumbs cleaned up.".format(str(len(images))))
    for id in ids:
        textexe.execute("DELETE FROM sizes WHERE idtexture = ?", (id, ))
        textexe.execute("DELETE FROM texture WHERE id = ?", (id, ))
    textexe.execute("VACUUM")
    textdb.commit()
    textexe.close()
    for image in images:
        path = os.path.join(CONFIG.THUMBNAILS, image)
        try:
            imagesize = os.path.getsize(path)
            os.remove(path)
            size += imagesize
        except OSError as e:
            logging.log("[Failed] to remove thumbnail {0}: {1}".format(path, e), level=xbmc.LOGDEBUG)
    removed = tools.convert_size(size)
    if len(images) > 0:
        logging.log_notify(CONFIG.ADDONTITLE,
                           '[COLOR {0}]Clear Thumbs: {1} Files / {2} MB[/COLOR]!'.format(CONFIG.COLOR2, str(len(images)), removed))
    else:
        logging.log_notify(CONFIG.ADDONTITLE,
                           '[COLOR {0}]Clear Thumbs: None Found![/COLOR]'.format(CONFIG.COLOR2))


def clear_crash(over=False):
    files = []
    for file in glob.glob(os.path.join(CONFIG.LOGPATH, '*crashlog*.*')):
        files.append(file)
    if len(files) > 0:
        dialog = xbmcgui.Dialog()

        if over or dialog.yesno(CONFIG.ADDONTITLE,
                            '[COLOR {0}]Would you like to delete the Crash logs?'.format(CONFIG.COLOR2)
                            +'\n'+'[COLOR {0}]{1}[/COLOR] Files Found[/COLOR]'.format(CONFIG.COLOR1, len(files)),
                            yeslabel="[B][COLOR springgreen]Remove Logs[/COLOR][/B]",
                            nolabel="[B][COLOR red]Keep Logs[/COLOR][/B]"):
            for f in files:
                os.remove(f)
            logging.log_notify('[COLOR {0}]Clear Crash Logs[/COLOR]'.format(CONFIG.COLOR1),
                               '[COLOR {0}]{1} Crash Logs Removed[/COLOR]'.format(CONFIG.COLOR2, len(files)))
        else:
            logging.log_notify(CONFIG.ADDONTITLE,
                               '[COLOR {0}]Clear Crash Logs Cancelled[/COLOR]'.format(CONFIG.COLOR2))
    else:
        logging.log_notify('[COLOR {0}]Clear Crash Logs[/COLOR]'.format(CONFIG.COLOR1),
                           '[COLOR {0}]No Crash Logs Found[/COLOR]'.format(CONFIG.COLOR2))


def force_text():
    tools.clean_house(CONFIG.TEXTCACHE)
    logging.log_notify(CONFIG.ADDONTITLE,
                       '[COLOR {0}]Text Files Flushed![/COLOR]'.format(CONFIG.COLOR2))


def toggle_cache(state):
    cachelist = cache_registry.toggle_ids()
    titlelist = cache_registry.toggle_titles()
    if state in ['true', 'false']:
        for item in cachelist:
            CONFIG.set_setting(item, state)
    else:
        if state not in ['includevideo', 'includeall'] and CONFIG.get_setting('includeall') == 'true':
            try:
                dialog = xbmcgui.Dialog()

                item = titlelist[cachelist.index(state)]
                dialog.ok(CONFIG.ADDONTITLE,
                              "[COLOR {0}]You will need to turn off [COLOR {1}]Include All Addons[/COLOR] to disable[/COLOR] [COLOR {2}]{3}[/COLOR]".format(CONFIG.COLOR2, CONFIG.COLOR1, CONFIG.COLOR1, item))
            except:
                logging.log_notify("[COLOR {0}]Toggle Cache[/COLOR]".format(CONFIG.COLOR1),
                                   "[COLOR {0}]Invalid Add-on ID: {1}[/COLOR]".format(CONFIG.COLOR2, state))
        else:
            new = 'true' if CONFIG.get_setting(state) == 'false' else 'false'
            CONFIG.set_setting(state, new)


def total_clean():
    dialog = xbmcgui.Dialog()

    if dialog.yesno(CONFIG.ADDONTITLE,
                        '[COLOR {0}]Would you like to clear cache, packages, thumbnails, old thumbnails, crash logs and the archive cache?[/COLOR]'.format(CONFIG.COLOR2),
                        nolabel='[B][COLOR red]Cancel Process[/COLOR][/B]',
                        yeslabel='[B][COLOR springgreen]Clean All[/COLOR][/B]'):
        clear_archive(over=True)
        clear_cache()
        clear_function_cache(over=True)
        clear_packages('total')
        old_thumbs()  # before clear_thumbs: it needs the Textures database that clear_thumbs deletes
        clear_thumbs('total')
        clear_crash(over=True)


def clear_thumbs(type=None):
    from resources.libs import db
    
    dialog = xbmcgui.Dialog()

    thumb_locations = {CONFIG.THUMBNAILS,
                       os.path.join(CONFIG.ADDON_DATA, 'script.module.metadatautils', 'animatedgifs'),
                       os.path.join(CONFIG.ADDON_DATA, 'script.extendedinfo', 'images')}

    latest = db.latest_db('Textures')
    if type is not None:
        choice = 1
    else:
        choice = dialog.yesno(CONFIG.ADDONTITLE, '[COLOR {0}]Would you like to delete the {1} and related thumbnail folders?'.format(CONFIG.COLOR2, latest) + '\n' + "They will repopulate on the next startup[/COLOR]", nolabel='[B][COLOR red]Don\'t Delete[/COLOR][/B]', yeslabel='[B][COLOR springgreen]Delete Thumbs[/COLOR][/B]')
    if choice == 1:
        try:
            tools.remove_file(os.path.join(CONFIG.DATABASE, latest))
        except:
            logging.log('Failed to delete, Purging DB.')
            db.purge_db_file(latest)
        for i in thumb_locations:
            tools.remove_folder(i)
    else:
        logging.log('Clear thumbnames cancelled')

    tools.redo_thumbs()


def remove_addon(addon, name, over=False, data=True):
    import sqlite3
    from resources.libs import db
    
    if over:
        yes = 1
    else:
        dialog = xbmcgui.Dialog()
        
        yes = dialog.yesno(CONFIG.ADDONTITLE,
                               '[COLOR {0}]Are you sure you want to delete the add-on:'.format(CONFIG.COLOR2)
                               +'\n'+'Name: [COLOR {0}]{1}[/COLOR]'.format(CONFIG.COLOR1, name)
                               +'\n'+'ID: [COLOR {0}]{1}[/COLOR][/COLOR]'.format(CONFIG.COLOR1, addon),
                               yeslabel='[B][COLOR springgreen]Remove Add-on[/COLOR][/B]',
                               nolabel='[B][COLOR red]Don\'t Remove[/COLOR][/B]')
    if yes == 1:
        folder = os.path.join(CONFIG.ADDONS, addon)
        logging.log("Removing Add-on: {0}".format(addon))

        from resources.libs.common import tools
        tools.clean_house(folder)
        xbmc.sleep(200)
        
        xbmc.executebuiltin('StopScript({0})'.format(addon))
        
        sqldb = sqlite3.connect(os.path.join(CONFIG.DATABASE, db.latest_db('Addons')))
        sqlexe = sqldb.cursor()
        query = "DELETE FROM {0} WHERE addonID = '{1}'"
        
        for table in ['addons', 'installed', 'package']:
            sqlexe.execute(query.format(table, addon))
        
        try:
            shutil.rmtree(folder)
        except Exception as e:
            logging.log("Error removing {0}: {1}".format(addon, str(e)))
        
        if data:
            remove_addon_data(addon)
            
        return True
            
    if not over:
        logging.log_notify(CONFIG.ADDONTITLE,
                           "[COLOR {0}]{1} Removed[/COLOR]".format(CONFIG.COLOR2, name))


def remove_addon_data(addon):
    dialog = xbmcgui.Dialog()

    if addon == 'all':  # clear ALL addon data
        if dialog.yesno(CONFIG.ADDONTITLE,
                            '[COLOR {0}]Would you like to remove [COLOR {1}]ALL[/COLOR] addon data stored in your userdata folder?[/COLOR]'.format(CONFIG.COLOR2, CONFIG.COLOR1),
                            yeslabel='[B][COLOR springgreen]Remove Data[/COLOR][/B]',
                            nolabel='[B][COLOR red]Don\'t Remove[/COLOR][/B]'):
            tools.clean_house(CONFIG.ADDON_DATA)
        else:
            logging.log_notify('[COLOR {0}]Remove Addon Data[/COLOR]'.format(CONFIG.COLOR1),
                               '[COLOR {0}]Cancelled![/COLOR]'.format(CONFIG.COLOR2))
    elif addon == 'uninstalled':  # clear addon data for uninstalled addons
        if dialog.yesno(CONFIG.ADDONTITLE,
                            '[COLOR {0}]Would you like to remove [COLOR {1}]ALL[/COLOR] addon data stored in your userdata folder for uninstalled addons?[/COLOR]'.format(CONFIG.COLOR2, CONFIG.COLOR1),
                            yeslabel='[B][COLOR springgreen]Remove Data[/COLOR][/B]',
                            nolabel='[B][COLOR red]Don\'t Remove[/COLOR][/B]'):
                            
            total = 0
            
            for folder in glob.glob(os.path.join(CONFIG.ADDON_DATA, '*')):
                foldername = folder.replace(CONFIG.ADDON_DATA, '').replace('\\', '').replace('/', '')
                if foldername in CONFIG.EXCLUDES:
                    pass
                elif os.path.exists(os.path.join(CONFIG.ADDONS, foldername)):
                    pass
                elif os.path.isdir(folder):
                    tools.clean_house(folder)
                    total += 1
                    logging.log(folder)
                    shutil.rmtree(folder)
            logging.log_notify('[COLOR {0}]Clean up Uninstalled[/COLOR]'.format(CONFIG.COLOR1),
                               '[COLOR {0}]{1} Folders(s) Removed[/COLOR]'.format(CONFIG.COLOR2, total))
        else:
            logging.log_notify('[COLOR {0}]Remove Add-on Data[/COLOR]'.format(CONFIG.COLOR1),
                               '[COLOR {0}]Cancelled![/COLOR]'.format(CONFIG.COLOR2))
    elif addon == 'empty':  # clear empty folders from addon_data
        if dialog.yesno(CONFIG.ADDONTITLE,
                            '[COLOR {0}]Would you like to remove [COLOR {1}]ALL[/COLOR] empty addon data folders in your userdata folder?[/COLOR]'.format(CONFIG.COLOR2, CONFIG.COLOR1),
                            yeslabel='[B][COLOR springgreen]Remove Data[/COLOR][/B]',
                            nolabel='[B][COLOR red]Don\'t Remove[/COLOR][/B]'):
            total = tools.empty_folder(CONFIG.ADDON_DATA)
            logging.log_notify('[COLOR {0}]Remove Empty Folders[/COLOR]'.format(CONFIG.COLOR1),
                               '[COLOR {0}]{1} Folders(s) Removed[/COLOR]'.format(CONFIG.COLOR2, total))
        else:
            logging.log_notify('[COLOR {0}]Remove Empty Folders[/COLOR]'.format(CONFIG.COLOR1),
                               '[COLOR {0}]Cancelled![/COLOR]'.format(CONFIG.COLOR2))
    else:  # clear addon data for a specific addon
        addon_data = os.path.join(CONFIG.ADDON_DATA, addon)
        if addon in CONFIG.EXCLUDES:
            logging.log_notify("[COLOR {0}]Protected Plugin[/COLOR]".format(CONFIG.COLOR1),
                               "[COLOR {0}]Not allowed to remove add-on data[/COLOR]".format(CONFIG.COLOR2))
        elif os.path.exists(addon_data):
            if dialog.yesno(CONFIG.ADDONTITLE, '[COLOR {0}]Would you also like to remove the add-on data for:[/COLOR]'.format(CONFIG.COLOR2) + '\n' + '[COLOR {0}]{1}[/COLOR]'.format(CONFIG.COLOR1, addon), yeslabel='[B][COLOR springgreen]Remove Data[/COLOR][/B]', nolabel='[B][COLOR red]Don\'t Remove[/COLOR][/B]'):
                tools.clean_house(addon_data)
                try:
                    shutil.rmtree(addon_data)
                except:
                    logging.log("Error deleting: {0}".format(addon_data))
            else:
                logging.log('Add-on data for {0} was not removed'.format(addon))
    xbmc.executebuiltin('Container.Refresh()')

    
def remove_addon_menu():
    from resources.libs.common import logging
    from resources.libs.common import tools
    from resources.libs import update
    
    from xml.etree import ElementTree
    
    dialog = xbmcgui.Dialog()

    addonfolders = glob.iglob(os.path.join(CONFIG.ADDONS, '*/'))
    addonnames = []
    addonids = []
    
    for folder in addonfolders:
        foldername = os.path.split(folder[:-1])[1]
        
        if foldername in CONFIG.EXCLUDES:
            continue
        elif foldername in CONFIG.DEFAULTPLUGINS:
            continue
        elif foldername == 'packages':
            continue    
        
        xml = os.path.join(folder, 'addon.xml')
        
        if os.path.exists(xml):
            root = ElementTree.parse(xml).getroot()
            addonid = root.get('id')
            addonname = root.get('name')
            
            try:
                addonnames.append(addonname)
                addonids.append(addonid)
            except:
                pass
                
    if len(addonnames) == 0:
        logging.log_notify(CONFIG.ADDONTITLE,
                           "[COLOR {0}]No Addons To Remove[/COLOR]".format(CONFIG.COLOR2))
        return
    selected = dialog.multiselect("{0}: Select the addons you wish to remove.".format(CONFIG.ADDONTITLE), addonnames)
    if not selected:
        return
    if len(selected) > 0:
        update.addon_updates('set')
        for addon in selected:
            remove_addon(addon=addonids[addon], name=addonnames[addon], over=True)

        xbmc.sleep(500)

        dialog.ok(CONFIG.ADDONTITLE, "[COLOR {0}]To save changes you now need to force close Kodi, Press OK to force close Kodi[/COLOR]".format(CONFIG.COLOR2))
        
        update.addon_updates('reset')
        tools.kill_kodi(over=True)
