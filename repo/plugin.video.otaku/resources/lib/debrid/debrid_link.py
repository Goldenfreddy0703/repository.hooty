import json
import time

from resources.lib.ui import client, control, source_utils


class DebridLink:
    def __init__(self):
        self.ClientID = 'sdpBuYFQo6L53s3B4apluw'
        self.USER_AGENT = 'Otaku/{0}'.format(control.ADDON_VERSION)
        self.token = control.getSetting('dl.auth')
        self.refresh = control.getSetting('dl.refresh')
        self.headers = {'User-Agent': self.USER_AGENT,
                        'Authorization': 'Bearer {0}'.format(
                            self.token)}
        self.api_url = "https://debrid-link.fr/api/v2"
        self.cache_check_results = {}

    def auth_loop(self):
        if control.progressDialog.iscanceled():
            control.progressDialog.close()
            return
        time.sleep(self.OauthTimeStep)
        url = '{0}/oauth/token'.format(self.api_url[:-3])
        data = {'client_id': self.ClientID,
                'code': self.DeviceCode,
                'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'}
        response = json.loads(client.request(url, post=data, headers={'User-Agent': self.USER_AGENT}, error=True))
        if 'error' in response:
            return False
        else:
            try:
                control.progressDialog.close()
                self.token = response.get('access_token')
                self.refresh = response.get('refresh_token')
                control.setSetting('dl.auth', self.token)
                control.setSetting('dl.refresh', self.refresh)
                control.setSetting('dl.expiry', str(time.time() + int(response['expires_in'])))
                self.headers.update({'Authorization': 'Bearer {0}'.format(self.token)})
            except:
                control.ok_dialog(control.ADDON_NAME, control.lang(30105))
            return True

    def auth(self):
        url = '{0}/oauth/device/code'.format(self.api_url[:-3])
        data = {'client_id': self.ClientID,
                'scope': 'get.post.delete.seedbox get.account'}
        response = json.loads(client.request(url, post=data, headers={'User-Agent': self.USER_AGENT}))
        self.OauthTimeout = response.get('expires_in')
        self.OauthTimeStep = response.get('interval')
        self.DeviceCode = response.get('device_code')

        control.copy2clip(response.get('user_code'))
        control.progressDialog.create('Debrid-Link Auth')
        control.progressDialog.update(
            -1,
            control.lang(30100).format(control.colorString(response.get('verification_url'))) + '[CR]'
            + control.lang(30101).format(control.colorString(response.get('user_code'))) + '[CR]'
            + control.lang(30102)
        )
        auth_done = False
        while not auth_done:
            auth_done = self.auth_loop()

        premium = self.get_info()
        if not premium:
            control.ok_dialog(control.ADDON_NAME, control.lang(30104))

    def get_info(self):
        url = '{0}/account/infos'.format(self.api_url[:-3])
        response = client.request(url, headers=self.headers)
        response = json.loads(response)
        username = response.get('value').get('pseudo')
        control.setSetting('dl.username', username)
        control.ok_dialog(control.ADDON_NAME, 'Debrid-Link ' + control.lang(30103))
        return response.get('value').get('premiumLeft') > 3600

    def refreshToken(self):
        postData = {'grant_type': 'refresh_token',
                    'refresh_token': self.refresh,
                    'client_id': self.ClientID}
        url = '{0}/oauth/token'.format(self.api_url[:-3])
        response = client.request(url, post=postData, headers={'User-Agent': self.USER_AGENT}, error=True)
        response = json.loads(response)
        if 'access_token' in response:
            self.token = response.get('access_token')
            control.setSetting('dl.auth', self.token)
            control.setSetting('dl.expiry', str(time.time() + response.get('expires_in')))

    def addMagnet(self, magnet):
        postData = {'url': magnet,
                    'async': 'true'}
        url = '{0}/seedbox/add'.format(self.api_url)
        resp = client.request(url, post=postData, headers=self.headers)
        js_result = json.loads(resp).get('value')
        if js_result:
            torrent_id = js_result.get('id')
            if js_result.get('downloadPercent') < 100:
                self.delete_transfer(torrent_id)
                return
            return js_result
        return

    def delete_transfer(self, transfer_id):
        url = '{0}/seedbox/{1}/remove'.format(self.api_url, transfer_id)
        _ = client.request(url, headers=self.headers, method='DELETE')

    def resolve_single_magnet(self, hash_, magnet, episode='', pack_select=False):
        selected_file = None
        res = self.addMagnet(magnet)
        if not res:
            return
        files = res.get('files')
        folder_details = [{'link': x['downloadUrl'], 'path': x['name']} for x in files]
        if episode:
            selected_file = source_utils.get_best_match('path', folder_details, episode, pack_select)
            if selected_file is not None:
                return selected_file['link']

        sources = [(item.get('size'), item.get('downloadUrl'))
                   for item in files
                   if any(item.get('name').lower().endswith(x) for x in ['avi', 'mp4', 'mkv'])]

        selected_file = max(sources)[1]
        if selected_file is None:
            return

        return selected_file
