import logging
import os
import sys
from logging.handlers import SysLogHandler
from dotenv import load_dotenv

from helperBot.TelegramController import TelegramController
from helperBot.DataBaseController import DataBaseController

console_handler = logging.StreamHandler()
handlers = [console_handler]

SYSLOG_ADDRESS = os.getenv('SYSLOG_ADDRESS', '')
if SYSLOG_ADDRESS:
    syslog_hostname, syslog_udp_port = SYSLOG_ADDRESS.split(":")
    syslog_udp_port = int(syslog_udp_port)
    syslog_handler = SysLogHandler(address=(syslog_hostname, syslog_udp_port))
    handlers.append(syslog_handler)

logging.basicConfig(format='%(asctime)s {} %(name)s: %(message)s'.format(os.getenv("HOSTNAME", "unknown_host")),
                    datefmt='%b %d %H:%M:%S',
                    level=logging.DEBUG, handlers=handlers)

logger = logging.getLogger(__name__)


def main():
    """
    Create .env file in /helperBot directory with the following structure:
    BOT_TOKEN=*********************
    VK_CLIENT_ID=**********
    """
    load_dotenv()
    tg_bot_token = os.getenv('BOT_TOKEN')
    vk_client_id = os.getenv('VK_CLIENT_ID')
    use_webhook = bool(int(os.getenv('USE_WEBHOOK', '0')))
    app_port = int(os.getenv('PORT', '5000'))
    app_url = os.getenv('APP_URL', '')

    args = sys.argv[1:]
    db = DataBaseController()
    if len(args) > 0:
        if '--reset-db' in args:
            print('Resetting database')
            db.clear()
            db.sync()

    bot = TelegramController(tg_bot_token, vk_client_id)
    bot.start(use_webhook, app_url, app_port)


if __name__ == '__main__':
    main()