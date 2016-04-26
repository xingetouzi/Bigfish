from pymongo import MongoClient


def singleton(cls, *args, **kw):
    instances = {}

    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]

    return _singleton


@singleton
class MongoPool:
    def __init__(self):
        self.host = '115.159.209.231'
        self.port = 27017
        self.password = 'Xinger520'
        self.__client = None

    @property
    def client(self):
        if not self.__client:
            self.__client = MongoClient(host=self.host, port=self.port)
        return self.__client


class MongoUser:
    def __init__(self, user):
        self.user = user
        self._client = MongoPool().client
        self._db = self.client.get_database('user')
        self._collection = self.db[self.user]

    @property
    def client(self):
        return self._client

    @property
    def db(self):
        return self._db

    @property
    def collection(self):
        return self._collection


if __name__ == '__main__':
    a = MongoUser('adsf')
    a.collection.insert({'a': 1})
    print(a.collection.find())
    for result in a.collection.find():
        print(result)
    print(a.collection.delete_one({'a': 1}))
