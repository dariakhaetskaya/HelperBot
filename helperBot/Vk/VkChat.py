import time

import jsonpickle

from helperBot.Vk.VkAsyncAPIHandler import VkAsyncAPIHandler as Vk
from helperBot.Vk.VkUser import VkUser
from helperBot.DataBaseController import DataBaseController

class VkChat():
    def __init__(self,
                 chat_id=None,
                 title='',
                 type='',
                 admin_id=None,
                 users=[],
                 created_at=time.time(),
                 **kwargs):
        self.id = chat_id
        self.title = title
        self.admin_id = admin_id
        self.photo = None
        self.created_at = created_at
        self.users = [VkUser(**u) for u in users]
        for u in self.users:
            u.persist()


    def __hash__(self):
        return abs(hash('chat-' + str(self.id))) % (10 ** 8)

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    @staticmethod
    def DB_KEY(chat_id):
        return 'VK-CHAT-' + str(chat_id)

    def empty(self):
        return self.id == None

    def get_name(self):
        if len(self.title) > 0:
            return self.title

        return 'Chat #' + self.id

    def name_from(self, uid_str):
        uid = int(float(uid_str))
        return next((u.get_name() + ' in '
                     for u in self.users
                     if u.id == uid), '') + self.get_name()

    def participants(self):
        return ', '.join([u.get_name() for u in self.users])

    def db_key(self):
        return VkChat.DB_KEY(self.id)

    def persist(self):
        db = DataBaseController()
        db.set(self.db_key(), self.to_json())
        db.sync()

    def outdated(self):
        one_week = 60 * 24 * 7
        return self.created_at < time.time() - one_week

    def should_fetch(self):
        return self.empty() or self.outdated()

    def to_json(self):
        return jsonpickle.encode(self)

    def send_message(self, token, message):
        params = { 'chat_id': self.id, 'message': message}
        message_id = Vk.api('messages.send', token, params)

    @staticmethod
    def from_json(json_str):
        return jsonpickle.decode(json_str)

    @staticmethod
    def from_api(token, params):
        chat = Vk.api('messages.getChat', token, params)
        if chat == None:
            return VkChat()

        vk_chat = VkChat(**chat)
        vk_chat.persist()
        return vk_chat

    @staticmethod
    def fetch(token, chat_id):
        db = DataBaseController()
        key = VkChat.DB_KEY(chat_id)
        if key in db.dict():
            chat = VkChat.from_json(db.get(key))
            if not chat.outdated():
                return chat

        params = {'chat_id': chat_id,
                  'fields': 'first_name, last_name, photo_400_orig'}
        return VkChat.from_api(token, params)
