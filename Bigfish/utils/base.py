# -*- coding: utf-8 -*-
"""
Created on Sat Dec 12 15:35:55 2015

@author: BurdenBear
"""

__all__ = ['Currency']


class Currency:
    """货币对象"""

    def __init__(self, name=""):
        self.__name = name
