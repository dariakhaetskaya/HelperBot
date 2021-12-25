# Actions

def constant(f):
    def fset(self, value):
        raise TypeError

    def fget(self):
        return f()

    return property(fget, fset)


class _Action():
    @constant
    def NOTHING():
        return 'NOTHING'

    @constant
    def ACCESS_TOKEN():
        return 'ACCESS_TOKEN'

    @constant
    def DOWNLOAD():
        return 'DOWNLOAD'

    @constant
    def RECEPIENT():
        return 'RECEPIENT'

    @constant
    def MESSAGE():
        return 'MESSAGE'


action = _Action()


class _Message():
    @staticmethod
    def WELCOME(link):
        return ('Please authorize!'
                'First, generate access token by '
                'following the link: ' + link)

    @constant
    def DOWNLOAD():
        return "Write me name of your file and I'll download it for you"

    @constant
    def COPY_TOKEN():
        return 'Now send generated access token from the URL or just send full URL from address bar.'

    @staticmethod
    def TOKEN_SAVED(name):
        return ('Hey, ' + name + '! Your token was saved! '
                                 'Now you will start receiving messages.')

    @constant
    def ECHO():
        return "Sorry, I didn't get it"

    @constant
    def UNKNOWN():
        return ('I have no clue about the command you specified. '
                'Where did you find it?')

    @staticmethod
    def NEW_MESSAGE(sender, text):
        return '*' + sender + ':* ' + text

    @staticmethod
    def WHOAMI(name):
        return 'You are ' + name

    @staticmethod
    def TYPE_MESSAGE(name):
        return 'Type message to *' + name + '* (or /details):'

    @staticmethod
    def USER_NAME(name):
        return '*Name:* ' + name

    @staticmethod
    def UNPICK(name):
        return 'You left conversation with *' + name + '*'

    @constant
    def FIRST_PICK_USER():
        return 'Pick someone first'

    @staticmethod
    def PARTICIPANTS(participants):
        return '*In chat:* ' + participants


message = _Message()
