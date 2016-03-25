# -*- coding: utf-8 -*-

"""
Created on Wed Nov 25 21:09:47 2015

@author: BurdenBear
"""

from Bigfish.models.common import Deque as deque
from functools import wraps, partial
from weakref import WeakKeyDictionary


class SeriesStorage:
    def __init__(self, series_id, maxlen, *args):
        self.__id = series_id
        self.__bar_now = 0
        self.series_args = {arg_name: deque([], maxlen) for arg_name in args}

    def append_all(self, barnum):
        if barnum == self.__bar_now:
            return
        self.__bar_now = barnum
        for series in self.series_args.values():
            if series:
                series.appendleft(series[0])
            else:
                series.appendleft(0)

    def get_id(self):
        return self.__id


# TODO export只能支持写在策略主文件中，还是改用闭包的方案吧
def export(*args, barnum=None, maxlen=1000, series_id=None, export_id=None, strategy=None):
    """访问序列变量，将其放入当前的堆栈
    :param barnum: 运行时传入
    :param export_id: 对应的export语句的ID，根据源码所在位置在编译时唯一确定
    :param maxlen: 回溯的最大长度（即缓存的最大长度）
    :param series_id: 对应的SeriesFunction的ID，运行时唯一确定
    :param strategy:  对应的策略
    """
    if not args:
        return None
    key = '%s.%s' % (series_id, export_id)
    if key not in strategy.series_storage:
        strategy.series_storage[key] = SeriesStorage(key, maxlen, *args)
    storage = strategy.series_storage[key]
    storage.append_all(barnum)
    return (storage.series_args[arg_name] for arg_name in args)


class SeriesFunction:
    def __init__(self, generator=None, handle=None):
        self.__handle = handle
        self.__generator = generator
        self.__cache = {}
        self.__map = {}
        self.__count = 0

    def __call__(self, *args, **kwargs):
        # TODO 根据generator的签名信息确定唯一的key，现在kwargs中参数顺序不同也会对应两个key，然而只能是一个
        key = self.get_key(args, kwargs)
        # XXX 目前假定键值一一对应，不可能会有异值同键的情况
        if key not in self.__cache:
            self.__count += 1
            self.__map[key] = self.__count
            self.__cache[key] = self.__generator(*args, series_id='%s.%s' % (self.__handle, self.__count), **kwargs)
        return self.__cache[key].__next__()

    def start(self):
        self.__cache.clear()
        self.__map.clear()

    def stop(self):
        for item in self.__cache.values():
            item.close()

    @staticmethod
    def get_key(args, kwargs):
        return args, tuple(kwargs.keys()), tuple(kwargs.values())

    @staticmethod
    def new(function=None, handle=None):
        return SeriesFunction(function, handle)
