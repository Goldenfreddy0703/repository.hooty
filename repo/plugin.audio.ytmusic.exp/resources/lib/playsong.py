import api
import utils
import xbmc
from storage import storage


class PlaySong:

    def __init__(self):
        self.api = api.Api()

    def play(self, params):
        videoId = params.pop('videoId')

        params = self.__getSongStreamUrl(videoId, params)
        url = params.pop('url')
        title = params.get('title')
        params['artist'] = [params['artist']]
        utils.log("Song: %s - %r " % (title, url))

        mime = utils.paramsToDict(url).get('mime', 'audio/mpeg')

        li = utils.createItem(title, params.pop('albumart')) #, params.pop('artistart'))
        li.setProperty('mimetype', mime)
        li.setContentLookup(False)
        li.setInfo(type=mime.split('/')[0], infoLabels=params)
        li.setPath(url)

        utils.setResolvedUrl(li)

        self.__prefetchUrl()
        song1 = self.api.getApi().get_song(videoId)
        li.setArt({'fanart': song1['videoDetails']['thumbnail']['thumbnails'][-1]['url']})
 

    def __getSongStreamUrl(self, videoId, params):
        # try to fetch from memory first
        params['url'] = utils.get_mem_cache(videoId)

        # if no metadata
        if 'title' not in params:
            song = storage.getSong(videoId)
            if not song:
                # fetch from web
                song = self.api.getTrack(videoId)
            params['title'] = song['title']
            params['artist'] = song['artist']
            params['albumart'] = song['albumart']
            params['artistart'] = song['artistart']
            params['album'] = song['album']

        # check if not expired before returning
        if params['url']:
            import time
            # utils.log("TIME "+str(utils.paramsToDict(params['url']))+ " "+str(time.time()))
            if int(utils.paramsToDict(params['url']).get('expire', 0)) < time.time():
                params['url'] = ''

        if not params['url']:
            # try to fetch from web
            params['url'] = self.api.getSongStreamUrl(videoId)

        return params

    def __prefetchUrl(self):
        import json
        jsonGetPlaylistPos = '{"jsonrpc":"2.0", "method":"Player.GetProperties", "params":{"playerid":0,"properties":["playlistid","position","percentage"]},"id":1}'
        jsonGetPlaylistItems = '{"jsonrpc":"2.0", "method":"Playlist.GetItems",    "params":{"playlistid":0,"properties":["file","duration"]}, "id":1}'

        # get song position in playlist
        playerProperties = json.loads(xbmc.executeJSONRPC(jsonGetPlaylistPos))
        while 'result' not in playerProperties or playerProperties['result']['percentage'] < 5:
            # wait for song playing and playlist ready
            xbmc.sleep(1000)
            playerProperties = json.loads(xbmc.executeJSONRPC(jsonGetPlaylistPos))

        position = playerProperties['result']['position']
        utils.log("position:" + str(position) + " percentage:" + str(playerProperties['result']['percentage']))

        # get next song id and fetch url
        playlistItems = json.loads(xbmc.executeJSONRPC(jsonGetPlaylistItems))
        # utils.log("playlistItems:: "+repr(playlistItems))

        if 'items' not in playlistItems['result']:
            utils.log("empty playlist")
            return

        if position + 1 >= len(playlistItems['result']['items']):
            utils.log("playlist end:: position " + repr(position) + " size " + repr(len(playlistItems['result']['items'])))
            return

        videoId_next = utils.paramsToDict(
            playlistItems['result']['items'][position + 1]['file']).get("videoId")

        stream_url = self.api.getSongStreamUrl(videoId_next)
        utils.set_mem_cache(videoId_next, stream_url)

