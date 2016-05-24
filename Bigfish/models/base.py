# -*- coding: utf-8 -*-
"""
Created on Sat Dec 12 15:35:55 2015

@author: BurdenBear
"""
from enum import Enum

__all__ = ['Currency', 'RunningMode', "TradingMode", "TradingCommands"]


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


# TODO running 状态改变的时候可能要加上线程锁
class Runnable:
    def __init__(self):
        self._running = False

    @property
    def running(self):
        return self._running

    def _start(self):
        raise NotImplementedError

    def start(self):
        if self._running:
            return
        else:
            self._start()
            self._running = True

    def _stop(self):
        raise NotImplementedError

    def stop(self):
        if not self._running:
            return
        else:
            self._stop()
            self._running = False


class Currency:
    """货币对象"""

    def __init__(self, name=""):
        self.__name = name
