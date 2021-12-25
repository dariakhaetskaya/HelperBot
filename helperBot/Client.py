import re
import time

import jsonpickle

from helperBot.Constants import action
from helperBot.Vk.VkUser import VkUser
from helperBot.DataBaseController import DataBaseController
"""
Bot client
"""


class Client:
    """
    Implementation of Bot Client
    """
    def __init__(self,
                 last_seen=time.time(),
                 next_action=action.NOTHING,
                 chat_id=None):

        self.last_seen = last_seen
        self.next_action = next_action
        self.chat_id = chat_id
        self.vk_user = VkUser()
        self.vk_token = None
        self.next_server = None
        self.interacted_with = set()  # set of chats or users
        self.next_recepient = None


    def db_key(self):
        """
        Method for getting Client Chat id = db_key for searching in database
        """
        return 'Client-' + str(self.chat_id)

    def persist(self):
        """
        Upload user stuff(Client class) to database
        """
        db = DataBaseController()
        self.seen_now()
        db.set(self.db_key(), self.to_json())
        db.sync()

    def seen_now(self):
        """
        Time when user was online
        """
        self.last_seen = time.time()

    def load_vk_user(self, vk_token):
        """
        Loading info about vk user
        """
        self.vk_token = vk_token
        if self.vk_user.should_fetch():
            user = VkUser.fetch_current_user(vk_token)
            if user != None:
                self.vk_user = user

    def keyboard_markup(self):
        """
        Init keyboard markup if user not picked:
        - [/friends]
        - [/pick <user> if user exists in db]
        - [/download]
        else:
        - [/unpick <user>]
        - [/details]
        """
        if self.next_action == action.MESSAGE:
            return self.picked_keyboard()
        return [['/friends']] + [['/download']]
               # + [['/pick ' + user.get_name()]
               #  for user in self.interacted_with
               #  if not user.should_fetch()]

    def picked_keyboard(self):
        return [['/unpick ' + self.next_recepient.get_name()],
                ['/details']]

    def expect_message_to(self, to_name):
        """
        Check if picked vk user(friend) was interacted with user
        """
        self.next_recepient = next((u for u in self.interacted_with
                                    if u.get_name() == to_name), None)
        if self.next_recepient != None:
            self.next_action = action.MESSAGE
        self.persist()
        return self.next_recepient

    def search(self, name):
        return self.vk_user.search_chat(self.vk_token, name)

    def load_friends(self):
        return self.vk_user.load_friends(self.vk_token)

    def send_message(self, text):
        """
        Send message to picked user
        """
        if self.next_recepient == None:
            return

        self.next_recepient.send_message(self.vk_token, text)

    def get_files(self, query_message):
        """
        Send request for getting doc/gif/image/etc
        """
        return self.vk_user.get_files(self.vk_token, query_message)

    def add_interaction_with(self, user):
        """
        Add interacted vk user with user
        """
        if user.empty():
            return

        self.interacted_with.add(user)

    def to_json(self):
        return jsonpickle.encode(self)

    @staticmethod
    def from_json(json_str):
        return jsonpickle.decode(json_str)

    @staticmethod
    def all_from_db():
        """
        Loading all information from database, when restarting app
        """
        db = DataBaseController()
        clients = dict()
        for client_key in db.dict():
            if not re.match('Client-.+', client_key):
                continue

            client_json = db.get(client_key)
            client = Client.from_json(client_json)
            if client.vk_user.should_fetch():
                client.load_vk_user(client.vk_token)

            clients[client.chat_id] = client

        print('Restored clients from db: ' + str(clients))
        return clients


