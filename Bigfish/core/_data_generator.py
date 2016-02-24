# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:41:04 2015

@author: BurdenBear
"""
import pandas as pd
import time
from functools import partial, wraps


class DataGenerator:
    """fetch data from somewhere and put dataEvent into eventEngine
        数据生成器
    Attr:
        __engine:the eventEngine where data event putted into
        __dataframe:data in pandas's dataframe format
    """

    def __init__(self, engine):
        self.__engine = engine
        self.__data_events = []
        self.__dataframe = None
        self.__get_data = None
        self.__is_alive = False
        self.__has_data = False
        self.__time_cost = 0

    # TODO 多态
    def _get_data(self, symbol, time_frame, start_time=None, end_time=None):
        """根据数据源的不同选择不同的实现"""
        raise NotImplementedError

    def get_dataframe(self):
        return self.__dataframe

    def with_time_cost_count(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            st = time.time()
            result = func(*args, **kwargs)
            self.__time_cost += time.time() - st
            return result

        return wrapper

    def __insert_data(self, symbol, time_frame):
        bars = self.__get_data(symbol, time_frame)
        if bars:
            if self.__dataframe is None:
                self.__dataframe = pd.DataFrame(list(map(lambda x: x.to_dict(), bars)), columns=bars[0].get_fields())
            else:
                temp = pd.DataFrame(list(map(lambda x: x.to_dict(), bars)), columns=bars[0].get_fields())
                self.__dataframe = pd.concat([self.__dataframe, temp], ignore_index=True, copy=False)
            self.__data_events.extend(map(lambda x: x.to_event(), bars))

    def __initialize(self):
        self.__time_cost = 0
        self.__get_data = partial(self._get_data, start_time=self.__engine.start_time, end_time=self.__engine.end_time)
        for symbol, time_frame in self.__engine.get_symbol_timeframe():
            self.__insert_data(symbol, time_frame)
        self.__data_events.sort(key=lambda x: x.content['data'].close_time)  # 按结束时间排序
        self.__dataframe.sort_values('close_time', inplace=True)

    def start(self):
        self.__is_alive = True
        if not self.__has_data:
            self.__initialize()
            self.__has_data = True
            print('拉取数据完毕，耗时<%s>s' % self.__time_cost)
        # 回放数据
        for data_event in self.__data_events:
            self.__engine.put_event(data_event)
            if not self.__is_alive:  # 判断用户是否取消
                break

    def stop(self):
        self._recycle()
        self.__is_alive = False

    def _recycle(self):
        """
        释放内存资源
        """
        self.__data_events.clear()
        self.__dataframe = None
        self.__has_data = False
