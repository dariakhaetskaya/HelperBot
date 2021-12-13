import string
from collections import namedtuple

import requests

LongPollServer = namedtuple('LongPollServer', 'server key ts chat_id')


class VkAsyncAPIHandler:
    def __init__(self, client_id):
        self._client_id = client_id

    @staticmethod
    def AUTH_URL(params):
        return string.Template(
            'https://oauth.vk.com/authorize'
            '?client_id=$client_id'
            '&display=page'
            '&scope=messages,offline'
            '&response_type=token'
            '&v=5.44').substitute(params)

    @staticmethod
    def API_URL(method):
        return 'https://api.vk.com/method/' + method + '/?v=5.131'

    @staticmethod
    def api(method, token, params=dict()):
        """
        Send request to vk by api url with token and params
        """
        params = params.copy()
        params['access_token'] = token
        print(f"Request:{VkAsyncAPIHandler.API_URL(method)}")
        print(f"Params:{params}")

        r = requests.get(VkAsyncAPIHandler.API_URL(method), params=params)
        print(VkAsyncAPIHandler.API_URL(method))
        print(params)
        if r.status_code != requests.codes.ok:
            return None

        json = r.json()
        print('VK api response: ' + str(json))

        if 'response' in json:
            return json['response']

        return None

    def get_auth_url(self):
        """
        Getting usrl for auth user(/start)
        """
        params = {'client_id': self._client_id}
        return VkAsyncAPIHandler.AUTH_URL(params)

    @staticmethod
    def get_long_poll_server(token, chat_id):
        """
        https://vk.com/dev/messages.getLongPollServer
        """
        method = 'messages.getLongPollServer'
        server = VkAsyncAPIHandler.api(method, token)
        if server == None:
            return None

        return LongPollServer(server['server'], server['key'],
                              server['ts'], chat_id)

    @staticmethod
    def poll(client, retry=True):
        server, key, ts, chat_id = client.next_server
        url = 'http://' + server
        params = {'key': key, 'ts': ts, 'wait': 25, 'act': 'a_check', 'mode': 2}
        r = requests.get(url, params=params)
        if r.status_code != requests.codes.ok:
            next_server = VkAsyncAPIHandler.get_long_poll_server(token=client.vk_token,
                                                  chat_id=client.chat_id)
            if next_server == None:
                return None

            client.next_server = next_server
            if retry:
                return VkAsyncAPIHandler.poll(client, retry=False)
            else:
                return None

        json = r.json()
        print("Poll results: " + str(json))
        if 'failed' in json:
            next_server = VkAsyncAPIHandler.get_long_poll_server(token=client.vk_token,
                                                  chat_id=client.chat_id)
            if next_server == None:
                return None

            client.next_server = next_server
            if retry:
                return VkAsyncAPIHandler.poll(client, retry=False)
            else:
                return None

        next_server = LongPollServer(server, key, json['ts'], chat_id)
        client.next_server = next_server
        return json['updates']
