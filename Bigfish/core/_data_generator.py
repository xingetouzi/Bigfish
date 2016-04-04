﻿# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:41:04 2015

@author: BurdenBear
"""
import logging
import pandas as pd
import time
from functools import partial, wraps
from Bigfish.utils.memory_profiler import profile
from Bigfish.config import MEMORY_DEBUG
from Bigfish.models.symbol import Forex
from Bigfish.utils.log import LoggerInterface
from Bigfish.event.event import EVENT_EXIT, EVENT_FINISH, Event

if MEMORY_DEBUG:
    import gc


class DataGenerator(LoggerInterface):
    """fetch data from somewhere and put dataEvent into eventEngine
        数据生成器
    Attr:
        __engine:the eventEngine where data event putted into
        __dataframe:data in pandas's dataframe format
    """

    def __init__(self, engine, logger=None, timer=None):
        super().__init__()
        self.__engine = engine
        self.__data_events = []
        self.__timer = timer
        self.__dataframe = None
        self.__get_data = None
        self.__is_alive = False
        self.__has_data = False
        self.__time_cost = 0
        if logger:
            self._logger = logger
        else:
            pass  # TODO 默认的日志行为

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

    @profile
    def __insert_data(self, symbol, time_frame):
        bars = self.__get_data(symbol, time_frame)
        if bars:
            dict_ = list(map(lambda x: x.to_dict(), bars))
            temp = pd.DataFrame(dict_, columns=bars[0].get_keys())
            if symbol.endswith('USD'):  # 间接报价
                temp['base_price'] = 1
            elif symbol.startswith('USD'):  # 直接报价
                temp['base_price'] = 1 / temp['close']
            else:  # TODO 处理交叉盘的情况
                base = symbol[-3:]
                if 'USD' + base in Forex.ALL.index:
                    extra = self.__insert_data('USD' + base, time_frame)
                    temp['base_price'] = 1 / extra['close']
                elif base + 'USD' in Forex.ALL.index:
                    extra = self.__insert_data(base + 'USD', time_frame)
                    temp['base_price'] = extra['close']
                else:
                    raise ValueError('找不到基准报价:%s' % base)
                temp['base_price'] = temp['base_price'].fillna(method='ffill')
            if self.__dataframe is None:
                self.__dataframe = temp
            else:
                self.__dataframe = pd.concat([self.__dataframe, temp], ignore_index=True, copy=False)
            self.__data_events.extend(map(lambda x: x.to_event(), bars))
            dict_.clear()
        bars.clear()

    @profile
    def __initialize(self):
        self.__time_cost = 0
        self.__get_data = partial(self._get_data, start_time=self.__engine.start_time, end_time=self.__engine.end_time)
        for symbol, time_frame in self.__engine.get_symbol_timeframe():
            self.__insert_data(symbol, time_frame)
        self.__data_events.sort(key=lambda x: x.content['data'].close_time)  # 按结束时间排序
        if self.__dataframe is not None:
            self.__dataframe.sort_values('close_time', kind='mergesort', inplace=True)  # 选择稳定的归并排序是为了让直盘数据排在前面

    @profile
    def start(self, **options):
        self.__is_alive = True
        if not self.__has_data:
            self.__initialize()
            self.__has_data = True
            self.log(self.__timer.time('拉取数据完毕，耗时:{0}'), logging.INFO)
        # 回放数据
        for data_event in self.__data_events:
            self.__engine.put_event(data_event)
            if not self.__is_alive:  # 判断用户是否取消
                self.__engine.put_event(Event(EVENT_EXIT))
                break
        self.__engine.put_event(Event(EVENT_FINISH))

    def stop(self):
        self._recycle()
        self.__is_alive = False

    @profile
    def _recycle(self):
        """
        释放内存资源
        """
        self.__data_events.clear()
        del self.__dataframe
        self.__dataframe = None
        self.__has_data = False


class AsyncDataGenerator:
    """fetch data from somewhere and put dataEvent into eventEngine
        数据生成器,分块异步读取数据
    Attr:
        __engine:the eventEngine where data event putted into
        __dataframe:data in pandas's dataframe format
    """

    def __init__(self, engine):
        self.__engine = engine
        self.__dataframe = None
        self.__get_data = None
        self.__is_alive = False
        self.__time_cost = 0

    def get_dataframe(self):
        return self.__dataframe

    @staticmethod
    def get_bars(self, data):
        return data

    def receive_data(self, data):
        bars = self.get_bars(data)
        if bars:
            if self.__dataframe is None:
                self.__dataframe = pd.DataFrame(self.__data_raw[0], columns=bars[0].get_keys())
            else:
                temp = pd.DataFrame(self.__data_raw[0], columns=bars[0].get_keys())
                self.__dataframe = pd.concat([self.__dataframe, temp], ignore_index=True, copy=False)
            # 回放数据
            for bar in bars:
                self.__engine.put_event(bar.to_event())
                if not self.__is_alive:  # 判断用户是否取消
                    break

    def subscribe_data(self, **options):
        """根据数据源的不同选择不同的实现"""
        raise NotImplementedError

    def start(self, **options):
        self.__is_alive = True
        self.subscribe_data(**options)

    def stop(self):
        self.__is_alive = False
        self._recycle()

    def _recycle(self):
        """
        释放内存资源
        """
        if self.__is_alive:
            self.__dataframe = None
