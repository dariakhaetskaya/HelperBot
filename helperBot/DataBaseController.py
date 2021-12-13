import shelve


# Pattern Singleton
class MetaSingleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(MetaSingleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class DataBaseController(metaclass=MetaSingleton):
    db = None

    def __init__(self):
        self.db = shelve.open('database.db', writeback=True)

    def set(self, key, value):
        try:
            self.db[key] = value

        except ValueError:
            pass

    def get(self, key):
        try:
            return self.db[key]

        except ValueError:
            return None

    def dict(self):
        return self.db

    def sync(self):
        try:
            self.db.sync()

        except ValueError:
            pass

    def close(self):
        self.db.sync()
        self.db.close()

    def addVKSubscriber(self, subscriber_id, profile_id):
        """

        :param subscriber_id: TgUID
        :param profile_id: VKUID
        :return: void
        """

    def get_subscriber(self, profile_id):
        """

        :param profile_id: VKID
        :return: List<TgUID>
        """
