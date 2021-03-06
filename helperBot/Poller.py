from queue import Queue
from threading import Thread

from telegram.ext.dispatcher import run_async

from helperBot.Vk.VkAsyncAPIHandler import VkAsyncAPIHandler as Vk


class Poller:
    """
    Poller class (long polls vk api for new message events)
    """
    def __init__(self):
        self.is_running = False
        self.clients = Queue()
        self.cb = Poller.noop

    def async_run(self, cb):
        self.is_running = True
        self.cb = cb
        poll_thread = Thread(target=self._run,
                             name='poll')

        poll_thread.start()

    def _run(self):
        print('In _run')
        while self.is_running:
            if not self.clients.empty():
                client = self.clients.get()
                updates = Vk.poll(client)
                if updates == None:
                    print("Updates are none")
                    continue

                client.persist()
                self.add(client)
                self.exec_cb(updates=updates, client=client)

        print('Exit _run')

    def stop(self):
        self.is_running = False

    @run_async
    def exec_cb(self, updates, client):
        self.cb(updates=updates, client=client)

    @staticmethod
    def noop():
        pass

    def add(self, client):
        if client.next_server == None:
            next_server = Vk.get_long_poll_server(token=client.vk_token,
                                                  chat_id=client.chat_id)
            if next_server == None:
                return

            client.next_server = next_server

        self.clients.put(client)