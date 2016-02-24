# -*- coding: utf-8 -*-

"""
Created on Wed Nov 25 21:09:47 2015

@author: BurdenBear
"""
import time
from functools import partial
from collections import defaultdict

# 自定义模块
from Bigfish.core import AccountManager
from Bigfish.event.event import *
from Bigfish.event.engine import EventEngine
from Bigfish.models.symbol import Forex
from Bigfish.models.trade import *
from Bigfish.utils.common import set_attr, get_attr
from Bigfish.models.common import Deque as deque
from Bigfish.utils.common import time_frame_to_seconds
from Bigfish.event.handle import SymbolsListener


# %% 策略引擎语句块
########################################################################
class StrategyEngine(object):
    """策略引擎"""
    CACHE_MAXLEN = 10000

    # ----------------------------------------------------------------------
    def __init__(self, is_backtest=False):
        """Constructor"""
        self.__event_engine = EventEngine()  # 事件处理引擎
        self.__account_manager = AccountManager()  # 账户管理
        self.__is_backtest = is_backtest  # 是否为回测
        self.__orders_done = {}  # 保存所有已处理报单数据的字典
        self.__orders_todo = {}  # 保存所有未处理报单（即挂单）数据的字典 key:id
        self.__orders_todo_index = {}  # 同上 key:symbol
        self.__symbol_pool = {}  # 保存交易物
        self.__deals = {}  # 保存所有成交数据的字典
        self.__positions = {}  # Key:id, value:position with responding id
        self.__current_positions = {}  # key：symbol，value：current position
        self.__strategys = {}  # 保存策略对象的字典,key为策略名称,value为策略对象
        self.__data = {}  # 统一的数据视图
        self.__max_len_info = {}  # key:(symbol,timeframe),value:maxlen
        self.start_time = None
        self.end_time = None
        self.__current_time = None  # 目前数据运行到的事件，用于计算回测进度

    start_time = property(partial(get_attr, attr='start_time'), partial(set_attr, attr='start_time'), None)
    end_time = property(partial(get_attr, attr='end_time'), partial(set_attr, attr='end_time'), None)

    # ----------------------------------------------------------------------
    def get_current_time(self):
        return self.__current_time

    # ----------------------------------------------------------------------
    def get_symbols(self):
        return self.__symbol_pool

    # ----------------------------------------------------------------------
    def get_symbol_timeframe(self):
        return self.__max_len_info.keys()

    # ----------------------------------------------------------------------
    def get_current_contracts(self):
        # TODO 现在持仓手数
        return self.__current_positions

    # ----------------------------------------------------------------------
    def get_current_positions(self):
        # TODO 读取每个品种的有效Position
        return self.__current_positions

    # ----------------------------------------------------------------------
    def get_deals(self):
        return self.__deals

    # ----------------------------------------------------------------------
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
    def set_capital_base(self, base):
        self.__account_manager.set_capital_base(base)

    # ----------------------------------------------------------------------
    def add_symbols(self, symbols, time_frame, max_length=0):
        for symbol in symbols:
            if (symbol, time_frame) not in self.__max_len_info:
                self.__max_len_info[(symbol, time_frame)] = max_length
            else:
                self.__max_len_info[(symbol, time_frame)] = max(max_length, self.__max_len_info[(symbol, time_frame)])
            self.register_event(EVENT_BAR_SYMBOL[symbol][time_frame], self.update_bar_data)
            # TODO 从全局的品种池中查询
            self.__symbol_pool[symbol] = Forex(symbol, symbol)

    # ----------------------------------------------------------------------
    def initialize(self):

        self.__current_time = None
        for (symbol, time_frame), maxlen in self.__max_len_info.items():
            if time_frame not in self.__data:
                self.__data[time_frame] = defaultdict(dict)
            if maxlen == 0:
                maxlen = self.CACHE_MAXLEN
            for field in ['open', 'high', 'low', 'close', 'time', 'volume']:
                self.__data[time_frame][field][symbol] = deque(maxlen=maxlen)
            if symbol not in self.__current_positions:
                position = Position(symbol)
                self.__current_positions[symbol] = position
                self.__positions[position.get_id()] = position

    # ----------------------------------------------------------------------
    def _recycle(self):
        # TODO 数据结构还需修改
        self.__data.clear()
        self.__deals.clear()
        self.__positions.clear()
        self.__current_positions.clear()
        # TODO 这里的auto_inc是模块级别的，需要修改成对象级别的。
        Deal.set_auto_inc(0)
        Position.set_auto_inc(0)
        deque.set_auto_inc(0)

    # ----------------------------------------------------------------------
    def add_file(self, file):
        self.__event_engine.add_file(file)

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
        self.__current_time = bar.close_time if not self.__current_time else max(self.__current_time, bar.close_time)
        for field in ['open', 'high', 'low', 'close', 'time', 'volume']:
            self.__data[time_frame][field][symbol].appendleft(getattr(bar, field))
        for order in self.__orders_todo:
            if bar.symbol == bar.symbol:
                result = self.__send_order_to_broker(order)
                self.__orders_done[order.get_id()] = order
                self.__update_position(*result[0])

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
                return 0
            elif num > 0:
                return 1
            else:
                return -1

        if deal.volume == 0:    return
        symbol = self.__symbol_pool[deal.symbol]
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
            if deal.symbol.endswith('USD'):  # 间接报价
                base_price = 1
            elif deal.symbol.startswith('USD'):  # 直接报价
                base_price = 1 / deal.price
            else:  # TODO 处理交叉盘的情况
                base_price = 1
            contracts = position_prev.volume - deal.volume
            position_now.volume = abs(contracts)
            position_now.type = position * sign(contracts)
            if (position_now.type == position) | (position_now.type == 0):
                # close or underweight position
                deal.entry = DEAL_ENTRY_OUT
                deal.profit = symbol.lot_value((deal.price - position_prev.price_current) * position, deal.volume,
                                               base_price=base_price)
                if position_now.type == 0:  # 防止浮点数精度可能引起的问题
                    position_now.price_current = 0
                    position_now.volume = 0
                else:
                    position_now.price_current = position_prev.price_current
                position_now.time_open = position_prev.time_open
                position_now.time_open_msc = position_prev.time_open_msc
                # XXX 反向开仓将被拆为两单
                """
            elif position_now.type != position:  # reverse position
                    deal.entry = DEAL_ENTRY_INOUT
                deal.profit = (deal.price - position_prev.price_current) * position * position_prev.volume
                position_now.price_current = deal.price
                position_now.time_open = deal.time
                position_now.time_open_msc = deal.time_msc
                position_now.price_open = position_now.price_current
                """
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
        if self.__is_backtest:
            time_frame = SymbolsListener.get_by_id(order.handle).get_time_frame()
            time_ = self.__data[time_frame]["time"][order.symbol][0] + time_frame_to_seconds(time_frame)
            order.time_done = int(time_)
            order.time_done_msc = int((time_ - int(time_)) * (10 ** 6))
            order.volume_current = order.volume_initial
            deal = Deal(order.symbol, order.strategy, order.handle)
            deal.volume = order.volume_current
            deal.time = order.time_done
            deal.time_msc = order.time_done_msc
            deal.type = 1 - ((order.type & 1) << 1)  # 参见ENUM_ORDER_TYPE和ENUM_DEAL_TYPE的定义
            deal.price = self.__data[time_frame]["close"][order.symbol][0]
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
                # send_order_to_broker = async_handle(self.__event_engine, self.__update_position)
                # (self.__send_order_to_broker)
                # send_order_to_broker(order)
                result = self.__send_order_to_broker(order)
                self.__orders_done[order.get_id()] = order
                self.__update_position(*result[0])
            else:
                self.__orders_todo[order.get_id()] = order
            return order.get_id()
        else:
            return -1

    # ----------------------------------------------------------------------
    def cancel_order(self, order_id):
        """
        撤单
        :param order_id: 所要取消的订单ID，为0时为取消所有订单
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
        self._recycle()  # 释放资源

    def wait(self, call_back=None, *args, **kwargs):
        """等待所有事件处理完毕
        :param call_back: 运行完成时的回调函数
        """
        self.__event_engine.wait()
        result = call_back(*args, **kwargs)
        self.stop()
        return result

    # TODO 对限价单的支持
    # ----------------------------------------------------------------------
    def close_position(self, symbol, volume=1, price=None, stop=False, limit=False, strategy=None, listener=None,
                       direction=0):
        """
        平仓下单指令
        :param symbol: 品种
        :param volume: 手数
        :param price: 限价单价格阈值
        :param stop: 是否为止损单
        :param limit: 是否为止盈单
        :param strategy: 发出下单指令的策略
        :param listener: 发出下单指令的信号
        :param direction: 下单指令的方向(多头或者空头)
        :return: 如果为0，表示下单失败，否则返回所下订单的ID
        """
        if volume == 0 or not direction:  # direction 对应多空头，1为多头，-1为空头
            return -1
        position = self.__current_positions.get(symbol, None)
        if not position or position.type != direction:
            return -1
        order_type = (direction + 1) >> 1  # 平仓，多头时order_type为1(ORDER_TYPE_SELL), 空头时order_type为0(ORDER_TYPE_BUY)
        order = Order(symbol, order_type, strategy, listener)
        order.volume_initial = volume
        if self.__is_backtest:
            time_ = self.__data[SymbolsListener.get_by_id(listener).get_time_frame()]['time'][symbol][0]
        else:
            time_ = time.time()
        order.time_setup = int(time_)
        order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
        return self.send_order(order)

    # ----------------------------------------------------------------------
    def open_position(self, symbol, volume=1, price=None, stop=False, limit=False, strategy=None, listener=None,
                      direction=0):
        """
        开仓下单指令
        :param symbol: 品种
        :param volume: 手数
        :param price: 限价单价格阈值
        :param stop: 是否为止损单
        :param limit: 是否为止盈单
        :param strategy: 发出下单指令的策略
        :param listener: 发出下单指令的信号
        :param direction: 下单指令的方向(多头或者空头)
        :return: 如果为0，表示下单失败，否则返回所下订单的ID
        """

        if self.__is_backtest:
            time_ = self.__data[SymbolsListener.get_by_id(listener).get_time_frame()]['time'][symbol][0]
        else:
            time_ = time.time()
        position = self.__current_positions.get(symbol, None)
        order_type = (1 - direction) >> 1  # 开仓，空头时order_type为1(ORDER_TYPE_SELL), 多头时order_type为0(ORDER_TYPE_BUY)
        if position and position.type < 0:
            order = Order(symbol, order_type, strategy, listener)
            order.volume_initial = position.volume
            order.time_setup = int(time_)
            order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
            # TODO 这里应该要支持事务性的下单操作
            self.send_order(order)
        if volume == 0:
            return -1
        order = Order(symbol, order_type, strategy, listener)
        order.volume_initial = volume
        order.time_setup = int(time_)
        order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
        return self.send_order(order)
