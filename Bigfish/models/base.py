# -*- coding: utf-8 -*-
"""
Created on Sat Dec 12 15:35:55 2015

@author: BurdenBear
"""
from enum import Enum

__all__ = ['Currency', 'RunningMode', "TradingMode"]


class RunningMode(Enum):
    backtest = 0
    runtime = 1


class TradingMode(Enum):
    on_bar = 0
    on_tick = 1


class Currency:
    """货币对象"""

    def __init__(self, name=""):
        self.__name = name
