# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:41:04 2015

@author: BurdenBear
"""

from Bigfish.core import DataGenerator, StrategyEngine, Strategy
from Bigfish.event.event import EVENT_BAR_SYMBOL, Event
from Bigfish.utils.quote import Bar
from Bigfish.utils.common import get_datetime
from functools import partial 
import tushare as ts

class DataGeneratorTushare(DataGenerator):
    @staticmethod    
    def __data_to_event(symbol, time_frame, data):
        bar = Bar(symbol)
        bar.time_frame = time_frame
        for field in ['open','high','low','close','volume']:
            setattr(bar,field,data[field])
        bar.time = get_datetime(data.name).timestamp()
        event = Event(EVENT_BAR_SYMBOL[symbol][time_frame],{'data':bar})
        return(event)
        
    def _get_data(self, symbol, time_frame, start_time=None, end_time=None):
        if time_frame == 'D1':
            data = ts.get_hist_data(symbol,start_time,end_time)
            return(data.apply(partial(self.__data_to_event,symbol,time_frame),axis=1).tolist())
        else:
            raise(ValueError)
            
class Backtesting:
    def __init__(self, id_, name, code):
        self.strategy_engine = StrategyEngine(backtesting=True)        
        self.strategy = Strategy(self.strategy_engine, id_, name, code)
        self.strategy_engine.add_strategy(self.strategy)
        self.data_generator = DataGeneratorTushare(self.strategy_engine)
        self.strategy_engine.initialize()
    
    def start(self):
        self.strategy_engine.start()
        self.data_generator.start()
        self.strategy_engine.wait()
        
    def get_profit_records(self):
         return(self.strategy_engine.get_profit_records())
        
    def stop(self):
        self.strategy_engine.stop()