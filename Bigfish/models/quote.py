# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 10:06:21 2015

@author: BurdenBear
"""
from Bigfish.event.event import EVENT_SYMBOL_BAR_RAW, Event, EVENT_SYMBOL_TICK_RAW
from Bigfish.models.common import DictLike
from Bigfish.utils.common import tf2s
from datetime import datetime
import pandas as pd


class BarFactory:
    @classmethod
    def to_dict(cls, bar):
        temp = super(Bar, bar).to_dict()
        temp['datetime'] = bar.datetime
        temp['close_time'] = bar.close_time
        return temp

    @classmethod
    def to_event(cls, bar):
        event = Event(EVENT_SYMBOL_BAR_RAW[bar.symbol][bar.time_frame], data=bar)
        return event

    @classmethod
    def get_keys(cls):
        """
        :return: field names in print order use for create dataframe
        """
        return Bar.get_keys()


class Bar(DictLike):
    """K线数据对象（开高低收成交量时间）"""
    __slots__ = ["symbol", "open", "high", "low", "close", "volume", "timestamp", "time_frame"]
    __keys__ = __slots__ + ['datetime', "close_time"]
    datetime = property(lambda self: datetime.fromtimestamp(self.timestamp))
    close_time = property(lambda self: self.timestamp + tf2s(self.time_frame))

    def __init__(self, symbol):
        self.symbol = symbol
        self.time_frame = None
        self.open = 0
        self.high = 0
        self.low = 0
        self.close = 0
        self.volume = 0
        self.timestamp = 0

    def to_event(self):
        event = Event(EVENT_SYMBOL_BAR_RAW[self.symbol][self.time_frame], data=self)
        return event

    @classmethod
    def get_keys(cls):
        """
        :return: field names in print order use for create dataframe
        """
        return cls.__keys__


class Tick:
    """Tick数据对象"""
    __DEPTH = 5
    __slots__ = ["symbol", "openPrice", "highPrice", "lowPrice", "lastPrice", "volume", "openInterest",
                 "upperLimit", "lowerLimit", "time", "time_msc"]
    __slots__.extend(["bidPrice%s" % (x + 1) for x in range(__DEPTH)])
    __slots__.extend(["bidVolume%s" % (x + 1) for x in range(__DEPTH)])
    __slots__.extend(["askPrice%s" % (x + 1) for x in range(__DEPTH)])
    __slots__.extend(["askVolume%s" % (x + 1) for x in range(__DEPTH)])

    __keys__ = __slots__ + ['datetime']

    datetime = property(lambda self: datetime.fromtimestamp(self.timestamp))

    @classmethod
    def get_depth(cls):
        return cls.__DEPTH

    def __init__(self, symbol):
        """Constructor"""
        self.symbol = symbol  # 合约代码
        # OHLC
        self.openPrice = 0
        self.highPrice = 0
        self.lowPrice = 0
        self.lastPrice = 0

        self.volume = 0  # 成交量
        self.openInterest = 0  # 持仓量

        self.upperLimit = 0  # 涨停价
        self.lowerLimit = 0  # 跌停价

        self.time = 0  # 更新时间和毫秒
        self.time_msc = 0

        # 深度行情
        # TODO 用反射比正常访问慢一倍，以后再设法优化吧
        for depth in range(self.__class__.__DEPTH):
            setattr(self, "bidPrice%s" % (depth + 1), 0)
            setattr(self, "bidVolume%s" % (depth + 1), 0)
            setattr(self, "askPrice%s" % (depth + 1), 0)
            setattr(self, "askVolume%s" % (depth + 1), 0)

    def to_event(self):
        event = Event(EVENT_SYMBOL_TICK_RAW[self.symbol], data=self)
        return event


if __name__ == '__main__':
    c = Bar('1')
    print(c.to_dict())
    print(BarFactory.to_dict(c))
    index = range(100)
    a = map(lambda x: Bar(x).to_dict(), index)
    print(pd.DataFrame(list(a), columns=BarFactory.get_keys()))
