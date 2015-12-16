# encoding: UTF-8
import json

from ..event.eventEngine import *
'''
from pymongo import connection as Connection
from pymongo.errors import *
'''

from .strategyEngine import *
from ..wind import *

########################################################################
class LimitOrder(object):
    """限价单对象"""

    #----------------------------------------------------------------------
    def __init__(self, symbol):
        """Constructor"""
        self.symbol = symbol
        self.price = 0
        self.volume = 0
        self.direction = None
        self.offset = None


########################################################################
class BacktestingEngine(object):
    """
    回测引擎，作用：
    1. 从数据库中读取数据并回放
    2. 作为StrategyEngine创建时的参数传入
    """

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.eventEngine = EventEngine()
        
        # 策略引擎
        self.strategyEngine = None
        
        # TICK历史数据列表，由于要使用For循环来实现仿真回放
        # 使用list的速度比Numpy和Pandas都要更快
        self.listDataHistory = []
        
        # 限价单字典
        self.dictOrder = {}
        
        # 最新的TICK数据
        self.currentData = None
        
        # 回测的成交字典
        self.listTrade = []
        
        # 报单编号
        self.orderRef = 0
        
        # 成交编号
        self.tradeID = 0
        
    #----------------------------------------------------------------------
    def setStrategyEngine(self, engine):
        """设置策略引擎"""
        self.strategyEngine = engine
        self.writeLog(u'策略引擎设置完成')
    
    #----------------------------------------------------------------------
    def connectMongo(self):
        """连接MongoDB数据库"""
        try:
            self.__mongoConnection = Connection()
            self.__mongoConnected = True
            self.__mongoTickDB = self.__mongoConnection['TickDB']
            self.writeLog(u'回测引擎连接MongoDB成功')
        except ConnectionFailure:
            self.writeLog(u'回测引擎连接MongoDB失败') 

    #----------------------------------------------------------------------
    def connectWind(self):

        #----        
        self.__windConnected = True
        return
        #----
        
        self.__windConnected=wind.connectWind()
        if self.__windConnected:
            self.writeLog(u"回测引擎连接Wind数据成功")
        else:
            self.writeLog(u"回测引擎连接Wind数据失败")
            
    #----------------------------------------------------------------------
    def loadDataHistory(self, symbol, startDate, endDate):
        """载入历史TICK数据"""
        if self.__mongoConnected:
            collection = self.__mongoTickDB[symbol]
            
            # 如果输入了读取TICK的最后日期
            if endDate:
                cx = collection.find({'date':{'$gte':startDate, '$lte':endDate}})
            elif startDate:
                cx = collection.find({'date':{'$gte':startDate}})
            else:
                cx = collection.find()
            
            # 将TICK数据读入内存
            self.listDataHistory = [data for data in cx]
            
            self.writeLog(u'历史TICK数据载入完成')
        else:
            self.writeLog(u'MongoDB未连接，请检查')
    
    #----------------------------------------------------------------------       
    def loadDataHistoryFromWind(self, symbol, startTime, endTime, barType = '1'):
        if self.__windConnected:
            self.listDataHistory = wind.getBarData(symbol, startTime , endTime, barType = '1')         
            if not self.listDataHistory == None:
                self.writeLog(u'历史K线数据载入完成')
            else:
                self.writeLog(u'历史K线数据载入失败')
        else:
            self.writeLog(u'Wind未连接，请检查')
        
            
    #----------------------------------------------------------------------
    def processLimitOrder(self):
        """处理限价单"""
        for ref, order in self.dictOrder.items():
            # 如果是买单，且限价大于等于当前TICK的卖一价，则假设成交
            if order.direction == DIRECTION_BUY and \
               order.price >= self.currentData['AskPrice1']:
                self.executeLimitOrder(ref, order, self.currentData['AskPrice1'])
            # 如果是卖单，且限价低于当前TICK的买一价，则假设全部成交
            if order.direction == DIRECTION_SELL and \
               order.price <= self.currentData['BidPrice1']:
                self.executeLimitOrder(ref, order, self.currentData['BidPrice1'])\
            
    def processLimitOrderByBar(self):
        """处理限价单"""
        #成交的表单列表
        listOrderExecuted = []         
        for ref,order in self.dictOrder.items():
            if order.direction == DIRECTION_BUY and \
               order.price <= self.currentData['High']:
                   self.executeLimitOrder(ref,order,self.currentData['High'])
                   listOrderExecuted.append(ref)
            if order.direction == DIRECTION_SELL and \
               order.price >= self.currentData['Low']:
                   self.executeLimitOrder(ref,order,self.currentData['Low'])
                   listOrderExecuted.append(ref)
        for ref in listOrderExecuted:
            del self.dictOrder[ref]
    #----------------------------------------------------------------------
    def executeLimitOrder(self, ref, order, price):
        """限价单成交处理"""
        # 成交回报
        self.tradeID = self.tradeID + 1
        
        tradeData = {}
        tradeData['InstrumentID'] = order.symbol
        tradeData['OrderRef'] = ref
        tradeData['TradeID'] = str(self.tradeID)
        tradeData['Direction'] = order.direction
        tradeData['OffsetFlag'] = order.offset
        tradeData['Price'] = price
        tradeData['Volume'] = order.volume
        
        tradeEvent = Event()
        tradeEvent.dict_['data'] = tradeData
        self.strategyEngine.updateTrade(tradeEvent)
        
        # 报单回报
        orderData = {}
        orderData['InstrumentID'] = order.symbol
        orderData['OrderRef'] = ref
        orderData['Direction'] = order.direction
        orderData['CombOffsetFlag'] = order.offset
        orderData['LimitPrice'] = price
        orderData['VolumeTotalOriginal'] = order.volume
        orderData['VolumeTraded'] = order.volume
        orderData['InsertTime'] = ''
        orderData['CancelTime'] = ''
        orderData['FrontID'] = ''
        orderData['SessionID'] = ''
        orderData['OrderStatus'] = ''
        
        orderEvent = Event()
        orderEvent.dict_['data'] = orderData
        self.strategyEngine.updateOrder(orderEvent)
        
        # 记录该成交到列表中
        self.listTrade.append(tradeData)
                
    #----------------------------------------------------------------------
    def startBacktesting(self):
        """开始回测"""
        self.writeLog(u'开始回测')
        
        listDataHistory = self.listDataHistory        
        listKey = [k for k,v in listDataHistory.items() if type(v) == list]
        length = len(listDataHistory['Time'])    
        data = {}        
        data['InstrumentID'] = listDataHistory['InstrumentID']
        for i in range(length):
            
            for k in listKey:            
                data[ k ] = listDataHistory[k][i]
            
            # 记录最新的TICK数据
            self.currentData = data
            
            # 处理限价单
            self.processLimitOrderByBar()
            
            # 推送到策略引擎中
            event = Event()
            event.dict_['data'] = data
            self.strategyEngine.updateBarData(event)
        
        self.saveTradeData()
        
        self.writeLog(u'回测结束')
    
    #----------------------------------------------------------------------
    def sendOrder(self, instrumentid, exchangeid, price, pricetype, volume, direction, offset):
        """回测发单"""
        order = LimitOrder(instrumentid)
        order.price = price
        order.direction = direction
        order.volume = volume
        order.offset = offset
        
        self.orderRef = self.orderRef + 1
        self.dictOrder[str(self.orderRef)] = order
        
        return str(self.orderRef)
    
    #----------------------------------------------------------------------
    def cancelOrder(self, instrumentid, exchangeid, orderref, frontid, sessionid):
        """回测撤单"""
        try:
            del self.dictOrder[orderref]
        except KeyError:
            pass
        
    #----------------------------------------------------------------------
    def writeLog(self, log):
        """写日志"""
        print (log)
        
    #----------------------------------------------------------------------
    def selectInstrument(self, symbol):
        """读取合约数据"""
        d = {}
        d['ExchangeID'] = 'BackTesting'
        return d
    
    #----------------------------------------------------------------------
    def saveTradeData(self):
        """保存交易记录"""
        print(self.listTrade)        
        with open('TradeRecord.bf','w') as f:
            json.dump(self.listTrade,f)            
            f.close()

    #----------------------------------------------------------------------
    def subscribe(self, symbol, exchange):
        """仿真订阅合约"""
        pass
        
    
    