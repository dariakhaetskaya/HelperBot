"""
VK User
"""
import time

import jsonpickle

from helperBot.DataBaseController import DataBaseController
from helperBot.Vk.VkAsyncAPIHandler import VkAsyncAPIHandler as Vk

"""
VK User
"""


class VkUser():
    def __init__(self,
                 id=None,
                 type='',
                 invited_by=0,
                 first_name='Unresolved',
                 last_name='Name',
                 deactivated=None,
                 can_access_closed=None,
                 is_closed=None,
                 photo_400_orig=None,
                 created_at=time.time()):

        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.can_access_closed = can_access_closed
        self.is_closed = is_closed
        self.photo = photo_400_orig
        self.created_at = created_at

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def db_key(self):
        return VkUser.DB_KEY(self.id)

    @staticmethod
    def DB_KEY(id):
        return 'VK-USER-' + str(id)

    def empty(self):
        return self.id == None

    def participants(self):
        return None

    def should_fetch(self):
        return self.id == None or self.outdated()

    def get_name(self):
        return self.first_name + ' ' + self.last_name

    def persist(self):
        db = DataBaseController()
        db.set(self.db_key(), self.to_json())
        db.sync()

    def send_message(self, token, message):
        """
        Creating url for sending message to user
        """
        params = {'user_id': self.id, 'random_id': 0, 'message': message}
        message_id = Vk.api('messages.send', token, params)

    def search_chat(self, token, name):
        params = {'q': name, 'count': 10, 'extanded': 1, 'fields': ""}
        message_id = Vk.api('messages.searchConversations', token, params)
        return message_id["items"][0]["peer"]["id"]

    def load_friends(self, token):
        params = {'user_id': self.id, 'order': 'hints', 'fields': "first_name, last_name"}
        friends_list = Vk.api('friends.get', token, params)
        return friends_list["items"]

    def list_files(self, token):
        params = {'owner_id': self.id}
        files_list = Vk.api('docs.get', token, params)
        return files_list["items"]

    def get_file_by_id(self, token, file_id):
        params = {'docs': str(self.id) + "_" + str(file_id)}
        response = Vk.api('docs.getById', token, params)
        return response[0]["title"], response[0]["url"]

    def get_files(self, token, query):
        """
        Create url for requesting files
        """
        params = {'q': query, 'search_own': 1, 'count': 1, 'offset': 0}
        message_id = Vk.api('docs.search', token, params)
        if message_id.get('count') == 0:
            return "there's no such document in your files"

        return message_id["items"][0]["url"]

    def outdated(self):
        one_week = 60 * 24 * 7
        return self.created_at < time.time() - one_week

    def to_json(self):
        return jsonpickle.encode(self)

    @staticmethod
    def from_json(json_str):
        return jsonpickle.decode(json_str)

    @staticmethod
    def from_api(token, params):
        users = Vk.api('users.get', token, params)
        if users == None:
            return VkUser()

        if len(users) == 0:
            return VkUser()

        user = VkUser(**users[0])
        user.persist()
        return user

    @staticmethod
    def fetch_current_user(token):
        params = {'fields': 'photo_400_orig'}
        return VkUser.from_api(token, params)

    @staticmethod
    def fetch_user(token, user_id):
        db = DataBaseController()
        key = VkUser.DB_KEY(user_id)
        if key in db.dict():
            print(key)
            print(db.get(key))
            user = VkUser.from_json(db.get(key))
            if not user.outdated():
                return user

        params = {'user_ids': user_id, 'fields': 'photo_400_orig'}
        return VkUser.from_api(token, params)
