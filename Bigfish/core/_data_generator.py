# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:41:04 2015

@author: BurdenBear
"""
from Bigfish.utils.common import _TIME_FRAME_PERIOD, quick_sort
from functools import partial

class DataGenerator:
    """fetch data from somewhere and put dataEvent into eventEngine
        数据生成器
    Attrs:
        __engine:the eventEngine where dataEvent putted into        
        __symols:symbol of assets
        __start_time:start time of data
        __end_time:end tiem of data
        __time_frame_bits:bits contain information of which time frame to use
    """
    
    def __init__(self, engine):
        self.__engine = engine
        self.__data_events = []
        self.__get_datas = None
    @staticmethod    
    def _close_time(arr, index):
        bar = arr[index].content['data']
        return(bar.time+_TIME_FRAME_PERIOD[bar.time_frame])
    #TODO 多态
    def _get_datas(self, symbol, time_frame, start_time=None, end_time=None):
        """根据数据源的不同选择不同的实现"""
        raise(NotImplementedError)
        
    def __insert_datas(self, symbol, time_frame):
        self.__data_events.extend(self.__get_datas(symbol, time_frame))
        
    def start(self):
        self.__get_datas = partial(self._get_datas,start_time=self.__engine.start_time,end_time=self.__engine.end_time)
        for symbol, time_frame in self.__engine.symbols.keys():
            self.__insert_datas(symbol, time_frame)
        quick_sort(0,len(self.__data_events)-1,self.__data_events,self._close_time)
        #回放数据
        for data_event in self.__data_events:
            self.__engine.put_event(data_event)
            
        
    
    