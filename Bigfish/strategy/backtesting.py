# -*- coding: utf-8 -*-
#自定义模块
from .strategyEngine import *
from .backtestingEngine import *
from .strategyContainer import *
#系统模块
from datetime import datetime
import time
# 回测脚本    
def backtesting(symbol,strategyNames,sourcePath,**kwargs):
 
    # 创建回测引擎
    be = BacktestingEngine()
    
    # 创建策略引擎对象
    se = StrategyEngine(be.eventEngine, be, backtesting=True)
    be.setStrategyEngine(se)
    sc = StrategyContainer('strategyContainer',symbol,se)
    sc.setSourcePath(sourcePath)    
    type_ = type(strategyNames)    
    if type_ == str:
        sc.addStrategy(strategyNames)
    elif (type_ == list):
        for strategyName in strategyNames: 
            sc.addStrategy(strategyName)
    else:
        print('策略名只支持字符串及字符串列表，请检查')
        return
    endTime = kwargs.pop('endTime',datetime.fromtimestamp(int(time.time())))
    startTime = kwargs.pop('startTime',datetime(2015,9,28))
    
    # 初始化回测引擎
    be.connectWind()
    be.loadDataHistoryFromWind(symbol, startTime, endTime)
    
    se.addStrategy(sc)
    
    # 启动所有策略
    se.startAll()
    
    # 开始回测
    be.startBacktesting()