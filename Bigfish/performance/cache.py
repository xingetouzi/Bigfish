import pickle
import ujson as json

import pandas as pd

from Bigfish.data.cache import RedisCacheWithExpire
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
        for key, value in performance.__dict__.items():
            cache_key = ':'.join([self._cls.__name__, key])
            if isinstance(value, pd.DataFrame):
                context = self._translator.dumps(value)
            elif isinstance(value, pd.Series):
                context = self._translator.dumps(pd.DataFrame(value))
            else:
                context = value
            self.put(cache_key, json.dumps(context))

    def get_performance(self):
        fields = list(self._cls().__dict__.keys())
        return RedisObject(fields, self._cls.__name__, self, encode='json')
