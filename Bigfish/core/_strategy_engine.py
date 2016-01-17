# -*- coding: utf-8 -*-

"""
Created on Wed Nov 25 21:09:47 2015

@author: BurdenBear
"""
import time

# 自定义模块
from Bigfish.core import AccountManager
from Bigfish.event.event import *
from Bigfish.event.engine import EventEngine
from Bigfish.models.trade import *
from Bigfish.utils.common import set_attr, get_attr
from Bigfish.models.common import deque
from Bigfish.event.handle import SymbolsListener
from functools import partial


# %% 策略引擎语句块
########################################################################
class StrategyEngine(object):
    """策略引擎"""
    CACHE_MAXLEN = 10000

    # ----------------------------------------------------------------------
    def __init__(self, backtesting=False):
        """Constructor"""
        self.__event_engine = EventEngine()  # 事件处理引擎
        self.__account_manager = AccountManager()  # 账户管理
        self.__backtesting = backtesting  # 是否为回测
        self.__orders_done = {}  # 保存所有已处理报单数据的字典
        self.__orders_todo = {}  # 保存所有未处理报单（即挂单）数据的字典
        self.__deals = {}  # 保存所有成交数据的字典
        self.__positions = {}  # Key:id, value:position with responding id
        self.__strategys = {}  # 保存策略对象的字典,key为策略名称,value为策略对象
        self.__data = {}  # 统一的数据视图
        self.__symbols = {}  # key:(symbol,timeframe),value:maxlen
        self.start_time = None
        self.end_time = None
        self.__current_positions = {}  # key：symbol，value：current position
        self.__initial_positions = {}  # key：symbol，value：initial position

    # TODO单独放入utils中
    symbols = property(partial(get_attr, attr='symbols'), None, None)
    start_time = property(partial(get_attr, attr='start_time'), partial(set_attr, attr='start_time'), None)
    end_time = property(partial(get_attr, attr='end_time'), partial(set_attr, attr='end_time'), None)

    # ----------------------------------------------------------------------
    def get_current_contracts(self):
        # TODO 现在持仓手数
        return ()

    # ----------------------------------------------------------------------
    def get_current_positions(self):
        # TODO 读取每个品种的有效Position
        return self.__current_positions

    def get_deals(self):
        return self.__deals

    def get_positions(self):
        return self.__positions

    # ----------------------------------------------------------------------
    def get_data(self):
        return self.__data

    # ----------------------------------------------------------------------
    def get_profit_records(self):
        """获取平仓收益记录"""
        return self.__account_manager.get_profit_records()

    # ----------------------------------------------------------------------
    def get_traceback(self):
        pass

    # ----------------------------------------------------------------------
    def get_position_records(self):
        """获取仓位收益记录"""

        def get_point(deal, entry, volume):
            if entry == DEAL_ENTRY_IN:
                if deal.type == DEAL_TYPE_BUY:
                    return ({'type': 'point', 'x': deal.time + deal.time_msc / (10 ** 6),
                             'y': deal.price, 'color': 'buy', 'text': 'Buy %s' % volume})
                elif deal.type == DEAL_TYPE_SELL:
                    return ({'type': 'point', 'x': deal.time + deal.time_msc / (10 ** 6),
                             'y': deal.price, 'color': 'short', 'text': 'Short %s' % volume})
            elif entry == DEAL_ENTRY_OUT:
                if deal.type == DEAL_TYPE_BUY:
                    return ({'type': 'point', 'x': deal.time + deal.time_msc / (10 ** 6),
                             'y': deal.price, 'color': 'cover', 'text': 'Cover %s' % volume})
                elif deal.type == DEAL_TYPE_SELL:
                    return ({'type': 'point', 'x': deal.time + deal.time_msc / (10 ** 6),
                             'y': deal.price, 'color': 'sell', 'text': 'Sell %s' % volume})

        def get_lines(position_start, position_end):
            deal_start = self.__deals[position_start.deal]
            deal_end = self.__deals[position_end.deal]
            start_time = deal_start.time + deal_start.time_msc / (10 ** 6)
            end_time = deal_end.time + deal_end.time_msc / (10 ** 6)
            result = {'type': 'line', 'x_start': start_time, 'x_end': end_time, 'y_start': deal_start.price,
                      'y_end': deal_end.price}
            if (deal_end.type == DEAL_TYPE_BUY) ^ (deal_start.price >= deal_end.price):
                result['color'] = 'win'
            else:
                result['color'] = 'lose'

        def next_position(position):
            return self.__positions.get(position.next_id, None)

        def prev_position(position):
            return self.__positions.get(position.prev_id, None)

        result = []
        stack = []
        for symbol in {symbol for (symbol, _) in self.__symbols}:
            position = next_position(self.__init_positions[symbol])
            while (position != None):
                deal = self.__deals[position.deal]
                if deal.entry == DEAL_ENTRY_IN:  # open or overweight position
                    result.append(get_point(deal, DEAL_ENTRY_IN, deal.volume))
                    stack.append((position, deal.volume))
                else:
                    if deal.entry == DEAL_ENTRY_INOUT:  # reverse position
                        volume_left = deal.volume - position.volume
                        result.append(get_point(deal, DEAL_ENTRY_IN, position.volume))
                    else:  # underweight position
                        volume_left = deal.volume
                    result.append(get_point(deal, DEAL_ENTRY_OUT, volume_left))
                    while volume_left > 0:
                        position_start, volume = stack.pop()
                        result.append(get_lines(position_start, position))
                        volume_left -= volume
                    if volume_left < 0:
                        stack.append(position_start, -volume_left)
                    elif deal.entry == DEAL_ENTRY_INOUT and position.volume > 0:
                        stack.append((position, position.volume))
                position = next_position(position)
        return result

    # ----------------------------------------------------------------------
    def set_capital_base(self, base):
        self.__account_manager.set_capital_base(base)

    # ----------------------------------------------------------------------
    def add_symbols(self, symbols, time_frame, max_length=0):
        for symbol in symbols:
            if (symbol, time_frame) not in self.__symbols:
                self.__symbols[(symbol, time_frame)] = max_length
            self.__symbols[(symbol, time_frame)] = max(max_length, self.__symbols[(symbol, time_frame)])
            self.register_event(EVENT_BAR_SYMBOL[symbol][time_frame], self.update_bar_data)

    # ----------------------------------------------------------------------
    def initialize(self):
        # TODO数据结构还需修改
        self.__deals = {}
        self.__positions = {}
        self.__data = {}
        for (symbol, time_frame), maxlen in self.__symbols.items():
            if symbol not in self.__data:
                self.__data[symbol] = {}
            if time_frame not in self.__data[symbol]:
                self.__data[symbol][time_frame] = {}
            if maxlen == 0:
                maxlen = self.CACHE_MAXLEN
            for field in ['open', 'high', 'low', 'close', 'time', 'volume']:
                self.__data[symbol][time_frame][field] = deque(maxlen=maxlen)
            if symbol not in self.__current_positions:
                position = Position(symbol)
                self.__current_positions[symbol] = position
                self.__initial_positions[symbol] = position
                self.__positions[position.get_id()] = position

    # ----------------------------------------------------------------------
    def add_strategy(self, strategy):
        """添加已创建的策略实例"""
        self.__strategys[strategy.get_id()] = strategy
        strategy.engine = self
        # ----------------------------------------------------------------------

    def update_market_data(self, event):
        """行情更新"""
        # TODO行情数据
        pass

    # ----------------------------------------------------------------------
    def update_bar_data(self, event):
        bar = event.content['data']
        symbol = bar.symbol
        time_frame = bar.time_frame
        for field in ['open', 'high', 'low', 'close', 'time', 'volume']:
            self.__data[symbol][time_frame][field].appendleft(getattr(bar, field))

    # ----------------------------------------------------------------------
    def __process_order(self, tick):
        """处理停止单"""
        pass

    # ----------------------------------------------------------------------
    def update_order(self, event):
        """报单更新"""
        # TODO 成交更新

    # ----------------------------------------------------------------------
    def update_trade(self, event):
        """成交更新"""
        # TODO 成交更新
        pass

    # ----------------------------------------------------------------------
    def __update_position(self, deal):
        def sign(num):
            if abs(num) <= 10 ** -7:
                return (0)
            elif num > 0:
                return (1)
            else:
                return (-1)

        if deal.volume == 0:    return
        position_prev = self.__current_positions[deal.symbol]
        position_now = Position(deal.symbol, deal.strategy, deal.handle)
        position_now.prev_id = position_prev.get_id()
        position_prev.next_id = position_now.get_id()
        position = position_prev.type
        # XXX常量定义改变这里的映射函数也可能改变
        if deal.type * position >= 0:
            deal.entry = DEAL_ENTRY_IN
            if position == 0:  # open position
                position_now.price_open = deal.price
                position_now.time_open = deal.time
                position_now.time_open_msc = deal.time_msc
            else:  # overweight position
                position_now.time_open = position_prev.time_open
                position_now.time_open_msc = position_prev.time_open_msc
            position_now.volume = deal.volume + position_prev.volume
            position_now.type = deal.type
            position_now.price_current = (position_prev.price_current * position_prev.volume
                                          + deal.price * deal.volume) / position_now.volume
        else:
            contracts = position_prev.volume - deal.volume
            position_now.volume = abs(contracts)
            position_now.type = position * sign(contracts)
            if position_now.type == 0:  # close position
                deal.entry = DEAL_ENTRY_OUT
                deal.profit = (deal.price - position_prev.price_current) * position * position_prev.volume
                position_now.price_current = 0
                position_now.volume = 0  # 防止浮点数精度可能引起的问题
                position_now.time_open = position_prev.time_open
                position_now.time_open_msc = position_prev.time_open_msc
            elif position_now != position:  # reverse position
                deal.entry = DEAL_ENTRY_INOUT
                deal.profit = (deal.price - position_prev.price_current) * position * position_prev.volume
                position_now.price_current = deal.price
                position_now.time_open = deal.time
                position_now.time_open_msc = deal.time_msc
                position_now.price_open = position_now.price_current
            else:  # underweight position
                # XXX 平部分仓位是直接计算入平仓收益还是将收益暂时算在浮动中
                deal.entry = DEAL_ENTRY_OUT
                deal.profit = (deal.price - position_prev.price_current) * position * deal.volume
                position_now.price_current = position_prev.price_current
                position_now.time_open = position_prev.time_open
                position_now.time_open_msc = position_prev.time_open_msc
        position_now.time_update = deal.time
        position_now.time_update_msc = deal.time_msc
        deal.position = position_now.get_id()
        position_now.deal = deal.get_id()
        self.__current_positions[deal.symbol] = position_now
        self.__positions[position_now.get_id()] = position_now
        self.__deals[deal.get_id()] = deal
        if deal.profit != 0:
            self.__account_manager.update_deal(deal)

    # ----------------------------------------------------------------------
    @staticmethod
    def check_order(order):
        if not isinstance(order, Order):
            return False
        # TODO更多关于订单合法性的检查
        return True

    # ----------------------------------------------------------------------
    def __send_order_to_broker(self, order):
        if self.__backtesting:
            time_frame = SymbolsListener.get_by_id(order.handle).get_time_frame()
            time_ = self.__data[order.symbol][time_frame]["time"][0]
            order.time_done = int(time_)
            order.time_done_msc = int((time_ - int(time_)) * (10 ** 6))
            order.volume_current = order.volume_initial
            deal = Deal(order.symbol, order.strategy, order.handle)
            deal.volume = order.volume_current
            deal.time = order.time_done
            deal.time_msc = order.time_done_msc
            deal.type = 1 - ((order.type & 1) << 1)  # 参见ENUM_ORDER_TYPE和ENUM_DEAL_TYPE的定义
            deal.price = self.__data[order.symbol][time_frame]["close"][0]
            # TODO加入手续费等
            order.deal = deal.get_id()
            deal.order = order.get_id()
            return [deal], {}
            # TODO 市价单成交
        else:
            pass
            # TODO 实盘交易

    # ----------------------------------------------------------------------
    def send_order(self, order):
        """
        发单（仅允许限价单）
        symbol：合约代码
        direction：方向，DIRECTION_BUY/DIRECTION_SELL
        offset：开平，OFFSET_OPEN/OFFSET_CLOSE
        price：下单价格
        volume：下单手数
        strategy：策略对象 
        """
        # TODO 更多属性的处理
        if self.check_order(order):
            if order.type <= 1:  # market order
                # send_order_to_broker = async_handle(self.__event_engine, self.__update_position)(self.__send_order_to_broker)
                # send_order_to_broker(order)
                result = self.__send_order_to_broker(order)
                self.__update_position(*result[0])
            else:
                self.__orders_todo[order.get_id()] = order
            return True
        else:
            return False

    # ----------------------------------------------------------------------
    def cancel_order(self, order_id):
        """
        撤单
        """
        if order_id == 0:
            self.__orders_todo = {}
        else:
            if order_id in self.__orders_todo:
                del (self.__orders_todo[order_id])

    # ----------------------------------------------------------------------
    def put_event(self, event):
        # TODO 加入验证
        # TODO 多了一层函数调用，尝试用绑定的形式
        self.__event_engine.put(event)

    # ----------------------------------------------------------------------
    def register_event(self, event_type, handle):
        """注册事件监听"""
        # TODO  加入验证
        self.__event_engine.register(event_type, handle)

    def unregister_event(self, event_type, handle):
        """取消事件监听"""
        self.__event_engine.unregister(event_type, handle)

    # ----------------------------------------------------------------------
    def writeLog(self, log):
        """写日志"""
        event = Event(type_=EVENT_LOG)
        event.content['log'] = log
        self.__event_engine.put(event)

    # ----------------------------------------------------------------------
    def start(self):
        """启动所有策略"""
        self.__event_engine.start()
        for strategy in self.__strategys.values():
            strategy.start()
            # ----------------------------------------------------------------------

    def stop(self):
        """停止所有策略"""
        self.__event_engine.stop()
        for strategy in self.__strategys.values():
            strategy.stop()

    def wait(self):
        """等待所有事件处理完毕"""
        self.__event_engine.wait()
        self.stop()

    # TODO 对限价单的支持
    # ----------------------------------------------------------------------
    def sell(self, symbol, volume=1, price=None, stop=False, limit=False, strategy=None, listener=None):
        if volume == 0:
            return
        position = self.__current_positions.get(symbol, None)
        if not position or position.type <= 0:
            return  # XXX可能的返回值
        order = Order(symbol, ORDER_TYPE_SELL, strategy, listener)
        order.volume_initial = volume
        if self.__backtesting:
            time_ = self.__data[symbol][SymbolsListener.get_by_id(listener).get_time_frame()]['time'][0]
        else:
            time_ = time.time()
        order.time_setup = int(time_)
        order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
        return self.send_order(order)

    # ----------------------------------------------------------------------
    def buy(self, symbol, volume=1, price=None, stop=False, limit=False, strategy=None, listener=None):
        if self.__backtesting:
            time_ = self.__data[symbol][SymbolsListener.get_by_id(listener).get_time_frame()]['time'][0]
        else:
            time_ = time.time()
        position = self.__current_positions.get(symbol, None)
        if position and position.type < 0:
            order = Order(symbol, ORDER_TYPE_BUY, strategy, listener)
            order.volume_initial = position.volume
            order.time_setup = int(time_)
            order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
            # TODO 这里应该要支持事务性的下单操作
            self.send_order(order)
        if volume == 0:
            return
        order = Order(symbol, ORDER_TYPE_BUY, strategy, listener)
        order.volume_initial = volume
        order.time_setup = int(time_)
        order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
        return self.send_order(order)

    # ----------------------------------------------------------------------
    def cover(self, symbol, volume=1, price=None, stop=False, limit=False, strategy=None, listener=None):
        if volume == 0:
            return
        position = self.__current_positions.get(symbol, None)
        order = Order(symbol, ORDER_TYPE_BUY, strategy, listener)
        if not position or position.type >= 0:
            return  # XXX可能的返回值
        order.volume_initial = volume
        if self.__backtesting:
            time_ = self.__data[symbol][SymbolsListener.get_by_id(listener).get_time_frame()]['time'][0]
        else:
            time_ = time.time()
        order.time_setup = int(time_)
        order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
        return self.send_order(order)

    # ----------------------------------------------------------------------
    def short(self, symbol, volume=1, price=None, stop=False, limit=False, strategy=None, listener=None):
        if self.__backtesting:
            time_ = self.__data[symbol][SymbolsListener.get_by_id(listener).get_time_frame()]['time'][0]
        else:
            time_ = time.time()
        position = self.__current_positions.get(symbol, None)
        if position and position.type > 0:
            order = Order(symbol, ORDER_TYPE_SELL, strategy, listener)
            order.volume_initial = position.volume
            order.time_setup = int(time_)
            order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
            # TODO 这里应该要支持事务性的下单操作
            self.send_order(order)
        if volume == 0:
            return
        order = Order(symbol, ORDER_TYPE_SELL, strategy, listener)
        order.volume_initial = volume
        order.time_setup = int(time_)
        order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
        return self.send_order(order)
