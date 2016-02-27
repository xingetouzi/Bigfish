# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 10:06:21 2015

@author: BurdenBear
"""
from Bigfish.event.event import EVENT_BAR_SYMBOL, Event
from Bigfish.models.common import DictLike
from Bigfish.utils.common import _TIME_FRAME_PERIOD
import pandas as pd


class BarFactory:
    @classmethod
    def to_dict(cls, bar):
        temp = super(Bar, bar).to_dict()
        temp['close_time'] = bar.close_time
        return temp

    @classmethod
    def to_event(cls, bar):
        event = Event(EVENT_BAR_SYMBOL[bar.symbol][bar.time_frame], {'data': bar})
        return event

    @classmethod
    def get_fields(cls):
        """
        :return: field names in print order use for create dataframe
        """
        temp = Bar.get_fields()
        temp[-1:-1] = ["close_time"]
        return temp


class Bar(DictLike):
    """K线数据对象（开高低收成交量时间）"""
    __slots__ = ["symbol", "open", "high", "low", "close", "volume", "time", "time_frame"]
    close_time = property(lambda self: self.time + _TIME_FRAME_PERIOD.get(self.time_frame, 0))

    def __init__(self, symbol):
        self.symbol = symbol
        self.time_frame = None
        self.open = 0
        self.high = 0
        self.low = 0
        self.close = 0
        self.volume = 0
        self.time = 0

    def to_dict(self):
        temp = super(Bar, self).to_dict()
        temp['close_time'] = self.close_time
        return temp

    def to_event(self):
        event = Event(EVENT_BAR_SYMBOL[self.symbol][self.time_frame], {'data': self})
        return event

    @classmethod
    def get_fields(cls):
        """
        :return: field names in print order use for create dataframe
        """
        temp = super().get_fields()
        temp[-1:-1] = ["close_time"]
        return temp


class Tick:
    """Tick数据对象"""
    __DEPTH = 5
    __slots__ = ["symbol", "openPrice", "highPrice", "lowPrice", "lastPrice", "volume", "openInterest",
                 "upperLimit", "lowerLimit", "time", "time_msc"]
    __slots__.extend(["bidPrice%s" % (x + 1) for x in range(__DEPTH)])
    __slots__.extend(["bidVolume%s" % (x + 1) for x in range(__DEPTH)])
    __slots__.extend(["askPrice%s" % (x + 1) for x in range(__DEPTH)])
    __slots__.extend(["askVolume%s" % (x + 1) for x in range(__DEPTH)])

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


if __name__ == '__main__':
    c = Bar('1')
    print(c.to_dict())
    print(BarFactory.to_dict(c))
    index = range(100)
    a = map(lambda x: Bar(x).to_dict(), index)
    print(pd.DataFrame(list(a), columns=BarFactory.get_fields()))
