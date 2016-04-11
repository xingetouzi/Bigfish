import pickle
import json

from Bigfish.data.cache import RedisCache
from Bigfish.performance.performance import StrategyPerformance
from Bigfish.utils.ligerUI_util import DataframeTranslator


class RedisObject:
    def __init__(self, fields, prefix, cache, encode='pickle'):
        self._fields = fields
        self._prefix = prefix
        self._cache = cache
        self._encode = encode

    def __getattr__(self, item):
        if item in self._fields:
            if self._encode == 'pickle':
                return pickle.loads(self._cache.get(':'.join([self._prefix, item]), decode=False))
            elif self._encode == 'json':
                return json.loads(self._cache.get(':'.join([self._prefix, item]), decode=True))
        else:
            raise AttributeError


class RedisCacheWithExpire(RedisCache):
    _time_expire = None

    def put(self, key, value):
        super().put(key, value)
        if self._time_expire is not None:
            cache_key = self.get_cache_key(key)
            self.redis.expire(cache_key, self._time_expire)


class ComplexObjectRedisCache(RedisCacheWithExpire):
    _cls = object
    _time_expire = 15 * 60

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


class StrategyPerformanceJsonCache(RedisCacheWithExpire):
    _cls = StrategyPerformance
    _time_expire = 15 * 60

    def __init__(self, user):
        super().__init__(user)
        self._translator = DataframeTranslator(
            {'height': 'auto', 'width': '98%', 'pageSize': 20, 'where': 'f_getWhere()'})

    def put_performance(self, performance):
        for key in performance.__dict__.items():
            cache_key = ':'.join([self._cls.__name__, key])
            if key in ['info_on_home_page', 'yield_curve']:
                context = getattr(performance, key)
            else:
                context = self._translator.dumps(getattr(performance, key))
            self.put(cache_key, json.dumps(context))

    def get_performance(self):
        fields = list(self._cls().__dict__.keys())
        return RedisObject(fields, self._cls.__name__, self, encode='json')
