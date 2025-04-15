import time
import json

from resources.lib.ui import client, control, source_utils, database


class RealDebrid:
    def __init__(self):
        self.ClientID = control.getSetting('realdebrid.client_id')
        if self.ClientID == '':
            api_info = database.get_info('Real-Debrid')
            self.ClientID = api_info['client_id']
        self.ClientSecret = control.getSetting('realdebrid.secret')
        self.token = control.getSetting('realdebrid.token')
        self.refresh = control.getSetting('realdebrid.refresh')
        self.autodelete = control.getBool('realdebrid.autodelete')
        self.DeviceCode = ''
        self.OauthTimeout = 0
        self.OauthTimeStep = 0
        self.OauthTotalTimeout = 0
        self.OauthUrl = 'https://api.real-debrid.com/oauth/v2'
        self.BaseUrl = "https://api.real-debrid.com/rest/1.0"

    def headers(self):
        return {'Authorization': f"Bearer {self.token}"}

    def auth_loop(self):
        if control.progressDialog.iscanceled():
            self.OauthTimeout = 0
            return False
        control.progressDialog.update(int(self.OauthTimeout / self.OauthTotalTimeout * 100))
        params = {
            'client_id': self.ClientID,
            'code': self.DeviceCode
        }
        r = client.request(f'{self.OauthUrl}/device/credentials', params=params, output='json')
        if r:
            response = json.loads(r)
            control.setSetting('realdebrid.client_id', response['client_id'])
            control.setSetting('realdebrid.secret', response['client_secret'])
            self.ClientSecret = response['client_secret']
            self.ClientID = response['client_id']
        return r is not None

    def auth(self):
        api_info = database.get_info('Real-Debrid')
        self.ClientID = api_info['client_id']
        self.ClientSecret = ''
        params = {
            'client_id': self.ClientID,
            'new_credentials': 'yes'
        }
        response = client.request(f'{self.OauthUrl}/device/code', params=params)
        resp = json.loads(response)
        copied = control.copy2clip(resp['user_code'])
        display_dialog = (f"{control.lang(30021).format(control.colorstr('https://real-debrid.com/device'))}[CR]"
                          f"{control.lang(30022).format(control.colorstr(resp['user_code']))}")
        if copied:
            display_dialog = f"{display_dialog}[CR]{control.lang(30023)}"
        control.progressDialog.create(f'{control.ADDON_NAME}: Real-Debrid Auth', display_dialog)
        control.progressDialog.update(100)
        self.OauthTotalTimeout = self.OauthTimeout = int(resp['expires_in'])
        self.OauthTimeStep = int(resp['interval'])
        self.DeviceCode = resp['device_code']
        auth_done = False
        while not auth_done and self.OauthTimeout > 0:
            self.OauthTimeout -= self.OauthTimeStep
            control.sleep(self.OauthTimeStep * 1000)
            auth_done = self.auth_loop()
        control.progressDialog.close()
        if auth_done:
            self.token_request()
            self.status()

    def token_request(self):
        if self.ClientSecret == '':
            return

        postData = {
            'client_id': self.ClientID,
            'client_secret': self.ClientSecret,
            'code': self.DeviceCode,
            'grant_type': 'http://oauth.net/grant_type/device/1.0'
        }

        response = client.request(f'{self.OauthUrl}/token', post=postData)
        response = json.loads(response)

        control.setSetting('realdebrid.token', response['access_token'])
        control.setSetting('realdebrid.refresh', response['refresh_token'])
        control.setInt('realdebrid.expiry', int(time.time()) + int(response['expires_in']))
        self.token = response['access_token']
        self.refresh = response['refresh_token']

    def status(self):
        response = client.request(f'{self.BaseUrl}/user', headers=self.headers())
        user_info = json.loads(response)
        control.setSetting('realdebrid.username', user_info['username'])
        control.setSetting('realdebrid.auth.status', user_info['type'].capitalize())
        control.ok_dialog(control.ADDON_NAME, f'Real-Debrid {control.lang(30024)}')
        control.setSetting('show.uncached', 'true')
        control.setSetting('uncached.autoruninforground', 'false')
        control.setSetting('uncached.autoruninbackground', 'false')
        control.setSetting('uncached.autoskipuncached', 'true')
        if user_info['type'] != 'premium':
            control.ok_dialog(f'{control.ADDON_NAME}: Real-Debrid', control.lang(30025))

    def refreshToken(self):
        postData = {
            'grant_type': 'http://oauth.net/grant_type/device/1.0',
            'code': self.refresh,
            'client_secret': self.ClientSecret,
            'client_id': self.ClientID
        }
        response = client.request(f"{self.OauthUrl}/token", post=postData, output='json')
        if response:
            response = json.loads(response)
            self.token = response['access_token']
            self.refresh = response['refresh_token']
            control.setSetting('realdebrid.token', self.token)
            control.setSetting('realdebrid.refresh', self.refresh)
            control.setInt('realdebrid.expiry', int(time.time()) + int(response['expires_in']))

            user_info_response = client.request(f'{self.BaseUrl}/user', headers=self.headers())
            user_info = json.loads(user_info_response)
            control.setSetting('realdebrid.username', user_info['username'])
            control.setSetting('realdebrid.auth.status', user_info['type'])
            control.log('refreshed realdebrid.token')
        else:
            control.log(f"realdebrid.refresh: {repr(response)}", 'warning')

    def addMagnet(self, magnet):
        postData = {'magnet': magnet}
        response = client.request(f'{self.BaseUrl}/torrents/addMagnet', headers=self.headers(), post=postData)
        response = json.loads(response)
        return response

    def list_torrents(self):
        response = client.request(f'{self.BaseUrl}/torrents', headers=self.headers())
        response = json.loads(response)
        return response

    def torrentInfo(self, torrent_id):
        response = client.request(f'{self.BaseUrl}/torrents/info/{torrent_id}', headers=self.headers())
        response = json.loads(response)
        return response

    def torrentSelect(self, torrentid, fileid='all'):
        postData = {'files': fileid}
        response = client.request(f'{self.BaseUrl}/torrents/selectFiles/{torrentid}', headers=self.headers(), post=postData)
        return response is not None

    def resolve_hoster(self, link):
        postData = {'link': link}
        response = client.request(f'{self.BaseUrl}/unrestrict/link', headers=self.headers(), post=postData)
        response = json.loads(response)
        return response['download']

    def deleteTorrent(self, torrent_id):
        response = client.request(f'{self.BaseUrl}/torrents/delete/{torrent_id}', headers=self.headers(), method='DELETE', timeout=10)
        return response is not None

    @staticmethod
    def resolve_cloud(source, pack_select):
        if source['torrent_files']:
            best_match = source_utils.get_best_match('path', source['torrent_files'], source['episode'], pack_select)
            if not best_match or not best_match['path']:
                return
            for f_index, torrent_file in enumerate(source['torrent_files']):
                if torrent_file['path'] == best_match['path']:
                    return source['torrent_info']['links'][f_index]

    def resolve_single_magnet(self, hash_, magnet, episode='', pack_select=False):
        hashCheck = client.request(f'{self.BaseUrl}/torrents/instantAvailability/{hash_}', headers=self.__headers())
        hashCheck = json.loads(hashCheck)
        stream_link = None
        for _ in hashCheck[hash_]['rd']:
            torrent = self.addMagnet(magnet)
            self.torrentSelect(torrent['id'])
            files = self.torrentInfo(torrent['id'])

            selected_files = [(idx, i) for idx, i in enumerate([i for i in files['files'] if i['selected'] == 1])]
            if pack_select:
                best_match = source_utils.get_best_match('path', [i[1] for i in selected_files], episode, pack_select)
                if best_match:
                    try:
                        file_index = [i[0] for i in selected_files if i[1]['path'] == best_match['path']][0]
                        link = files['links'][file_index]
                        stream_link = self.resolve_hoster(link)
                    except IndexError:
                        pass
            elif len(selected_files) == 1:
                stream_link = self.resolve_hoster(files['links'][0])
            elif len(selected_files) > 1:
                best_match = source_utils.get_best_match('path', [i[1] for i in selected_files], episode)
                if best_match:
                    try:
                        file_index = [i[0] for i in selected_files if i[1]['path'] == best_match['path']][0]
                        link = files['links'][file_index]
                        stream_link = self.resolve_hoster(link)
                    except IndexError:
                        pass
            self.deleteTorrent(torrent['id'])
            return stream_link

    def get_torrent_status(self, magnet):
        """
        Given a magnet link, get torrent data needed for further resolution.
        Returns a tuple: (torrent_id, status, torrent_info)
        If the torrent cannot be selected, returns (None, None, None).
        """
        magnet_data = self.addMagnet(magnet)
        if not self.torrentSelect(magnet_data['id']):
            self.deleteTorrent(magnet_data['id'])
            control.ok_dialog(control.ADDON_NAME, "BAD LINK")
            return None, None, None
        torrent_id = magnet_data['id']
        torrent_info = self.torrentInfo(torrent_id)
        status = torrent_info.get('status', 'error')
        return torrent_id, status, torrent_info

    def resolve_uncached_source(self, source, runinbackground, runinforground, pack_select):
        heading = f'{control.ADDON_NAME}: Cache Resolver'
        if runinforground:
            control.progressDialog.create(heading, "Caching Progress")
        stream_link = None
        magnet = source['magnet']
        magnet_data = self.addMagnet(magnet)

        if not self.torrentSelect(magnet_data['id']):
            self.deleteTorrent(magnet_data['id'])
            control.ok_dialog(control.ADDON_NAME, "BAD LINK")
            if runinbackground:
                return

        torrent_id = magnet_data['id']
        torrent_info = self.torrentInfo(torrent_id)
        status = torrent_info['status']

        if runinbackground:
            control.notify(heading, "The source is downloading to your cloud")
            return

        progress = 0
        while status not in ['downloaded', 'error']:
            if runinforground and (control.progressDialog.iscanceled() or control.wait_for_abort(5)):
                break
            torrent_info = self.torrentInfo(torrent_id)
            status = torrent_info.get('status', 'error')
            progress = torrent_info.get('progress', 0)
            seeders = torrent_info.get('seeders', 0)
            speed = torrent_info.get('speed', 0)
            if runinforground:
                f_body = (f"Status: {status}[CR]"
                          f"Progress: {round(progress, 2)} %[CR]"
                          f"Seeders: {seeders}[CR]"
                          f"Speed: {source_utils.get_size(speed)}")
                control.progressDialog.update(int(progress), f_body)

        if status == 'downloaded':
            if progress == 100:
                control.ok_dialog(heading, "This file has been added to your Cloud")
            torrent_files = [selected for selected in torrent_info['files'] if selected['selected'] == 1]
            if len(torrent_info['files']) == 1:
                best_match = torrent_files[0]
            else:
                best_match = source_utils.get_best_match('path', torrent_files, source['episode_re'], pack_select)
            if not best_match or not best_match['path']:
                return
            for f_index, torrent_file in enumerate(torrent_files):
                if torrent_file['path'] == best_match['path']:
                    hash_ = torrent_info['links'][f_index]
                    stream_link = self.resolve_hoster(hash_)
            if self.autodelete:
                self.deleteTorrent(torrent_id)
        else:
            self.deleteTorrent(torrent_id)
        if runinforground:
            control.progressDialog.close()
        return stream_link
