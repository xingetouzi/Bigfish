import redis


def singleton(cls, *args, **kw):
    instances = {}

    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]

    return _singleton


@singleton
class RedisPool:
    def __init__(self):
        # self.host = '1490r19q77.51mypc.cn'  # 花生壳免费域名
        self.host = '139.129.19.54'
        self.port = 6379
        self.db = 0
        self.password = 'Xinger520'
        self.__pool = None

    @property
    def pool(self):
        if not self.__pool:
            self.__pool = redis.ConnectionPool(host=self.host, port=self.port, db=self.db, password=self.password)
        return self.__pool


class RedisCache:
    """Redis Cache

    Supports the following objects and types by default:

    +-------------------+---------------+
    | Python            | Cache         |
    +===================+===============+
    | dict              | dict          |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str               | string        |
    +-------------------+---------------+
    | int, float        | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-------------------+---------------+
    | object(__dict__)  | dict          |
    +-------------------+---------------+
    也可以访问这个对象的成员变量 redis 获得Redis对象直接操作缓存

    """

    def __init__(self, user):
        self.pool = RedisPool()
        self.redis = redis.Redis(connection_pool=self.pool.pool)
        # assert isinstance(user, User)
        self.user = user

    def put(self, key, value):
        """
        支持所有对象的缓存.注意 对于自定义的对象,会把对象的__dict__来缓存
        对于list或者tuple, 请直接调用put_list()方法
        Parameters
        ----------
        key: 键(必须为字符串)
        value: 要缓存的对象
        -------
        """
        self.__check_key(key)
        cache_key = self.get_cache_key(key)
        if isinstance(value, dict):
            self.redis.hmset(cache_key, value)
        elif value is True:
            self.redis.set(cache_key, value)
        elif value is False:
            self.redis.set(cache_key, value)
        elif isinstance(value, (int, float, str, bytes)):
            self.redis.set(cache_key, value)
        elif isinstance(value, (list, tuple)):
            self.put_list(cache_key, value)
        elif value is None:
            # None 啥也不干
            pass
        else:
            self.redis.hmset(cache_key, value.__dict__)

    def put_list(self, key, values):
        """
        如果list中每一个元素是复杂对象(自定义(__dict__), dict),请保持对象结构一致,不然会抛出错误
        注意: 复杂对象如dict会把dict中的每一个key当做一个list,取的时候也要注意
        Parameters
        ----------
        key: key
        value: list对象
        -------
        """
        self.__check_key(key)
        cache_key = self.get_cache_key(key)
        if len(values) > 0:
            if isinstance(values[0], (int, float, str)):
                self.redis.rpush(cache_key, values)
            elif isinstance(values[0], dict):
                for dk in values[0].keys():
                    self.redis.rpush("%s:%s" % (cache_key, dk), [dv[dk] for dv in values])
            else:
                for dk in values[0].keys():
                    self.redis.rpush("%s:%s" % (cache_key, dk), [dv[dk] for dv in values])

    def get(self, key, decode=True):
        result = self.redis.get(self.get_cache_key(key))
        if decode:
            return result.decode("utf8")
        else:
            return result

    def remove(self, key):
        self.redis.delete(self.get_cache_key(key))

    # =============字典相关方法============== #
    def hset(self, cache_key, prop_key, value):
        return self.redis.hset(self.get_cache_key(cache_key), prop_key, value)

    def hget(self, cache_key, prop_key):
        return self.redis.hget(self.get_cache_key(cache_key), prop_key).decode("utf8")

    def hkeys(self, key):
        keys = self.redis.hkeys(self.get_cache_key(key))
        return [key.decode("utf8") for key in keys]

    def hgetall(self, cache_key, decode=True):
        result = self.redis.hgetall(self.get_cache_key(cache_key))
        if decode:
            return {k.decode('utf-8'):v.decode('utf-8') for k,v in result.items()}
        else:
            return result

    # =============列表相关方法============= #
    # 注意:以下dict_key是缓存dict对象列表时的dict的key #
    # 简单对象可以不传 dict_key #
    def lindex(self, key, index, dict_key=None):
        return self.redis.lindex(self.get_cache_key(key, dict_key), index).decode("utf8")

    def lpop(self, key, dict_key=None):
        return self.redis.lpop(self.get_cache_key(key, dict_key)).decode("utf8")

    def lpush(self, key, dict_key=None):
        return self.redis.lpush(self.get_cache_key(key, dict_key))

    def rpop(self, key, dict_key=None):
        return self.redis.rpop(self.get_cache_key(key, dict_key)).decode("utf8")

    def rpush(self, key, dict_key=None):
        return self.redis.rpush(self.get_cache_key(key, dict_key))

    def llen(self, key, dict_key=None):
        return self.redis.llen(self.get_cache_key(key, dict_key)).decode("utf8")

    def lrange(self, key, dict_key=None, start=0, end=0):
        if end == 0:
            end = self.llen(key, dict_key)
        cache_key = self.get_cache_key(key, dict_key)
        values = self.redis.lrange(cache_key, start, end)
        return [value.decode("utf8") for value in values]

    def remove_keys(self, key, *dict_keys):
        for dict_key in dict_keys:
            self.redis.delete(self.get_cache_key(key, dict_key))

    def get_cache_key(self, key, dict_key=None):
        if dict_key:
            return "%s:%s:%s" % (self.user, key, dict_key)
        else:
            return "%s:%s" % (self.user, key)

    def __check_key(self, key):
        if not isinstance(key, str):
            raise AssertionError("The key only support str object!")


if __name__ == '__main__':
    from Bigfish.models.model import User

    r = RedisCache(User("10086"))
    d = {"a": "123", "b": "456"}
    r.put('test', d)
    print(r.redis.hgetall("test"))
    # r.put_list("abc", [{"a":"123", "b":"456"}, {"a":"789", "b":"678"}])
    r.remove_keys("abc", "a", "b")
