# -*- coding: utf-8 -*-
#内置模块
from datetime import datetime

#自定义模块
from .strategyEngine import *

#math包里没这个函数，自己写个
def sign (n):
    if n > 0:
        return 1
    elif n < 0:
        return -1
    else:
        return 0

class demoStrategy(StrategyTemplate):
    """测试用策略，突破20Bar高点买入开仓，跌破10Bar低点卖出平仓；跌破20Bar卖出开仓，
       突破10Bar高点买入平仓
    """
    #----------------------------------------------------------------------    
    def __init__(self, name, symbol, engine):
        super(demoStrategy, self).__init__(name, symbol, engine)
        #策略参数
        self.fastLength = 10
        self.slowLength = 20
        
        #保存K线数据的列表对象
        self.listOpen = []
        self.listHigh = []
        self.listLow = []
        self.listClose = []
        self.listVolume = []
        self.listTime = []
        
        #策略部位相关数据
        self.totalBar = 1        
        self.currentBar = 0
        self.marketPosition = 0
        self.currentContracts = 0
        
        #报单代码列表
        self.listOrderRef = []
        self.listStopOrder = []
        
        #
        self.onBarGeneratorInstance = self.onBarGenerator()
        #是否完成了初始化
        self.initCompleted = False
    
    #----------------------------------------------------------------------
    def loadSetting(self, strategySetting):
        pass
    
    #----------------------------------------------------------------------
    def onOrder(self, order):
        pass
    
    #----------------------------------------------------------------------    
    def onTrade(self, trade):
        """交易更新"""
        """trade.direction = 1 买单,trade.direction = -1 卖单
           marketposition = 1 持多仓,-1持空仓,0为空仓
        """
        marketPosition = self.marketPosition
        if trade.direction * marketPosition >= 0:
                self.currentContracts += trade.volume
                self.marketPosition = trade.direction
        else:
                currentConstracts = self.currentContracts - trade.volume
                self.currentConstracts = abs(currentConstracts)
                self.marketPosition = marketPosition * sign(currentConstracts)

    def onBarGenerator(self):
        if self.initCompleted == False:        
            fastLength = self.fastLength
            slowLength = self.slowLength
            listOpen = self.listOpen
            listHigh = self.listHigh
            listLow = self.listLow        
            listClose = self.listClose
            listVolume = self.listVolume
            listTime = self.listTime
            buy = self.buy
            short =self.short
            sell = self.sell     
            cover = self.cover            
            self.initCompleted = True
        while True:
            Open = listOpen[-1]
            High = listHigh[-1]
            Low = listLow[-1]        
            Close = listClose[-1]
            Volume = listVolume[-1]
            Time = listTime [-1]
            marketPosition = self.marketPosition            
            totalBar = self.totalBar 
            #print(totalBar,Open,High,Low,Close,mar)            
            self.totalBar = totalBar + 1           
           
            #计算slowLengh内最高最低价以及入场
            if totalBar > fastLength:
                highestFast = max(listHigh[(-fastLength-1):-1])
                lowestFast = min(listLow[(-fastLength-1):-1])
                if (High > highestFast)and(marketPosition < 0):
                    self.cover(highestFast, 1)
                    print("cover")
                if (Low  < lowestFast)and(marketPosition > 0):
                    self.sell(lowestFast, 1)
                    print("sell")


            #维护slowLengh内最高最低价以及入场
            if totalBar > slowLength:
                highestSlow = max(listHigh[(-slowLength-1):-1])
                lowestSlow = min(listLow[(-slowLength-1):-1])
                if (High > highestSlow) and (marketPosition == 0):
                    self.buy(highestSlow,1)
                    print("buy")
                if (Low < lowestSlow) and (marketPosition == 0):
                    self.short(lowestSlow,1)
                    print("short")            
            yield
    
    #----------------------------------------------------------------------        
    def onBar(self,bar):
        self.listOpen.append(bar.open)
        self.listHigh.append(bar.high)
        self.listLow.append(bar.low)
        self.listClose.append(bar.close)
        self.listVolume.append(bar.volume)
        self.listTime.append(bar.time)
        next(self.onBarGeneratorInstance)
    
        
                
            
            
                        
                    