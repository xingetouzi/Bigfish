# -*- coding: utf-8 -*-
"""
Created on Sat Dec 12 15:35:55 2015

@author: BurdenBear
"""
from Bigfish.utils.common import DictLike
import os
import sqlite3

__all__ = ['Symbol', 'Currency']
_DBPATH = os.path.join(os.path.realpath(os.path.split(__file__)[0]),'symbol.sqlite3')

###################################################################
class Symbol(DictLike):
    __all = {}
    __slots__ = ["code", "name"]
    @classmethod
    def get_all_symbols(cls):
        #TODO 真正的获取symbol，拟定从数据库中获取
        #TODO 资产的其他信息，如滑点、手续费等信息
        #将以json的形式存于文件或数据库中        
        if len(cls.__all) == 0:
           with sqlite3.connect(_DBPATH) as conn:
               cur = conn.cursor()
               cur.execute("select code,name from symbol;")
               for item in cur.fetchall():
                   cls.__all[item[0]] = Symbol(*item)
        return([symbol.to_dict() for symbol in cls.__all.values()])
    def __init__(self, code, name):
        self.code = code
        self.name = name
    
###################################################################
class Currency:
    """货币对象"""
    def __init__(self, name=""):
        self.__name = name
