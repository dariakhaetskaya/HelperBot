import logging
from urllib.parse import urlparse, parse_qs, urljoin
from telegram import ParseMode, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, Update, CallbackQuery
from telegram.error import (TelegramError, Unauthorized, BadRequest, TimedOut, ChatMigrated, NetworkError)
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
from telegram.ext.dispatcher import run_async

from helperBot.DataBaseController import DataBaseController
from helperBot.Client import Client
from helperBot.Constants import action, message
from helperBot.Poller import Poller
from helperBot.Vk.VkAsyncAPIHandler import VkAsyncAPIHandler as Vk
from helperBot.Vk.VkChat import VkChat
from helperBot.Vk.VkUser import VkUser

logger = logging.getLogger(__name__)

class TelegramController:
    """
    Implementation of Telegram Controller aka Telegram Bot
    """

    def __init__(self, tg_bot_token, vk_client_id):
        """
        Init Bot
        """
        self.tg_bot_token = tg_bot_token
        self.poller = Poller()
        self.vk = Vk(vk_client_id)
        self.clients = Client.all_from_db()
        self.updater = Updater(token=tg_bot_token)
        dispatcher = self.updater.dispatcher

        start_command_handler = CommandHandler('start', self.start_command_callback)
        dispatcher.add_handler(start_command_handler)
        start_command_handler = CommandHandler('whoami', self.whoami_command_callback)
        dispatcher.add_handler(start_command_handler)
        start_command_handler = CommandHandler('pick', self.pick_command_callback)
        dispatcher.add_handler(start_command_handler)
        start_command_handler = CommandHandler('unpick', self.unpick_command_callback)
        dispatcher.add_handler(start_command_handler)
        start_command_handler = CommandHandler('details', self.details_command_callback)
        dispatcher.add_handler(start_command_handler)
        start_command_handler = CommandHandler('download', self.download_file_callback)
        dispatcher.add_handler(start_command_handler)
        start_command_handler = CommandHandler('user', self.user_chat)
        dispatcher.add_handler(start_command_handler)
        start_command_handler = CommandHandler('friends', self.friends_command_callback)
        dispatcher.add_handler(start_command_handler)
        unknown_handler = MessageHandler(Filters.command, self.unknown_command_callback)
        dispatcher.add_handler(unknown_handler)
        message_handler = MessageHandler(Filters.text, self.message_callback)
        dispatcher.add_handler(message_handler)
        dispatcher.add_error_handler(self.error_callback)
        dispatcher.add_handler(CallbackQueryHandler(self.button))

        self.restore()

    def button(self, update: Update, context: CallbackContext) -> None:
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query
        query.answer()

        client = self.clients[query.message.chat_id]
        client.seen_now()

        username = self.add_user(self.updater.bot, update, client, query.data)
        client.expect_message_to(username)

        self.updater.bot.send_message(chat_id=query.message.chat_id,
                    text=message.TYPE_MESSAGE(username),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=TelegramController.keyboard(client.keyboard_markup()))
        # self.updater.bot.send_message(query.message.chat_id, str(query.data))

    def start(self, use_webhook=False, app_url=None, app_port=None):
        """
        Start bot
        """
        db = DataBaseController()
        self.poller.async_run(self.on_update)

        if use_webhook:
            url_path = self.tg_bot_token.replace(":", "")
            self.updater.start_webhook(listen="0.0.0.0",
                                       port=app_port,
                                       url_path=url_path)
            self.updater.bot.set_webhook(urljoin(app_url, url_path))
        else:
            self.updater.start_polling()
        self.updater.idle()

        self.poller.stop()
        self.persist()
        db.close()

    def persist(self):
        for _, client in self.clients.items():
            client.persist()

    def restore(self):
        for _, client in self.clients.items():
            self.add_poll_server(client)

    def start_command_callback(self, update, context: CallbackContext):
        """
        Handler /start
        Bot will send a welcome message and wait for the Vk token
        """
        chat_id = update.message.chat_id
        auth_url = self.vk.get_auth_url()
        # Send first info messages
        self.updater.bot.sendMessage(chat_id=chat_id,
                        text=message.WELCOME(auth_url))
        self.updater.bot.sendMessage(chat_id=chat_id, text=message.COPY_TOKEN)
        # Create new client
        client = Client(next_action=action.ACCESS_TOKEN,
                        chat_id=chat_id)
        self.clients[chat_id] = client
        client.persist()

    def whoami_command_callback(self, update, context: CallbackContext):
        """
        Handler /whoami
        Bot will display information about Vk User
        """
        chat_id = update.message.chat_id
        if not chat_id in self.clients:
            return

        client = self.clients[chat_id]
        self.updater.bot.sendMessage(chat_id=chat_id,
                        text=message.WHOAMI(client.vk_user.get_name()),
                        reply_markup=TelegramController.keyboard(client.keyboard_markup()))

    def download_file_callback(self, update, context: CallbackContext):
        """
        Handler /download
        Bot will send a message and wait for the name of vk doc to download
        """
        chat_id = update.message.chat_id
        if not chat_id in self.clients:
            return

        self.updater.bot.sendMessage(chat_id=chat_id,
                        text=message.DOWNLOAD)
        client = self.clients[chat_id]
        client.next_action = action.DOWNLOAD
        self.clients[chat_id] = client
        client.persist()

    def user_chat(self, update, context: CallbackContext):
        chat_id = update.message.chat_id
        if not chat_id in self.clients:
            return
        client = self.clients[chat_id]
        recepient = update.message.text[6:]
        res = client.search(recepient)
        self.updater.bot.sendMessage(chat_id=chat_id,
                        text=res)
        self.clients[chat_id] = client
        client.persist()

    def build_menu(self, buttons, header_buttons=None, footer_buttons=None):
        n_cols = 2
        menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
        if header_buttons:
            menu.insert(0, header_buttons)
        if footer_buttons:
            menu.append(footer_buttons)
        return menu

    def friends_command_callback(self, update, context: CallbackContext):
        chat_id = update.message.chat_id
        if not chat_id in self.clients:
            self.start_command_callback(self.updater.bot, update)
            return

        client = self.clients[chat_id]
        client.seen_now()
        friend_list = client.load_friends()

        button_list = []
        for each in friend_list:
            button_list.append(
                InlineKeyboardButton(each['first_name'] + " " + each['last_name'], callback_data=each['id']))
        reply_markup = InlineKeyboardMarkup(self.build_menu(button_list))

        self.updater.bot.sendMessage(chat_id=chat_id,
                        text='Choose from the following',
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup)

    def pick_command_callback(self, update, context: CallbackContext):
        """
        Handler /pick [vk_user in database]
        Bot will open chat with Vk user, who send message before
        """
        chat_id = update.message.chat_id
        if not chat_id in self.clients:
            self.start_command_callback(self.updater.bot, update)
            return

        recepient = update.message.text[6:]
        client = self.clients[chat_id]
        client.seen_now()
        if client.expect_message_to(recepient) is None:
            res = client.search(recepient)
            print(res)
            username = self.add_user(self.updater.bot, update, client, res)
            client.expect_message_to(username)

        self.updater.bot.sendMessage(chat_id=chat_id,
                        text=message.TYPE_MESSAGE(recepient),
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=TelegramController.keyboard(client.keyboard_markup()))

    def unpick_command_callback(self, update, context: CallbackContext):
        """
        Handler /unpick
        Bot will close chat with picked Vk user
        """
        chat_id = update.message.chat_id
        if not chat_id in self.clients:
            self.start_command_callback(self.updater.bot, update)
            return

        client = self.clients[chat_id]
        client.next_action = action.NOTHING
        client.persist()
        self.updater.bot.sendMessage(chat_id=chat_id,
                        text=message.UNPICK(client.next_recepient.get_name()),
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=TelegramController.keyboard(client.keyboard_markup()))
        client.next_recepient = None

    def details_command_callback(self, update, context: CallbackContext):
        """
        Handler /details
        Bot display information about picked Vk user(photo and name)
        """
        chat_id = update.message.chat_id
        if not chat_id in self.clients:
            self.start_command_callback(self.updater.bot, update)
            return

        client = self.clients[chat_id]
        client.seen_now()
        user = client.next_recepient
        if user == None:
            self.updater.bot.sendMessage(chat_id=chat_id,
                            text=message.FIRST_PICK_USER,
                            reply_markup=TelegramController.keyboard(client.keyboard_markup()))
            return

        if user.photo != None:
            self.updater.bot.sendPhoto(chat_id=chat_id, photo=user.photo)

        self.updater.bot.sendMessage(chat_id=chat_id,
                        text=message.USER_NAME(user.get_name()),
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=TelegramController.keyboard(client.keyboard_markup()))

        participants = user.participants()
        if participants != None:
            self.updater.bot.sendMessage(chat_id=chat_id,
                            text=message.PARTICIPANTS(participants),
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=TelegramController.keyboard(client.keyboard_markup()))

    def unknown_command_callback(self, update, context: CallbackContext):
        """
        Handler /<unknown_command>
        Bot will send a message about the unknown command
        """
        self.updater.bot.sendMessage(chat_id=update.message.chat_id,
                        text=message.UNKNOWN)

    def error_callback(self, bot, update, error):
        """
        Handler for errors
        """
        try:
            raise error
        except Unauthorized:
            # remove update.message.chat_id from conversation list
            logger.debug('Update {} caused error {}'.format(update, error))
        except BadRequest:
            # handle malformed requests - read more below!
            logger.debug('Update {} caused error {}'.format(update, error))
        except TimedOut:
            # handle slow connection problems
            logger.debug('Update {} caused error {}'.format(update, error))
        except NetworkError:
            # handle other connection problems
            logger.debug('Update {} caused error {}'.format(update, error))
        except ChatMigrated as e:
            # the chat_id of a group has changed, use e.new_chat_id instead
            logger.debug('Update {} caused error {}'.format(update, error))
        except TelegramError:
            # handle all other telegram related errors
            logger.debug('Update {} caused error {}'.format(update, error))

    def message_callback(self, update, context: CallbackContext):
        """
        Handler for user's messages to bot
        There are some cases of messages:
        - Message, which contains Access token
        - Message, which contains name of doc to be downloaded
        - Message to Vk user(chat with picked User)
        - Other messages
        """
        chat_id = update.message.chat_id

        if not chat_id in self.clients:
            return self.start_command_callback(self.updater.bot, update)

        client = self.clients[chat_id]
        client.seen_now()

        if client.next_action == action.ACCESS_TOKEN:
            return self.on_token_message(self.updater.bot, update, client)
        elif client.next_action == action.DOWNLOAD:
            return self.on_download(self.updater.bot, update, client)
        elif client.next_action == action.MESSAGE:
            return self.on_typed_message(self.updater.bot, update, client)

        self.echo(update.message.chat_id)

    def on_download(self, bot, update, client):
        """
        Method for receiving name of vk doc from user and bot will send request to get and download it
        """
        message = update.message.text
        files = client.get_files(message)
        if files == "there's no such document in your files":
            bot.sendMessage(chat_id=update.message.chat_id,
                            text=files,
                            reply_markup=TelegramController.keyboard(client.keyboard_markup()))
        else:
            bot.sendDocument(chat_id=client.chat_id,
                             document=files,
                             reply_markup=TelegramController.keyboard(client.keyboard_markup()))
        client.next_action = action.NOTHING

    def on_token_message(self, bot, update, client):
        """
        Method for receiving vk token from user and bot will parse, send request to get access
        and display name of Vk User
        """
        parseresult = urlparse(update.message.text)
        if parseresult.scheme == 'https':
            parseparams = parse_qs(parseresult.fragment)
            access_token = parseparams.get('access_token')[0]
            client.load_vk_user(access_token)
        else:
            client.load_vk_user(update.message.text)
        name = client.vk_user.get_name()
        client.next_action = action.NOTHING
        self.add_poll_server(client)
        bot.sendMessage(chat_id=update.message.chat_id,
                        text=message.TOKEN_SAVED(name),
                        reply_markup=TelegramController.keyboard(client.keyboard_markup()))

    def on_typed_message(self, bot, update, client):
        """
        Method for sending message to picked vk user
        """
        client.send_message(update.message.text)

    @run_async
    def add_poll_server(self, client):
        if client.vk_token != None:
            self.poller.add(client)

    def echo(self, chat_id):
        """
        Method for sending message to Tg User on message
        """
        self.updater.bot.sendMessage(chat_id=chat_id, text=message.ECHO)

    @staticmethod
    def keyboard(keyboard_markup):
        """
        Create keyboard
        :param - keyboard markup
        :return - keyboard
        """
        return ReplyKeyboardMarkup(
            keyboard_markup,
            selective=True,
            resize_keyboard=True)

    def on_update(self, updates, client):
        """
        Checking for updates(messages from vk)
        """
        for update in updates:
            self.process_update(update, client)

    def process_update(self, update, client):
        """
        Processing update and check for messages from vk user
        """
        if len(update) == 0:
            return

        if update[0] == 4:
            # When new message received
            self.receive_vk_message(update, client)

    def add_user(self, bot, update, client, id):
        from_id = id

        from_name = ''

        user = VkUser.fetch_user(client.vk_token, from_id)
        from_name = user.get_name()
        client.add_interaction_with(user)

        self.updater.bot.sendMessage(chat_id=client.chat_id,
                                     text=from_name)
        client.persist()
        return from_name

    def receive_vk_message(self, update, client):
        """
        Receiving messages from vk user/chat and sending to telegram User
        """
        flags = update[2]
        from_id = update[3]
        text = update[6]
        attachments = update[7]

        if flags & 2 == 2:
            # Skip when message is outgoing
            return

        from_name = ''

        if from_id & 2000000000 == 2000000000:
            # Message came from chat
            chat_id = from_id - 2000000000
            chat = VkChat.fetch(client.vk_token, chat_id, )
            from_name = chat.name_from(attachments['from'])
            client.add_interaction_with(chat)
        else:
            user = VkUser.fetch_user(client.vk_token, from_id)
            from_name = user.get_name()
            client.add_interaction_with(user)

        self.updater.bot.sendMessage(chat_id=client.chat_id,
                                     text=message.NEW_MESSAGE(from_name, text),
                                     reply_markup=TelegramController.keyboard(client.keyboard_markup()),
                                     parse_mode=ParseMode.MARKDOWN)
        client.persist()

