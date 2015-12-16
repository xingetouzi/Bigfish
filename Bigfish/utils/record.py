# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 10:34:52 2015

@author: BurdenBear
"""

###################################################################
class dictlike():
    def to_dict(self):
        return ({slot:getattr(self,slot) for slot in self.__slots__})
        
###################################################################
class TranscationRecord():
    """交易记录对象"""    
    __slots__ = ["strategy", "lot", "profit", "symbol", "ctime"]
    def __init__(self, strategy="" , lot=0, profit=0, symbol="", ctime=None):
        super().__init__        
        self.strategy = strategy
        self.lot = lot
        self.profit = profit
        self.symbol = symbol
        self.ctime = ctime
        
###################################################################        
class YieldRecord(dictlike):
    """收益记录对象"""    
    __slots__ = ["yield_", "ctime"]    
    def __init__(self, yield_=0, ctime=None):
        super().__init__        
        self.yield_ = yield_
        self.ctime = ctime
     