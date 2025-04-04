import re
import string
import xbmc


from resources.lib.ui import control

res = ['EQ', '480p', '720p', '1080p', '4k']


def getAudio_lang(release_title):
    release_title = cleanTitle(release_title)
    if any(i in release_title for i in ['multi audio', 'multi lang', 'multiple audio', 'multiple lang']):
        lang = 0
    elif any(i in release_title for i in ['dual audio']):
        lang = 1
    elif any(i in release_title for i in ['dub', 'dubbed']):
        lang = 3
    else:
        lang = 2
    return lang


def getAudio_channel(release_title):
    release_title = cleanTitle(release_title)
    if any(i in release_title for i in ['2 0 ', '2 0ch', '2ch']):
        channel = 0
    elif any(i in release_title for i in ['5 1 ', '5 1ch', '6ch']):
        channel = 1
    elif any(i in release_title for i in ['7 1 ', '7 1ch', '8ch']):
        channel = 2
    else:
        channel = 3
    return channel


def getSubtitle_lang(release_title):
    release_title = cleanTitle(release_title)
    if any(i in release_title for i in ['multi sub', 'multiple sub']):
        sub = 0
    else:
        sub = 1
    return sub


def getQuality(release_title):
    release_title = release_title.lower()
    if any(i in release_title for i in ['4k', '2160', "216o"]):
        quality = 4
    elif any(i in release_title for i in ["1080", "1o80", "108o", "1o8o"]):
        quality = 3
    elif any(i in release_title for i in ["720", "72o"]):
        quality = 2
    else:
        quality = 1
    return quality


def getInfo(release_title):
    info = []
    release_title = cleanTitle(release_title)
    # info.video
    if any(i in release_title for i in ['x264', 'x 264', 'h264', 'h 264', 'avc']):
        info.append('AVC')
    if any(i in release_title for i in ['x265', 'x 265', 'h265', 'h 265', 'hevc']):
        info.append('HEVC')
    if any(i in release_title for i in ['xvid']):
        info.append('XVID')
    if any(i in release_title for i in ['divx']):
        info.append('DIVX')
    if any(i in release_title for i in ['mp4']):
        info.append('MP4')
    if any(i in release_title for i in ['wmv']):
        info.append('WMV')
    if any(i in release_title for i in ['mpeg']):
        info.append('MPEG')
    if any(i in release_title for i in ['vp9']):
        info.append('VP9')
    if any(i in release_title for i in ['av1']):
        info.append('AV1')
    if any(i in release_title for i in ['remux', 'bdremux']):
        info.append('REMUX')
    if any(i in release_title for i in [' hdr ', 'hdr10', 'hdr 10', 'uhd bluray 2160p', 'uhd blu ray 2160p', '2160p uhd bluray', '2160p uhd blu ray', '2160p bluray hevc truehd', '2160p bluray hevc dts', '2160p bluray hevc lpcm', '2160p us bluray hevc truehd', '2160p us bluray hevc dts']):
        info.append('HDR')
    if any(i in release_title for i in [' sdr ']):
        info.append('SDR')
    if any(i in release_title for i in [' dv ', 'dovi', 'dolby vision', 'dolbyvision']):
        info.append('DV')

    # info.audio
    if any(i in release_title for i in ['aac']):
        info.append('AAC')
    if any(i in release_title for i in ['dts']):
        info.append('DTS')
    if any(i in release_title for i in ['hd ma', 'hdma']):
        info.append('DTS-HDMA')
    if any(i in release_title for i in ['hd hr', 'hdhr', 'dts hr', 'dtshr']):
        info.append('DTS-HDHR')
    if any(i in release_title for i in ['dtsx', ' dts x']):
        info.append('DTS-X')
    if any(i in release_title for i in ['atmos']):
        info.append('ATMOS')
    if any(i in release_title for i in ['truehd', 'true hd']):
        info.append('TRUEHD')
    if any(i in release_title for i in ['ddp', 'dd+', 'eac3', ' e ac3', ' e ac 3']):
        info.append('DD+')
    if any(i in release_title for i in [' dd ', 'dd2', 'dd5', 'dd7', ' ac3', ' ac 3']):
        info.append('DD')
    if any(i in release_title for i in ['mp3']):
        info.append('MP3')
    if any(i in release_title for i in [' wma']):
        info.append('WMA')
    if any(i in release_title for i in ['opus']):
        info.append('OPUS')
    if any(i in release_title for i in ['dub', 'dubbed']):
        info.append('DUB')
    if any(i in release_title for i in ['dual audio']):
        info.append('DUAL-AUDIO')
    if any(i in release_title for i in ['multi audio', 'multi lang', 'multiple audio', 'multiple lang']):
        info.append('MULTI-AUDIO')

    # info.channels
    if any(i in release_title for i in ['2 0 ', '2 0ch', '2ch']):
        info.append('2.0')
    if any(i in release_title for i in ['5 1 ', '5 1ch', '6ch']):
        info.append('5.1')
    if any(i in release_title for i in ['7 1 ', '7 1ch', '8ch']):
        info.append('7.1')

    # info.subtitles
    if any(i in release_title for i in ['multi sub', 'multiple sub']):
        info.append('MULTI-SUB')

    # info.source
    # no point at all with WEBRip vs WEB-DL cuz it's always labeled wrong with TV Shows
    # WEB = WEB-DL in terms of size and quality
    if any(i in release_title for i in ['bluray', 'blu ray', 'bdrip', 'bd rip', 'brrip', 'br rip']):
        info.append('BLURAY')
    if any(i in release_title for i in [' web ', 'webrip', 'webdl', 'web rip', 'web dl']):
        info.append('WEB')
    if any(i in release_title for i in [' hdrip', ' hd rip']):
        info.append('HDRIP')
    if any(i in release_title for i in ['dvdrip', 'dvd rip']):
        info.append('DVDRIP')
    if any(i in release_title for i in ['hdtv']):
        info.append('HDTV')
    if any(i in release_title for i in ['pdtv']):
        info.append('PDTV')
    if any(i in release_title for i in [' cam ', 'camrip', 'hdcam', 'hd cam', ' ts ', 'hd ts', 'hdts', 'telesync', ' tc ', 'hd tc', 'hdtc', 'telecine', 'xbet']):
        info.append('CAM')
    if any(i in release_title for i in ['dvdscr', ' scr ', 'screener']):
        info.append('SCR')
    if any(i in release_title for i in ['korsub', ' kor ', ' hc']):
        info.append('HC')
    if any(i in release_title for i in ['blurred']):
        info.append('BLUR')
    if any(i in release_title for i in [" 3d", " half ou", " half sbs"]):
        info.append('3D')
    if any(i in release_title for i in [" 60 fps", " 60fps"]):
        info.append('60-FPS')

    # info.batch
    if any(i in release_title for i in ['batch', 'complete series']):
        info.append('BATCH')

    return info


def get_cache_check_reg(episode):
    # playList = control.playList
    # playList_position = playList.getposition()
    # if playList_position != -1:
    #     info = playList[playList_position].getVideoInfoTag()
    #     season = str(info.getSeason()).zfill(2)
    # else:
    #     season = ''
    episode = str(episode)
    season = ''
    # if control.getBool('regex.question'):
    #     reg_string = r'''(?ix)                              # Ignore case (i), and use verbose regex (x)
    #                  (?:                                    # non-grouping pattern
    #                    s|season                             # s or season
    #                    )?
    #                  ({})?                                  # season num format
    #                  (?:                                    # non-grouping pattern
    #                    e|x|episode|ep|ep\.|_|-|\(           # e or x or episode or start of a line
    #                    )?                                   # end non-grouping pattern
    #                  \s*                                    # 0-or-more whitespaces
    #                  (?<![\d])
    #                  ({}|{})                                # episode num format: xx or xxx
    #                  (?![\d])
    #                  '''.format(season, episode.zfill(2), episode.zfill(3))
    # else:
    reg_string = r'''(?ix)                              # Ignore case (i), and use verbose regex (x)
                 (?:                                    # non-grouping pattern
                   s|season                             # s or season
                   )?
                 ({})?                                  # season num format
                 (?:                                    # non-grouping pattern
                   e|x|episode|ep|ep\.|_|-|\(           # e or x or episode or start of a line
                   )                                    # end non-grouping pattern
                 \s*                                    # 0-or-more whitespaces
                 (?<![\d])
                 ({}|{}|{})                             # episode num format: xx or xxx or xxxx
                 (?![\d])
                 '''.format(season, episode.zfill(2), episode.zfill(3), episode.zfill(4))
    return re.compile(reg_string)


def convert_to_bytes(size, units):
    unit = units.upper()
    if unit == 'KB':
        byte_size = size * 2**10
    elif unit == 'MB':
        byte_size = size * 2**20
    elif unit == 'GB':
        byte_size = size * 2**30
    elif unit == 'TB':
        byte_size = size * 2**40
    else:
        raise ValueError("Unit must be 'KB', 'MB', 'GB', 'TB' ")
    return byte_size


def get_size(size=0):
    power = 1024.0
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB'}
    while size > power:
        size /= power
        n += 1
    return '{0:.2f} {1}'.format(size, power_labels[n])


def get_best_match(dict_key, dictionary_list, episode, pack_select=False):
    regex = get_cache_check_reg(episode)
    files = []
    for i in dictionary_list:
        path = re.sub(r'\[.*?]', '', i[dict_key].split('/')[-1])
        if not is_file_ext_valid(path):
            continue
        i['regex_matches'] = regex.findall(path)
        files.append(i)
    if pack_select:
        files = user_select(files, dict_key)
    else:
        files = [i for i in files if len(i['regex_matches']) > 0]
        if len(files) == 0:
            return {}
        files = sorted(files, key=lambda x: len(' '.join(list(x['regex_matches'][0]))), reverse=True)
        if len(files) != 1:
            files = user_select(files, dict_key)

    return files[0]


def filter_sources(provider, torrent_list, season=None, episode=None, anidb_id=None, part=None, invert=True):
    """
    Combined filter:
      - When invert is False (default), it returns torrents that have valid episode (and season) info.
        (Uses season and episode parameters for comparison.)
      - When invert is True, it returns torrents that DO NOT have any episode, season, or part info.
        (In this case season/episode comparisons are skipped.)
    """
    import itertools

    # Common regex patterns
    regex_season = r"(?i)\b(?:s(?:eason)?[ ._-]?(\d{1,2}))(?=\D|$)"
    rex_season = re.compile(regex_season)
    regex_ep = r"(?i)(?:s(?:eason)?\s?\d{1,2})?[ ._-]?(?:e(?:p)?\s?(\d{1,4})(?!\s*(?:st|nd|rd|th))(?:v\d+)?)?(?:[ ._-]?[-~][ ._-]?e?(?:p)?\s?(\d{1,4})(?!\s*(?:st|nd|rd|th)))?|(?:-\s?(\d{1,4})(?!\s*(?:st|nd|rd|th))\b)"
    rex_ep = re.compile(regex_ep)
    regex_part = r"part ?(\d+)"
    rex_part = re.compile(regex_part)

    filtered = []

    # Loop over each torrent in the list
    for torrent in torrent_list:
        # Set up the torrent hash as in the original functions
        if provider == 'animetosho':
            if 'hash' not in torrent:
                continue
        elif provider == 'nyaa':
            torrent['hash'] = re.findall(r'btih:(.*?)(?:&|$)', torrent['magnet'])[0]
        elif provider == 'realdebrid':
            torrent['hash'] = torrent.get('hash', '')
        elif provider == 'alldebrid':
            link = torrent['link']
            torrent['hash'] = re.search(r'/f/([^/]+)', link).group(1)
        elif provider == 'premiumize':
            torrent['hash'] = torrent.get('id', '')
        elif provider == 'torbox':
            torrent['hash'] = torrent.get('hash', '')
        elif provider == 'local':
            torrent['hash'] = torrent.get('path', '')
        else:
            continue

        # Select the title based on provider
        if provider in ['realdebrid', 'alldebrid']:
            title = torrent['filename'].lower()
        else:
            title = torrent['name'].lower()

        # Clean the title for extraction (using your clean_text helper)
        clean_title = clean_text(title)

        # If a part is expected, filter out torrents that don’t match
        if rex_part and 'part' in title:
            part_match = rex_part.search(title)
            if part_match:
                current_part = int(part_match.group(1).strip())
                if part is not None and current_part != part:
                    continue

        # Extract episode matches (convert to ints)
        ep_match = rex_ep.findall(clean_title)
        ep_match = list(filter(None, itertools.chain(*ep_match)))
        # Ignore if the only match is a single digit "0"
        ep_match = [int(match) for match in ep_match if not (len(match) == 1 and match == '0')]
        # Extract season matches
        season_match = rex_season.findall(title)
        season_match = [int(s) for s in season_match if s]

        # Determine if the torrent has episode/season/part info
        has_info = bool(ep_match or season_match or (rex_part.search(title) if 'part' in title else None))

        # For the inverted filter, we want torrents with no info.
        if invert:
            if not has_info:
                filtered.append(torrent)

        # In the non-inverted case, we need to match the expected episode and season.
        # First, if no episode info was found, skip this torrent.
        if not ep_match:
            continue
        # Then check that the episode matches the requested one.
        # (Assumes episode is passed as a string that can be converted to int.)
        try:
            req_ep = int(episode)
        except (ValueError, TypeError):
            continue
        # If the first episode number doesn't match and a range isn’t provided, skip.
        if ep_match[0] != req_ep:
            # If a range is provided (two numbers), check if it falls within
            if not (len(ep_match) > 1 and ep_match[0] <= req_ep <= ep_match[1]):
                continue

        # Now filter based on season if not using anidb_id (or if season info exists)
        if not anidb_id:
            if season_match:
                try:
                    req_season = int(season)
                except (ValueError, TypeError):
                    continue
                if not (season_match[0] <= req_season <= season_match[-1]):
                    continue

        filtered.append(torrent)

    return filtered


# Example helper: clean_text remains the same
def clean_text(text):
    text = re.sub(r"\[.*?\]|\(.*?\)", "", text).strip()
    text = re.sub(r"\b(?:480p|720p|1080p|2160p|4k|h\.264|x264|x265|hevc|web-dl|webrip|bluray|hdr)\b",
                  "", text, flags=re.I)
    return text


def clean_text(text):
    text = re.sub(r"\[.*?\]|\(.*?\)", "", text).strip()  # Remove brackets
    text = re.sub(r"\b(?:480p|720p|1080p|2160p|4k|h\.264|x264|x265|hevc|web-dl|webrip|bluray|hdr)\b", "", text, flags=re.I)  # Remove resolutions
    return text


def cleanTitle(title):
    title = title.lower()
    result = ''.join(char for char in title if char in string.printable)
    title = result.encode('ascii', errors='ignore').decode('ascii', errors='ignore')
    apostrophe_replacement = 's'
    title = title.replace("\\'s", apostrophe_replacement)
    title = title.replace("'s", apostrophe_replacement)
    title = title.replace("&#039;s", apostrophe_replacement)
    title = title.replace(" 039 s", apostrophe_replacement)
    title = re.sub(r'[:/,!?()\'"\\\[\]\-_.]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'&', 'and', title)
    return title.strip()


def is_file_ext_valid(file_name):
    return False if '.' + file_name.split('.')[-1] not in video_ext() else True


def video_ext():
    COMMON_VIDEO_EXTENSIONS = xbmc.getSupportedMedia('video').split('|')
    COMMON_VIDEO_EXTENSIONS = [i for i in COMMON_VIDEO_EXTENSIONS if i != '' and i != '.zip']
    return COMMON_VIDEO_EXTENSIONS


def user_select(files, dict_key):
    idx = control.select_dialog('Select File', [i[dict_key].rsplit('/')[-1] for i in files])
    if idx == -1:
        file = [{'path': ''}]
    else:
        file = [files[idx]]
    return file


def get_embedhost(url):
    s = re.search(r'(?://|\.)([^.]+)\.', url)
    return s.group(1)
