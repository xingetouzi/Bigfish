# -*- coding: utf-8 -*-

"""
Created on Wed Nov 25 21:09:47 2015

@author: BurdenBear
"""
import time
from collections import defaultdict
from weakref import proxy

# 自定义模块
from Bigfish.core import AccountManager
from Bigfish.event.event import *
from Bigfish.event.engine import EventEngine
from Bigfish.models.symbol import Forex
from Bigfish.models.trade import *
from Bigfish.models.common import Deque as deque
from Bigfish.utils.common import tf2s


# %% 策略引擎语句块
########################################################################
class StrategyEngine(object):
    """策略引擎"""
    CACHE_MAXLEN = 10000

    # ----------------------------------------------------------------------
    def __init__(self, is_backtest=False, **config):
        """Constructor"""
        self.__config = config
        self.__event_engine = EventEngine()  # 事件处理引擎
        self.__account_manager = AccountManager(self, **config)  # 账户管理
        self.__trade_manager = TradeManager(self, is_backtest, **config)  # 交易管理器
        self.__data_cache = DataCache(self)  # 数据中继站
        self.__strategys = {}  # 策略管理器

    def get_data(self):
        return self.__data_cache.data

    def get_symbol_pool(self):
        return self.__data_cache.symbol_pool

    def get_current_positions(self):
        return self.__trade_manager.current_positions

    def get_current_time(self):
        return self.__data_cache.current_time

    def get_positions(self):
        return self.__trade_manager.positions

    def get_deals(self):
        return self.__trade_manager.deals

    def get_strategys(self):
        return self.__strategys

    def get_profit_records(self):
        """获取平仓收益记录"""
        return self.__account_manager.get_profit_records()

    def get_symbol_timeframe(self):
        return self.__data_cache.get_cache_info().keys()

    # XXX之所以不用装饰器的方式是考虑到不知经过一层property会不会影响效率，所以保留用get_XXX直接访问
    # property:
    current_time = property(get_current_time)
    symbol_pool = property(get_symbol_pool)
    data = property(get_data)
    current_positions = property(get_current_positions)
    positions = property(get_positions)
    deal = property(get_deals)
    strategys = property(get_strategys)
    profit_records = property(get_profit_records)
    symbol_timeframe = property(get_symbol_timeframe)

    def get_base_price(self, code, time_frame):
        symbol = self.symbol_pool[code]
        if symbol.code.endswith('USD'):  # 间接报价
            base_price = 1
        elif symbol.code.startswith('USD'):  # 直接报价
            base = symbol.code[-3:]
            base_price = 1 / self.data[time_frame]['close']['USD' + base][0]
        else:
            base = symbol.code[-3:]
            if base + 'USD' in symbol.ALL.index:
                base_price = self.data[time_frame]['close'][base + 'USD'][0]
            elif 'USD' + base in symbol.ALL.index:
                base_price = 1 / self.data[time_frame]['close']['USD' + base][0]
            else:
                raise ValueError('找不到基准报价:%s' % base)
        return base_price

    def update_records(self, positions, time, time_frame=None):
        self.__account_manager.update_records(positions, time, time_frame=time_frame)

    def update_deal(self, deal):
        self.__account_manager.update_deal(deal)

    def open_position(self, *args, **kwargs):
        self.__trade_manager.open_position(*args, **kwargs)

    def close_position(self, *args, **kwargs):
        self.__trade_manager.close_position(*args, **kwargs)

    def set_capital_base(self, base):
        self.__account_manager.set_capital_base(base)

    # ----------------------------------------------------------------------
    def add_cache_info(self, *args, **kwargs):
        self.__data_cache.add_cache_info(*args, **kwargs)
        # TODO 从全局的品种池中查询

    # ----------------------------------------------------------------------
    def add_file(self, file):
        self.__event_engine.add_file(file)

    # ----------------------------------------------------------------------
    def add_strategy(self, strategy):
        """添加已创建的策略实例"""
        self.__strategys[strategy.get_id()] = strategy
        strategy.engine = self

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
    def write_log(self, log):
        """写日志"""
        self.__event_engine.put(Event(type=EVENT_LOG, log=log))

    # ----------------------------------------------------------------------
    def start(self):
        """启动所有策略"""
        for strategy in self.__strategys.values():
            strategy.start()
        self.__data_cache.start()
        self.__trade_manager.init()
        self.__event_engine.start()
        self.__account_manager.initialize()

    # ----------------------------------------------------------------------

    def stop(self):
        """停止所有策略"""
        self.__event_engine.stop()
        self.__data_cache.stop()
        for strategy in self.__strategys.values():
            strategy.stop()
        self._recycle()  # 释放资源

    # ----------------------------------------------------------------------

    def _recycle(self):
        self.__data_cache.stop()
        self.__trade_manager.recycle()
        # self.__account_manager.initialize()

    def wait(self, call_back=None, finished=True, *args, **kwargs):
        """等待所有事件处理完毕
        :param call_back: 运行完成时的回调函数
        :param finish: 向下兼容，finish为True时，事件队列处理完成时结束整个回测引擎；为False时只是调用回调函数，继续挂起回测引擎。
        """
        self.__event_engine.wait()
        result = call_back(*args, **kwargs)
        if finished:
            self.stop()
        return result


class DataCache:
    """数据缓存器"""
    CACHE_MAXLEN = 1000  # 默认的缓存长度

    @classmethod
    def set_default_maxlen(cls, maxlen):
        cls.CACHE_MAXLEN = maxlen

    def __init__(self, engine):
        self._cache_info = defaultdict(int)  # 需要拉取和缓存哪些品种和时间尺度的数据，字典，key:(symbol, timeframe)，value:(maxlen)
        self._engine = proxy(engine)  # 避免循环引用
        self._running = False
        self._data = {}
        self._symbol_pool = {}
        self.current_time = None  # 目前数据运行到的时间，用于计算回测进度
        self._min_time_frame = None
        self._count = 0

    def get_min_time_frame(self):
        return self._min_time_frame

    def set_min_time_frame(self, time_frame):
        if not self._min_time_frame or tf2s(time_frame) < tf2s(self._min_time_frame):
            self._min_time_frame = time_frame

    def get_data(self):
        return self._data

    def get_symbol_pool(self):
        return self._symbol_pool

    # TODO 根据总回测时间区间去计算浮动收益的统计频率
    @property
    def float_pnl_frequency(self):
        if self.min_time_frame in ['M1', 'M5']:
            return 1
        time = tf2s(self.min_time_frame)
        result = 2 * 60 * 60 // time  # 统计频率为2H一次
        if result == 0:
            return 1
        else:
            return result

    data = property(get_data)
    symbol_pool = property(get_symbol_pool)
    min_time_frame = property(get_min_time_frame, set_min_time_frame)

    def add_cache_info(self, symbols, time_frame, maxlen=0):
        symbols = set(symbols)
        symbols_ = symbols.copy()
        for symbol in symbols:
            if not (symbol.startswith('USD') or symbol.endswith('USD')):
                if symbol[-3:] + 'USD' in Forex.ALL.index:
                    symbols_.add(symbol[-3:] + 'USD')
                elif 'USD' + symbol[-3:] in Forex.ALL.index:
                    symbols_.add('USD' + symbol[-3:])
        for symbol in symbols_:
            key = (symbol, time_frame)
            self.min_time_frame = time_frame
            self._cache_info[key] = max(self._cache_info[key], maxlen)
        self._symbol_pool.update(
            {symbol: Forex(symbol) for symbol in symbols_ if symbol not in self._symbol_pool})

    def get_cache_info(self):
        return self._cache_info.copy()

    def init(self):
        for key, maxlen in self._cache_info.items():
            symbol, timeframe = key
            if timeframe not in self._data:
                self._data[timeframe] = defaultdict(dict)
            if maxlen == 0:
                maxlen = self.CACHE_MAXLEN
            for field in ['open', 'high', 'low', 'close', 'datetime', 'timestamp', 'volume']:
                self._data[timeframe][field][symbol] = deque(maxlen=maxlen)
            self._engine.register_event(EVENT_SYMBOL_BAR_RAW[symbol][timeframe], self.on_bar)
            # TODO 这里只考虑了单品种情况
            self._engine.register_event(EVENT_SYMBOL_BAR_COMPLETED[symbol][timeframe], self.on_next_bar)
        self._count = 0

    def start(self):
        self.init()
        self._running = True

    def stop(self):
        self._running = False
        self._data.clear()

    def on_bar(self, event):
        if self._running:
            bar = event.content['data']
            symbol = bar.symbol
            time_frame = bar.time_frame
            self.current_time = bar.close_time if not self.current_time else max(self.current_time, bar.close_time)
            last_time = self._data[time_frame]['timestamp'][symbol][0] \
                if self._data[time_frame]['timestamp'][symbol] else 0
            if bar.timestamp - last_time >= tf2s(time_frame):  # 当last_time = 0时，该条件显然成立
                for field in ['open', 'high', 'low', 'close', 'datetime', 'timestamp', 'volume']:
                    self._data[time_frame][field][symbol].appendleft(getattr(bar, field))
                self._engine.put_event(Event(EVENT_SYMBOL_BAR_COMPLETED[symbol][time_frame]))
            else:
                for field in ['open', 'high', 'low', 'close', 'datetime', 'timestamp', 'volume']:
                    self._data[time_frame][field][symbol][0] = getattr(bar, field)
                self._engine.put_event(Event(EVENT_SYMBOL_BAR_UPDATE[symbol][time_frame]))

    def on_next_bar(self, event):
        self._count += 1
        if self._count % self.float_pnl_frequency == 0:
            self._engine.update_records(self._engine.get_current_positions(), self.current_time)


class TradeManager:
    """负责保存交易信息，管理订单相关事件"""

    def __init__(self, engine, is_backtest=True, **config):
        self.engine = proxy(engine)
        self.__is_backtest = is_backtest  # 是否为回测
        self.__config = config
        self.__position_factory = PositionFactory()
        self.__order_factory = OrderFactory()
        self.__deal_factory = DealFactory()
        self.__orders_done = {}  # 保存所有已处理报单数据的字典
        self.__orders_todo = {}  # 保存所有未处理报单（即挂单）数据的字典 key:id
        self.__orders_todo_index = {}  # 同上 key:symbol
        self.__positions = {}  # Key:id, value:position with responding id
        self.__current_positions = {}  # key：symbol，value：current position
        self.__deals = {}  # key:id, value:deal with responding id

    def get_current_positions(self):
        return self.__current_positions

    def get_positions(self):
        return self.__positions

    def get_deals(self):
        return self.__deals

    current_positions = property(get_current_positions)
    positions = property(get_positions)
    deals = property(get_deals)

    def init(self):
        for symbol, _ in self.engine.symbol_pool.items():
            if symbol not in self.__current_positions:
                position = self.__position_factory(symbol)
                self.__current_positions[symbol] = position
                self.__positions[position.get_id()] = position

    def recycle(self):
        # TODO 数据结构还需修改
        self.__orders_done.clear()
        self.__orders_todo.clear()
        self.__orders_todo_index.clear()
        self.__deals.clear()
        self.__positions.clear()
        self.__current_positions.clear()
        self.__position_factory.reset()
        self.__deal_factory.reset()
        self.__order_factory.reset()

    @staticmethod
    def check_order(order):
        if not isinstance(order, Order):
            return False
        # TODO更多关于订单合法性的检查
        return True

    # ----------------------------------------------------------------------
    def __send_order_to_broker(self, order):
        if self.__is_backtest:
            time_frame = self.engine.strategys[order.strategy].signals[order.signal].get_time_frame()
            time_ = self.engine.data[time_frame]["timestamp"][order.symbol][0] + tf2s(time_frame)
            order.time_done = int(time_)
            order.time_done_msc = int((time_ - int(time_)) * (10 ** 6))
            order.volume_current = order.volume_initial
            deal = self.__deal_factory(order.symbol, order.strategy, order.signal)
            deal.volume = order.volume_current
            deal.time = order.time_done
            deal.time_msc = order.time_done_msc
            deal.type = 1 - ((order.type & 1) << 1)  # 参见ENUM_ORDER_TYPE和ENUM_DEAL_TYPE的定义
            deal.price = self.engine.data[time_frame]["close"][order.symbol][0]
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
                result[0].clear()  # 去掉对deal的引用
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
            self.__orders_todo.clear()
        else:
            if order_id in self.__orders_todo:
                del (self.__orders_todo[order_id])

    def __update_position(self, deal):
        def sign(num):
            if abs(num) <= 10 ** -7:
                return 0
            elif num > 0:
                return 1
            else:
                return -1

        if deal.volume == 0:
            return
        symbol = self.engine.symbol_pool[deal.symbol]
        position_prev = self.__current_positions[deal.symbol]
        position_now = self.__position_factory(deal.symbol, deal.strategy, deal.signal)
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
            time_frame = self.engine.strategys[deal.strategy].signals[deal.signal].time_frame
            base_price = self.engine.get_base_price(deal.symbol, time_frame)
            contracts = position_prev.volume - deal.volume
            position_now.volume = abs(contracts)
            position_now.type = position * sign(contracts)
            if (position_now.type == position) | (position_now.type == 0):
                # close or underweight position
                deal.entry = DEAL_ENTRY_OUT
                deal.profit = symbol.lot_value((deal.price - position_prev.price_current) * position, deal.volume,
                                               commission=self.__config['commission'],
                                               slippage=self.__config['slippage'], base_price=base_price)
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
            self.engine.update_deal(deal)

    # ----------------------------------------------------------------------
    def close_position(self, symbol, volume=1, price=None, stop=False, limit=False, strategy=None, signal=None,
                       direction=0):
        """
        平仓下单指令
        :param symbol: 品种
        :param volume: 手数
        :param price: 限价单价格阈值
        :param stop: 是否为止损单
        :param limit: 是否为止盈单
        :param strategy: 发出下单指令的策略
        :param signal: 发出下单指令的信号
        :param direction: 下单指令的方向(多头或者空头)
        :return: 如果为0，表示下单失败，否则返回所下订单的ID
        """
        if volume == 0 or not direction:  # direction 对应多空头，1为多头，-1为空头
            return -1
        position = self.__current_positions.get(symbol, None)
        if not position or position.type != direction:
            return -1
        order_type = (direction + 1) >> 1  # 平仓，多头时order_type为1(ORDER_TYPE_SELL), 空头时order_type为0(ORDER_TYPE_BUY)
        order = self.__order_factory(symbol, order_type, strategy, signal)
        order.volume_initial = volume
        if self.__is_backtest:
            time_frame = self.engine.strategys[strategy].signals[signal].time_frame
            time_ = self.engine.data[time_frame]['timestamp'][symbol][0]
        else:
            time_ = time.time()
        order.time_setup = int(time_)
        order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
        return self.send_order(order)

    # ----------------------------------------------------------------------
    def open_position(self, symbol, volume=1, price=None, stop=False, limit=False, strategy=None, signal=None,
                      direction=0):
        """
        开仓下单指令
        :param symbol: 品种
        :param volume: 手数
        :param price: 限价单价格阈值
        :param stop: 是否为止损单
        :param limit: 是否为止盈单
        :param strategy: 发出下单指令的策略
        :param signal: 发出下单指令的信号
        :param direction: 下单指令的方向(多头或者空头)
        :return: 如果为0，表示下单失败，否则返回所下订单的ID
        """

        if self.__is_backtest:
            time_frame = self.engine.strategys[strategy].signals[signal].get_time_frame()
            time_ = self.engine.data[time_frame]['timestamp'][symbol][0]
        else:
            time_ = time.time()
        position = self.__current_positions.get(symbol, None)
        order_type = (1 - direction) >> 1  # 开仓，空头时order_type为1(ORDER_TYPE_SELL), 多头时order_type为0(ORDER_TYPE_BUY)
        if position and position.type != direction:
            order = self.__order_factory(symbol, order_type, strategy, signal)
            order.volume_initial = position.volume
            order.time_setup = int(time_)
            order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
            # TODO 这里应该要支持事务性的下单操作
            self.send_order(order)
        if volume == 0:
            return -1
        order = self.__order_factory(symbol, order_type, strategy, signal)
        order.volume_initial = volume
        order.time_setup = int(time_)
        order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
        return self.send_order(order)
