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


def get_fuzzy_match(query, filenames):
    import difflib
    threshold_percent = control.getInt('general.fuzzy')
    threshold = threshold_percent / 100.0
    query_lower = query.lower()
    filenames_lower = [f.lower() for f in filenames]

    scored = []
    for i, name in enumerate(filenames_lower):
        ratio = difflib.SequenceMatcher(None, query_lower, name).ratio()
        if ratio >= threshold:
            scored.append((i, ratio))

    # Optional: sort by best match first
    scored.sort(key=lambda x: x[1], reverse=True)
    return [i for i, _ in scored]


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


def filter_sources(provider, torrent_list, mal_id, season=None, episode=None, part=None, anidb_id=True):
    from resources.lib.ui import database
    """
    Filter torrents based on season, episode, and part information.
    Uses improved regex patterns to handle a wider variety of media title formats.
    """
    # Check for Large Animes or Tvdb Animes with season 0
    if season == 1:
        mal_mapping = database.get_mappings(mal_id, 'mal_id')
        if mal_mapping and 'thetvdb_season' in mal_mapping:
            thetvdb_season = mal_mapping['thetvdb_season']
            if thetvdb_season == 'a' or thetvdb_season == 0:
                season = None

    # Define regexes from the testing file
    regex_season = re.compile(r"(?i)\b(?:s(?:eason)?[ ._-]?(\d{1,2}))(?!\d)")
    regex_episode = re.compile(r"""(?ix)
        (?:^|[\s._-])                     # separator
        (?:e(?:p)?\s?(\d{1,4}))           # E12, EP12
        |
        -\s?(\d{1,4})\b                   # - 12
        |
        \b(?:episode|ep|e)\s?(\d{1,4})\b   # ep 03
        |
        s\d{1,2}e(\d{1,4})                # s01e07 format
        |
        (\d{1,4})\s+(\d{1,4})             # standalone episode range
    """)
    regex_episode_range = re.compile(r"(\d{1,4})\s*[~\-]\s*(\d{1,4})")
    regex_part = re.compile(r"(?i)\b(?:part|cour)[ ._-]?(\d+)(?:[&-](\d+))?\b")
    regex_trailing_number = re.compile(r"""(?ix)
        \b(?:[a-z]{3,})\s+(\d{1,3})\b
    """)
    regex_ordinal_check = re.compile(r"\b\d+(?:st|nd|rd|th)\b", re.IGNORECASE)

    filtered = []

    # Loop over each torrent in the list
    for torrent in torrent_list:
        # Set up the torrent hash as in the original function
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
        
        # Clean the title for extraction
        clean_title = clean_text(title)

        # Extract parts
        part_matches = regex_part.findall(title)
        extracted_parts = []
        for match in part_matches:
            for group in match:
                if group:
                    extracted_parts.append(group)
        
        # Extract seasons
        season_matches = regex_season.findall(title)
        extracted_seasons = None
        if season_matches:
            extracted_seasons = ", ".join(season_matches)

        # For episode extraction, remove part tokens from the clean title
        clean_title_no_parts = re.sub(regex_part, "", clean_title)

        # Extract episode using the improved logic from testing.py
        extracted_episode = None

        # First, if an sXXeYY pattern exists, extract the episode number directly
        se_match = re.search(r"s\d{1,2}e(\d{1,4})", clean_title_no_parts, re.IGNORECASE)
        if se_match:
            epnum = se_match.group(1)
            if not (extracted_parts and epnum in extracted_parts):
                extracted_episode = epnum

        # Otherwise, check for a dedicated episode range using "~" or "-"
        if not extracted_episode:
            range_match = regex_episode_range.search(clean_title_no_parts)
            if range_match:
                start, end = range_match.group(1), range_match.group(2)
                if not (extracted_parts and (start in extracted_parts or end in extracted_parts)):
                    extracted_episode = f"{start}-{end}"

        # Fallback: use the regex_episode findall approach
        if not extracted_episode:
            ep_match = regex_episode.findall(clean_title_no_parts)
            if ep_match:
                episodes = []
                for match in ep_match:
                    for group in match:
                        if group and group not in extracted_parts:
                            episodes.append(group)

                # If season is detected, drop a leading number equal to a season
                if extracted_seasons and episodes:
                    try:
                        season_nums = [int(s.strip()) for s in extracted_seasons.split(",") if s.strip().isdigit()]
                        if episodes[0].isdigit() and int(episodes[0]) in season_nums:
                            episodes = episodes[1:]
                    except Exception:
                        season_nums = []

                if len(episodes) >= 2 and episodes[0].isdigit() and episodes[-1].isdigit():
                    extracted_episode = f"{episodes[0]}-{episodes[-1]}"
                elif episodes:
                    extracted_episode = ", ".join(episodes)

        # Fallback: get final word-number match (unless it matches a part)
        if not extracted_episode:
            trail_matches = regex_trailing_number.findall(clean_title_no_parts)
            if trail_matches:
                last_num = trail_matches[-1]
                if not (extracted_parts and last_num in extracted_parts):
                    if extracted_seasons:
                        try:
                            season_nums = [int(s.strip()) for s in extracted_seasons.split(",") if s.strip().isdigit()]
                            if last_num.isdigit() and int(last_num) in season_nums:
                                extracted_episode = None
                            elif not regex_ordinal_check.search(clean_title_no_parts):
                                extracted_episode = last_num
                        except Exception:
                            season_nums = []
                    elif not regex_ordinal_check.search(clean_title_no_parts):
                        extracted_episode = last_num

        # Determine if we have any metadata to filter by
        has_info = bool(extracted_episode or extracted_seasons or extracted_parts)
        
        # For the inverted filter, torrents with no info are immediately added.
        if not has_info:
            filtered.append(torrent)
            continue

        valid = True

        # Check episode match if applicable
        if episode and extracted_episode:
            episode_nums = []
            # Handle episode ranges
            if "-" in extracted_episode:
                start, end = extracted_episode.split("-")
                try:
                    episode_nums = list(range(int(start), int(end) + 1))
                except (ValueError, TypeError):
                    valid = False
            # Handle single episode
            else:
                try:
                    episode_nums = [int(extracted_episode)]
                except (ValueError, TypeError):
                    valid = False

            if episode_nums:
                try:
                    req_ep = int(episode)
                    if req_ep not in episode_nums:
                        valid = False
                except (ValueError, TypeError):
                    valid = False

        # Check season match if applicable
        if season and extracted_seasons:
            season_nums = []
            for s in extracted_seasons.split(","):
                try:
                    season_nums.append(int(s.strip()))
                except (ValueError, TypeError):
                    pass
                    
            if season_nums:
                try:
                    req_season = int(season)
                    if req_season not in season_nums:
                        valid = False
                except (ValueError, TypeError):
                    valid = False

        # Check part match if applicable
        if part and extracted_parts:
            part_nums = []
            for p in extracted_parts:
                try:
                    part_nums.append(int(p))
                except (ValueError, TypeError):
                    pass
                    
            if part_nums:
                try:
                    req_part = int(part)
                    if req_part not in part_nums:
                        valid = False
                except (ValueError, TypeError):
                    valid = False

        if valid:
            filtered.append(torrent)

    return filtered


def remove_patterns(text):
    patterns = [
        r"\b(?:360p|480p|720p|1080p|2160p|4k)(?!\d)",
        r"\b10\s?bits?\b",  # matches 10bit, 10bits, 10 bit, 10 bits
        r"\b(?:h\.?\s?264|x\.?\s?264|h\.?\s?265|x\.?\s?265|hevc|avc|hls)(?!\d)",
        r"\b(?:web-dl|webrip|bluray|hdrip|dvdrip|hdtv|pdtv|cam|screener)\b",
        r"\b(?:hdr10|hdr|sdr|dv|dolby vision|dovi)\b",
        r"\b(?:mp4|vp9|av1|mpeg|xvid|divx|wmv|flac)\b",
        r"\b(?:aac|mp3|opus|ddp|dd(?:\s?(?:2|5|7))|ac3|dts(?:-hdma|-hdhr|-x)?|atmos|truehd)(?:\d+(?:\.\d+)?)?\b",
        r"\b(?:1\.0|2\.0|5\.1|7\.1|2ch|5ch|7ch|8ch)\b",
        r"\b(?:3d|60[-\s]?fps)\b",
        r"\b(?:multi audio|dual audio|dub(?:bed)?|multi sub|batch|complete series)\b"
    ]
    combined_pattern = "|".join(patterns)
    return re.sub(combined_pattern, "", text, flags=re.I)


def cleanup_text(text):
    # Remove content within brackets or parentheses
    text = re.sub(r"\[.*?\]|\(.*?\)", "", text).strip()
    # Replace special characters with a space
    text = re.sub(r"[:/,!?()'\"\\\[\]\-_.]", " ", text)
    # Collapse multiple spaces into one
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text):
    text = remove_patterns(text)
    text = cleanup_text(text)
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
