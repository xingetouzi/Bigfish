from Bigfish.data.cache import RedisCache
from Bigfish.performance.performance import StrategyPerformance
import pickle


class RedisObject:
    def __init__(self, fields, prefix, cache):
        self._fields = fields
        self._prefix = prefix
        self._cache = cache

    def __getattr__(self, item):
        if item in self._fields:
            return pickle.loads(self._cache.get(':'.join([self._prefix, item]), decode=False))
        else:
            raise AttributeError


class ComplexObjectRedisCache(RedisCache):
    _cls = object

    def __init__(self, user):
        super(ComplexObjectRedisCache, self).__init__(user)

    def put_object(self, obj):
        for key, value in obj.__dict__.items():
            cache_key = ':'.join([self._cls.__name__, key])
            self.put(cache_key, pickle.dumps(value))

    def get_object(self):
        fields = list(self._cls().__dict__.keys())
        return RedisObject(fields, self._cls.__name__, self)


class StrategyPerformanceCache(ComplexObjectRedisCache):
    _cls = StrategyPerformance
