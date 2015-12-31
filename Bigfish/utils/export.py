# -*- coding: utf-8 -*-

"""
Created on Wed Nov 25 21:09:47 2015

@author: BurdenBear
"""

from Bigfish.models.common import deque


class SeriesStorage:
    def __init__(self, series_id, maxlen, *args):
        self.__id = series_id
        self.series_args = {arg_name: deque([], maxlen) for arg_name in args}

    def append_all(self):
        for series in self.series_args.values():
            if series:
                series.appendleft(series[0])
            else:
                series.appendleft(0)

    def get_id(self):
        return self.__id


# TODO export只能支持写在策略主文件中，还是改用闭包的方案吧
def export(strategy, *args, maxlen=1000, series_id=None):
    """访问序列变量，将其放入当前的堆栈
    :param maxlen: 回溯的最大长度（即缓存的最大长度）
    :param series_id: 对应的SeriesStorage的id，根据源码所在位置唯一确定
    :param strategy:  对应的策略
    """
    if not args:
        return None
    if series_id not in strategy.series_storage:
        strategy.series_storage[series_id] = SeriesStorage(series_id, maxlen, *args)
    storage = strategy.series_storage[series_id]
    storage.append_all()
    return (storage.series_args[arg_name] for arg_name in args)
