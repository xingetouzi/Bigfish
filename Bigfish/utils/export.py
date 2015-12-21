# -*- coding: utf-8 -*-

"""
Created on Wed Nov 25 21:09:47 2015

@author: BurdenBear
"""

import sys
import functools

from Bigfish.utils.common import deque


class SeriesStorage():
    def __init__(self, series_id, maxlen, *args):
        self.__id = self.series_id
        self.series_args = {arg_name: deque([], maxlen) for arg_name in args}

    def append_all(self):
        for series in self.series_args.values():
            series.appendleft(series[0])

    def get_id(self):
        return self.__id


def export(strategy, *args, maxlen=1000, series_id=None):
    """访问序列变量，将其放入当前的堆栈"""
    if series_id not in strategy.series_storage:
        strategy.series_storage[series_id] = SeriesStorage(series_id, maxlen, *args)
        storage = strategy.series_storage[series_id]
    storage.append_all()
    frame = sys._getframe()
    caller = frame.f_back
    caller.f_locals.update(storage.series_args)

class ExportWrapper():
    """为了支持特殊语法对export函数进行封装"""

    def __init__(self, strategy):
        global export
        self.__export = functools.partial(export, strategy)

    def __call__(self, *args, maxlen=1000, series_id=None):
        self.__export(*args, maxlen=maxlen, series_id=series_id)

    def __getitem__(self, maxlen):
        return functools.patial(self.__export, partial=maxlen  )
