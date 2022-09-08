from ytmusicapi import YTMusic
from typing import List, Dict
from ytmusicapi.helpers import *
from ytmusicapi.parsers.library import *
from ytmusicapi.parsers.uploads import *


class MyYtMus(YTMusic):
    def get_library_upload_songs_incremental(self, order: str = None) -> List[Dict]:
        """
        Returns a list of uploaded songs

        :param order: Order of songs to return. Allowed values: 'a_to_z', 'z_to_a', 'recently_added'. Default: Default order.
        :return: List of uploaded songs.

        """
        self._check_auth()
        endpoint = 'browse'
        body = {"browseId": "FEmusic_library_privately_owned_tracks"}
        validate_order_parameter(order)
        if order is not None:
            body["params"] = prepare_order_params(order)
        response = self._send_request(endpoint, body)
        results = find_object_by_key(nav(response, SINGLE_COLUMN_TAB + SECTION_LIST),
                                     'itemSectionRenderer')
        results = nav(results, ITEM_SECTION)
        if 'musicShelfRenderer' not in results:
            return []
        else:
            results = results['musicShelfRenderer']

        songs = []

        songs.extend(parse_uploaded_items(results['contents'][1:]))
        yield songs

        def request_func(additionalParams): return self._send_request(
            endpoint, body, additionalParams)
        while 'continuations' in results:
            additionalParams = get_continuation_params(results, "")
            response = request_func(additionalParams)
            if 'continuationContents' in response:
                results = response['continuationContents']['musicShelfContinuation']
            else:
                break
            contents = get_continuation_contents(results, parse_uploaded_items)
            if contents:
                yield contents

    def get_library_songs_incremental(self,
                                      order: str = None) -> List[Dict]:
        """
        Gets the songs in the user's library (liked videos are not included).
        To get liked songs and videos, use :py:func:`get_liked_songs`

        :param validate_responses: Flag indicating if responses from YTM should be validated and retried in case
            when some songs are missing. Default: False
        :param order: Order of songs to return. Allowed values: 'a_to_z', 'z_to_a', 'recently_added'. Default: Default order.
        :return: List of songs. Same format as :py:func:`get_playlist`
        """
        self._check_auth()
        body = {'browseId': 'FEmusic_liked_videos'}
        validate_order_parameter(order)
        if order is not None:
            body["params"] = prepare_order_params(order)
        endpoint = 'browse'

        def request_func(additionalParams): return self._send_request(
            endpoint, body)

        def parse_func(raw_response): return parse_library_songs(raw_response)

        response = parse_func(request_func(None))

        results = response['results']
        songs = response['parsed']
        yield songs

        def request_continuations_func(additionalParams): return self._send_request(
            endpoint, body, additionalParams)

        def parse_continuations_func(
            contents): return parse_playlist_items(contents)

        while 'continuations' in results:
            additionalParams = get_continuation_params(results, "")
            response = request_continuations_func(additionalParams)
            if 'continuationContents' in response:
                results = response['continuationContents']['musicShelfContinuation']
            else:
                break
            contents = get_continuation_contents(
                results, parse_continuations_func)
            if contents:
                yield contents
