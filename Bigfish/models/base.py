# -*- coding: utf-8 -*-
"""
Created on Sat Dec 12 15:35:55 2015

@author: BurdenBear
"""
from enum import Enum

__all__ = ['Currency', 'RunningMode', "TradingMode", "TradingCommands", "BfConfig"]


# TODO 把这些枚举量的定义都拿出去

class RunningMode(Enum):
    backtest = 0
    runtime = 1


class TradingMode(Enum):
    on_bar = 0
    on_tick = 1


class TradingCommands(Enum):
    buy = "Buy"
    sell = "SellShort"
    sellshort = "SellShort"
    buytocover = "BuyToCover"


class BfConfig:
    """
    运行一个策略所需的配置类
    """

    def __init__(self, user='', name='', symbols=[], time_frame='', start_time=None, end_time=None, capital_base=100000,
                 commission=0, slippage=0, account=None, password=None, running_mode=RunningMode.backtest.value,
                 trading_mode=TradingMode.on_bar.value):
        self.user = user
        self.name = name
        self.capital_base = capital_base
        self.time_frame = time_frame
        self.symbols = symbols
        self.start_time = start_time
        self.end_time = end_time
        self.commission = commission
        self.slippage = slippage
        self.account = account
        self.password = password
        self.running_mode = RunningMode(running_mode)
        self.trading_mode = TradingMode(trading_mode)

    def __getitem__(self, item):
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError

    def to_dict(self):
        result = {}
        for field in ["user", "name", "capital_base", "time_frame", "symbols", "start_time", "end_time",
                      "commission", "slippage", "account", "password"]:
            result[field] = getattr(self, field)
        result["running_mode"] = self.running_mode.value
        result["trading_mode"] = self.trading_mode.value
        return result


class Currency:
    """货币对象"""

    def __init__(self, name=""):
        self.__name = name
