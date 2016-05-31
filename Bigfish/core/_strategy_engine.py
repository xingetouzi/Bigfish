import time
from collections import defaultdict
from functools import partial
from queue import PriorityQueue
from weakref import proxy
from dateutil.parser import parse
from Bigfish.core import BfAccountManager, FDTAccountManager, AccountManager
from Bigfish.data.mongo_utils import MongoUser
from Bigfish.event.engine import EventEngine
from Bigfish.event.event import EVENT_SYMBOL_TICK_RAW, EVENT_SYMBOL_BAR_RAW, EVENT_SYMBOL_BAR_UPDATE, \
    EVENT_SYMBOL_BAR_COMPLETED, Event, EVENT_LOG
from Bigfish.models.base import Runnable, RunningMode, TradingMode
from Bigfish.models.common import Deque as deque
from Bigfish.models.config import ConfigInterface
from Bigfish.models.enviroment import APIInterface, Globals
from Bigfish.models.quote import Bar
from Bigfish.models.symbol import Forex
from Bigfish.models.trade import *
from Bigfish.utils.common import tf2s
from Bigfish.utils.log import LoggerInterface


class CacheInfo:
    """
    用于记录行情数据品种，书简尺度，缓存最大长度等信息的对象
    """
    CACHE_MAXLEN = 1000  # 默认的缓存长度

    def __init__(self, symbol, time_frame, length=None):
        self.__symbol = symbol
        self.__time_frame = time_frame
        self.length = length if length is not None else self.CACHE_MAXLEN

    @property
    def symbol(self):
        return self.__symbol

    @property
    def time_frame(self):
        return self.__time_frame

    @property
    def key(self):
        return self.symbol, self.time_frame


class QuotationData:
    """
    行情数据
    """

    def __init__(self, cache_info):
        self.info = cache_info
        self.open = deque(maxlen=self.info.length)
        self.high = deque(maxlen=self.info.length)
        self.low = deque(maxlen=self.info.length)
        self.close = deque(maxlen=self.info.length)
        self.volume = deque(maxlen=self.info.length)
        self.datetime = deque(maxlen=self.info.length)
        self.timestamp = deque(maxlen=self.info.length)
        self.tick_open = None


class QuotationDataView:
    def __init__(self):
        self.__info = {}
        self.__data = {}

    def get_keys(self):
        return self.__data.keys()

    def set(self, cache_info):
        self.__info[cache_info.key] = cache_info

    def update(self, cache_info):
        if self.__info.get(cache_info.key, None) is None or cache_info.length > self.__info[cache_info.key].length:
            self.__info[cache_info.key] = cache_info

    def create(self, symbol, time_frame):
        if self.__info.get((symbol, time_frame), None) is not None:
            self.__data[(symbol, time_frame)] = QuotationData(self.__info[(symbol, time_frame)])

    def find(self, symbol, time_frame) -> QuotationData:
        try:
            return self.__data[(symbol, time_frame)]
        except KeyError:
            raise KeyError("找不到报价数据:(%s, %s)" % (symbol, time_frame))

    def create_all(self):
        for symbol, time_frame in self.__info.keys():
            self.create(symbol, time_frame)

    def clear(self):
        self.__data.clear()
        self.__info.clear()


class QuotationManager(LoggerInterface, Runnable, ConfigInterface, APIInterface):
    TICK_INTERVAL = 10  # Tick数据推送间隔

    def __init__(self, engine, parent=None):
        LoggerInterface.__init__(self)
        Runnable.__init__(self)
        APIInterface.__init__(self)
        ConfigInterface.__init__(self, parent=parent)
        self._engine = proxy(engine)  # 避免循环引用
        self._tick_cache = {}
        self._running = False
        self._data_view = QuotationDataView()
        self._symbol_pool = {}
        self.current_time = None  # 目前数据运行到的时间，用于计算回测进度
        self._min_time_frame = None
        self._count = 0

    @property
    def min_time_frame(self):
        return self._min_time_frame

    @min_time_frame.setter
    def min_time_frame(self, time_frame):
        if not self._min_time_frame or tf2s(time_frame) < tf2s(self._min_time_frame):
            self._min_time_frame = time_frame

    @property
    def symbol_pool(self):
        return self._symbol_pool

    # TODO 根据总回测时间区间去计算浮动收益的统计频率
    @property
    def float_pnl_frequency(self):
        if self.config.running_mode == RunningMode.runtime:
            return 1
        if self.min_time_frame in ['M1', 'M5']:
            return 1
        time = tf2s(self.min_time_frame)
        result = 2 * 60 * 60 // time  # 统计频率为2H一次
        if result == 0:
            return 1
        else:
            return result

    def find_quotation(self, symbol, time_frame):
        return self._data_view.find(symbol, time_frame)

    def get_counter_price(self, code, time_frame):
        """
        计算当前对应货币对的报价货币(counter currency)兑美元的价格
        :param code: 品种代码
        :param time_frame: 时间尺度
        :return: 当前对应货币对的报价货币(counter currency)兑美元的价格
        """
        symbol = self.symbol_pool[code]
        if symbol.code.endswith('USD'):  # 间接报价
            base_price = 1
        elif symbol.code.startswith('USD'):  # 直接报价
            base = symbol.code[-3:]
            base_price = 1 / self.get_strike_price('USD' + base, time_frame)
        else:  # 交叉盘
            base = symbol.code[-3:]
            if base + 'USD' in symbol.ALL.index:
                base_price = self.get_strike_price(base + 'USD', time_frame)
            elif 'USD' + base in symbol.ALL.index:
                base_price = self.get_strike_price('USD' + base, time_frame)
            else:
                raise ValueError('找不到基准报价:%s' % base)
        return base_price

    def get_base_price(self, code, time_frame):
        """
        计算当前对应货币对的基准货币(base currency)兑美元的价格
        :param code: 品种代码
        :param time_frame: 时间尺度
        :return: 当前对应货币对的报价货币(base currency)兑美元的价格
        """
        symbol = self._symbol_pool[code]
        if symbol.code.startswith('USD'):  # 间接报价
            base_price = 1
        elif symbol.code.endswith('USD'):  # 直接报价
            base = symbol.code[:3]
            base_price = self.get_strike_price(base + 'USD', time_frame)
        else:  # 交叉盘
            base = symbol.code[:3]
            if base + 'USD' in symbol.ALL.index:
                base_price = self.get_strike_price(base + 'USD', time_frame)
            elif 'USD' + base in symbol.ALL.index:
                base_price = 1 / self.get_strike_price('USD' + base, time_frame)
            else:
                raise ValueError('找不到基准报价:%s' % base)
        return base_price

    def get_strike_price(self, symbol, time_frame):
        quotation = self._data_view.find(symbol, time_frame)
        if self.config.trading_mode == TradingMode.on_tick:
            return quotation.tick_open  # 以next tick open 成交
        else:
            return quotation.open[0]

    def add_cache_info(self, symbols, time_frame, length=None):
        symbols = set(symbols)
        symbols_ = symbols.copy()
        for symbol in symbols:
            if not (symbol.startswith('USD') or symbol.endswith('USD')):
                if symbol[-3:] + 'USD' in Forex.ALL.index:
                    symbols_.add(symbol[-3:] + 'USD')
                elif 'USD' + symbol[-3:] in Forex.ALL.index:
                    symbols_.add('USD' + symbol[-3:])
        for symbol in symbols_:
            self.min_time_frame = time_frame
            self._data_view.update(CacheInfo(symbol, time_frame, length))
        self._symbol_pool.update(
            {symbol: Forex(symbol) for symbol in symbols_ if symbol not in self._symbol_pool})

    def init(self):
        self._data_view.create_all()
        for symbol, time_frame in self._data_view.get_keys():
            if self.config.running_mode == RunningMode.runtime:
                self._engine.register_event(EVENT_SYMBOL_TICK_RAW[symbol], self.on_tick)
            elif self.config.running_mode == RunningMode.backtest:
                self._engine.register_event(EVENT_SYMBOL_BAR_RAW[symbol][time_frame], self.on_bar)
            elif self.config.running_mode == RunningMode.traceback:
                self._engine.register_event(EVENT_SYMBOL_TICK_RAW[symbol], self.on_tick)
                self._engine.register_event(EVENT_SYMBOL_BAR_RAW[symbol][time_frame], self.on_bar)
            # TODO 这里只考虑了单品种情况
            if self.config.trading_mode == TradingMode.on_tick:
                self._engine.register_event(EVENT_SYMBOL_BAR_UPDATE[symbol][time_frame], self.on_next_bar)
            self._engine.register_event(EVENT_SYMBOL_BAR_COMPLETED[symbol][time_frame], self.on_next_bar)
        self._count = 0

    def _start(self):
        self.init()

    def _stop(self):
        self._data_view.clear()

    def update_bar(self, bar: Bar):
        symbol = bar.symbol
        time_frame = bar.time_frame
        quotation = self._data_view.find(symbol, time_frame)
        self.current_time = bar.close_time if not self.current_time else max(self.current_time, bar.close_time)
        last_time = quotation.timestamp[0] if quotation.timestamp else 0
        if self.config.trading_mode == TradingMode.on_tick:
            quotation.tick_open = bar.open
        if bar.timestamp - last_time >= tf2s(time_frame):  # 当last_time = 0时，该条件显然成立
            for field in ['open', 'high', 'low', 'close', 'datetime', 'timestamp', 'volume']:
                getattr(quotation, field).appendleft(getattr(bar, field))
            self._engine.put_event(Event(EVENT_SYMBOL_BAR_COMPLETED[symbol][time_frame]))
        else:
            quotation.high[0] = max(quotation.high[0], bar.high)
            quotation.low[0] = min(quotation.low[0], bar.low)
            quotation.volume[0] += bar.volume
            for field in ["datetime", "timestamp", "close"]:
                getattr(quotation, field)[0] = getattr(bar, field)
            self._engine.put_event(Event(EVENT_SYMBOL_BAR_UPDATE[symbol][time_frame]))

    def on_bar(self, event: Event):
        if self._running:
            bar = event.content['data']
            self.update_bar(bar)

    def on_tick(self, event: Event):
        if self._running:
            tick = event.content['data']
            symbol = tick.symbol
            for time_frame in {item[1] for item in self._data_view.get_keys() if item[0] == symbol}:
                bar_interval = tf2s(time_frame)
                if symbol not in self._tick_cache:
                    self._tick_cache[symbol] = {}
                if time_frame not in self._tick_cache[symbol]:
                    self._tick_cache[symbol][time_frame] = {
                        'open': tick.openPrice, 'high': tick.highPrice,
                        'low': tick.lastPrice, 'close': tick.lastPrice,
                        'volume': tick.volume, 'timestamp': tick.time // self.TICK_INTERVAL * self.TICK_INTERVAL,
                    }
                else:
                    dict_ = self._tick_cache[symbol][time_frame]
                    if tick.time - dict_['timestamp'] >= self.TICK_INTERVAL:  # bar_interval 能被TICK_INTERVAL整除
                        bar = Bar(symbol)
                        bar.time_frame = time_frame
                        bar.timestamp = dict_['timestamp'] // bar_interval * bar_interval
                        bar.open = dict_['open']
                        bar.high = dict_['high']
                        bar.low = dict_['low']
                        bar.close = dict_['close']
                        self.update_bar(bar)
                        dict_["open"] = tick.openPrice
                        dict_["high"] = tick.highPrice
                        dict_["low"] = tick.lowPrice
                        dict_["close"] = tick.lastPrice
                        dict_["volume"] = tick.volume
                        dict_["timestamp"] = tick.time // self.TICK_INTERVAL * self.TICK_INTERVAL
                    else:
                        dict_['low'] = min(dict_['low'], tick.lowPrice)
                        dict_['high'] = max(dict_['high'], tick.highPrice)
                        dict_['close'] = tick.lastPrice
                        dict_["volume"] += tick.volume
                        dict_['timestamp'] = tick.time // self.TICK_INTERVAL * self.TICK_INTERVAL

    def on_next_bar(self, event: Event):
        # 更新浮动盈亏
        self._count += 1
        if self._count % self.float_pnl_frequency == 0:
            if self.config.running_mode == RunningMode.backtest:
                pnl = self._engine.profit_record(self.current_time)
                self._engine.profit_records.append(pnl)
            else:
                pnl = self._engine.profit_record()
                self._engine.mongo_user.collection['PnLs'].insert_one(pnl)
        self._engine.realize_order()

    def get_APIs(self, symbols=None, time_frame=None) -> Globals:
        def capitalize(s: str) -> str:
            return s[0].upper() + s[1:]

        APIs = Globals({}, {})
        if symbols and time_frame:
            for field in ["open", "high", "low", "close", "volume", "timestamp", "datetime"]:
                APIs.const[capitalize(field) + 's'] = {}
                for symbol in symbols:
                    APIs.const[capitalize(field) + 's'][symbol] = getattr(self._data_view.find(symbol, time_frame),
                                                                          field)
                APIs.const[capitalize(field)] = getattr(self._data_view.find(symbols[0], time_frame), field)
                APIs.const[field[0].upper()] = getattr(self._data_view.find(symbols[0], time_frame), field)
        APIs.const["Points"] = {symbol: self._symbol_pool[symbol].point for symbol in symbols}
        APIs.const["Point"] = self._symbol_pool[symbols[0]].point
        return APIs


########################################################################################################################
class TradingDataFactory(ConfigInterface):
    def __init__(self, parent=None):
        ConfigInterface.__init__(self, parent=parent)
        if self.config.running_mode == RunningMode.backtest:
            self._position_factory = PositionFactory()
            self._order_factory = OrderFactory()
            self._deal_factory = DealFactory()
        else:
            # 暂时只用account当前缀，下单时间和策略，信号的信息有了，只有对应实盘账户信息没有
            prefix = '-'.join([self.config['account']])
            self._position_factory = PositionFactory(prefix + '-P', timestamp=True)
            self._order_factory = OrderFactory(prefix + '-O', timestamp=True)
            self._deal_factory = DealFactory(prefix + '-D', timestamp=True)

    def new_position(self, *args, **kwargs):
        return self._position_factory.new(*args, **kwargs)

    def new_order(self, *args, **kwargs):
        return self._order_factory.new(*args, **kwargs)

    def new_deal(self, *args, **kwargs):
        return self._deal_factory.new(*args, **kwargs)

    def find_position(self, id_):
        return self._position_factory.find(id_)

    def find_order(self, id_):
        return self._order_factory.find(id_)

    def find_deal(self, id_):
        return self._deal_factory.find(id_)

    @property
    def positions(self):
        return self._position_factory.map

    @property
    def deals(self):
        return self._deal_factory.map

    @property
    def orders(self):
        return self._order_factory.map

    def clear(self):
        self._position_factory.clear()
        self._deal_factory.clear()
        self._order_factory.clear()


class OrdersUr:
    def __init__(self):
        self.queue = defaultdict(PriorityQueue)  #
        self.flag = set()
        self.count = 0


class TradingManager(ConfigInterface, APIInterface, LoggerInterface):
    def __init__(self, engine, quotation_manager, account_manager, parent=None):
        APIInterface.__init__(self)
        LoggerInterface.__init__(self)
        ConfigInterface.__init__(self, parent=parent)
        self._engine = proxy(engine)
        self.__quotation_manager = proxy(quotation_manager)
        self.__account_manager = proxy(account_manager)
        self.__factory = TradingDataFactory(parent=self)
        self.__orders_ur = defaultdict(OrdersUr)  # orders unrealized 还未被处理的订单请求
        self.__orders_done = {}  # 保存所有已处理报单数据的字典
        self.__orders_todo = {}  # 保存所有未处理报单（即挂单）数据的字典 key:id
        self.__orders_todo_index = {}  # 同上 key:symbol
        self.__positions = {}  # Key:id, value:position with responding id
        self.__current_positions = {}  # key：symbol，value：current position
        self.max_margin = 0

    @property
    def current_positions(self):
        return self.__current_positions

    @property
    def positions(self):
        return self.__factory.positions

    @property
    def deals(self):
        return self.__factory.deals

    @property
    def float_pnl(self):
        symbol_pool = self.__quotation_manager.symbol_pool
        float_pnl = 0
        time_frame = self.config['time_frame']  # 应该是最小的事件尺度
        for symbol, position in self.__current_positions.items():
            quotation = self.__quotation_manager.find_quotation(symbol, time_frame)
            price = quotation.close[0]
            base_price = self.__quotation_manager.get_counter_price(symbol, time_frame)
            float_pnl += symbol_pool[symbol].lot_value((price - position.price_current) * position.type,
                                                       position.volume,
                                                       commission=self.config['commission'],
                                                       slippage=self.config['slippage'],
                                                       base_price=base_price)
        return float_pnl

    @property
    def margin(self):
        margin = 0
        symbol_pool = self.__quotation_manager.symbol_pool
        for symbol, positions in self.current_positions.items():
            if symbol.startswith('USD'):
                margin += positions.volume * 100000 / symbol_pool[symbol].leverage
            elif symbol.endswith('USD'):
                margin += positions.volume * 100000 * positions.price_current / symbol_pool[symbol].leverage
        return margin

    def init(self):
        for symbol in self.__quotation_manager.symbol_pool.keys():
            if symbol not in self.__current_positions:
                position = self.__factory.new_position(symbol)
                self.__current_positions[symbol] = position
        self.max_margin = 0

    def recycle(self):
        # TODO 数据结构还需修改
        self.__orders_done.clear()
        self.__orders_todo.clear()
        self.__orders_todo_index.clear()
        self.__current_positions.clear()
        self.__factory.clear()

    @staticmethod
    def check_order(order):
        if not isinstance(order, Order):
            return False
        # TODO更多关于订单合法性的检查
        return True

    def __send_order_to_broker(self, order):
        # if order.volume_initial == 0:
        # return
        if order.volume_initial <= 0:
            return -1
        if self.config.running_mode == RunningMode.backtest:
            time_frame = self._engine.strategys[order.strategy].signals[order.signal].time_frame
            position = self.__current_positions[order.symbol]
            symbol = self.__quotation_manager.symbol_pool[order.symbol]
            quotation = self.__quotation_manager.find_quotation(order.symbol, time_frame)
            volume = order.volume_initial
            margin = 0
            if position.type * (1 - (order.type << 1)) < 0:
                if symbol.code.startswith('USD'):  # 间接报价
                    base_price = 1
                elif symbol.code.endswith('USD'):  # 直接报价
                    base_price = position.price_current
                margin -= symbol.margin(min(position.volume, volume), commission=self.config.commission,
                                        base_price=base_price)
                volume -= position.volume
            if volume > 0:
                margin += symbol.margin(volume, commission=self.config.commission,
                                        base_price=self.__quotation_manager.get_base_price(order.symbol, time_frame))
            if self.__account_manager.capital_available - margin >= 0:
                time_ = quotation.timestamp[0]
                order.time_done = int(time_)
                order.time_done_msc = int((time_ - int(time_)) * (10 ** 6))
                order.volume_current = order.volume_initial
                deal = self.__factory.new_deal(order.symbol, order.strategy, order.signal)
                deal.volume = order.volume_current
                deal.time = order.time_done
                deal.time_msc = order.time_done_msc
                deal.type = 1 - ((order.type & 1) << 1)  # 参见ENUM_ORDER_TYPE和ENUM_DEAL_TYPE的定义
                deal.price = self.__quotation_manager.get_strike_price(order.symbol, time_frame)
                order.deal = deal.get_id()
                deal.order = order.get_id()
                order_id = order.get_id()
            else:
                print('下单失败,保证金不足')
                return -1
        else:
            cash_old = self.__account_manager.capital_cash
            order_id = self.__account_manager.send_order_to_broker(order)
            if order_id != -1:
                res = self.__account_manager.order_status()
                if res['ok']:
                    order_status = res.get('orders', [])
                    for state in order_status:
                        if state['id'] == order_id:
                            deal = self.__factory.new_deal(order.symbol, order.strategy, order.signal)
                            deal.type = 1 - ((order.type & 1) << 1)
                            deal.volume = round(state['quantity'] / 100000, 2)  # 换算成手，精确到mini手
                            deal.time = parse(state['created']).timestamp()
                            deal.price = state['avgPx']
                            deal.symbol = order.symbol
                            deal.order = order.get_id()
                            cash_now = self.__account_manager.capital_cash
                            deal.profit = cash_now - cash_old
                            break
        if order_id != -1:
            self.logger.info("编号<%s>下单成功,订单ID:%s" % (order.id, order_id))
            self.__update_position(deal)  # TODO 加入事件引擎，支持异步
            self.__orders_done[order.get_id()] = order
            return order.get_id()
        else:
            self.logger.info("编号<%s>下单失败,订单ID:%s" % (order.id, order_id))
            return -1

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
                return self.__send_order_to_broker(order)
            else:
                self.__orders_todo[order.get_id()] = order
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

        position_prev = self.__current_positions[deal.symbol]
        position_now = self.__factory.new_position(deal.symbol, deal.strategy, deal.signal)
        position_now.prev_id = position_prev.get_id()
        position_prev.next_id = position_now.get_id()
        if self.config.running_mode == RunningMode.backtest:
            symbol = self.__quotation_manager.symbol_pool[deal.symbol]
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
                time_frame = self._engine.strategys[deal.strategy].signals[deal.signal].time_frame
                base_price = self.__quotation_manager.get_counter_price(deal.symbol, time_frame)
                contracts = position_prev.volume - deal.volume
                position_now.volume = abs(contracts)
                position_now.type = position * sign(contracts)
                if (position_now.type == position) | (position_now.type == 0):
                    # close or underweight position
                    deal.entry = DEAL_ENTRY_OUT
                    deal.profit = symbol.lot_value((deal.price - position_prev.price_current) * position, deal.volume,
                                                   commission=self.config.commission,
                                                   slippage=self.config.slippage, base_price=base_price)
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
            if deal.profit is not None:
                self.__account_manager.capital_cash += deal.profit
        else:
            res = self.__account_manager.position_status(deal.symbol)
            if res is not None:
                qty = res['qty']
                price = res['price']
            else:
                qty = 0
                price = 0
            position_now.symbol = deal.symbol
            position_now.type = sign(qty)
            position_now.volume = round(abs(qty) / 100000, 2)  # 精确到迷你手
            position_now.price_current = price
            if position_prev.type * deal.type >= 0:
                deal.entry = DEAL_ENTRY_IN
            else:
                deal.entry = DEAL_ENTRY_OUT
            if position_now.type * position_prev.type >= 0:
                position_now.time_open = position_prev.time_open
                position_now.time_open_msc = position_prev.time_open_msc
                position_now.price_open = position_prev.price_open
            else:
                position_now.time_open = deal.time
                position_now.time_open_msc = deal.time_msc
                position_now.price_open = price
        position_now.time_update = deal.time
        position_now.time_update_msc = deal.time_msc
        deal.position = position_now.get_id()
        position_now.deal = deal.get_id()
        self.__current_positions[deal.symbol] = position_now
        if self.config.running_mode == RunningMode.backtest:
            self.max_margin = max(self.max_margin, self.__account_manager.capital_margin)
            pass
        else:
            self._engine.mongo_user.collection['positions'].insert_one(position_now.to_dict())
            self._engine.mongo_user.collection['deals'].insert_one(deal.to_dict())

    def realize_order(self):
        def get_order_info(orders_ur, direction):
            if orders_ur.queue[direction].empty():
                return None
            return orders_ur.queue[direction].get()

        def commit_order(direction, symbol, order_info):
            if direction == OrderDirection.long_entry:
                self.open_position(symbol, *order_info, direction=1)
            elif direction == OrderDirection.short_entry:
                self.open_position(symbol, *order_info, direction=-1)
            elif direction == OrderDirection.long_exit:
                self.close_position(symbol, *order_info, direction=1)
            elif direction == OrderDirection.short_exit:
                self.close_position(symbol, *order_info, direction=-1)

        def choose_from_two_direction(orders_ur, direction_a, direction_b):
            info_a = get_order_info(orders_ur, direction_a)
            info_b = get_order_info(orders_ur, direction_b)
            if info_a is None and info_b is None:
                return False
            elif info_a is None:
                commit_order(direction_b, symbol, info_b[3:])
            elif info_b is None:
                commit_order(direction_a, symbol, info_a[3:])
            elif info_a < info_b:
                commit_order(direction_a, symbol, info_a[3:])
                orders_ur.queue[direction_b].put(info_b)
            else:
                commit_order(direction_b, symbol, info_b[3:])
                orders_ur.queue[direction_a].put(info_a)
            return True

        # TODO 相同方向最多进场数
        for symbol, orders_ur in self.__orders_ur.items():
            while True:
                # TODO 同步仓位机制
                position = self.current_positions[symbol]
                if position.type == POSITION_TYPE_BUY:
                    info = get_order_info(orders_ur, OrderDirection.short_entry)
                    if info is not None:
                        commit_order(OrderDirection.short_entry, symbol, info[3:])
                    elif not choose_from_two_direction(orders_ur, OrderDirection.long_entry, OrderDirection.long_exit):
                        break
                elif position.type == POSITION_TYPE_SELL:
                    info = get_order_info(orders_ur, OrderDirection.long_entry)
                    if info is not None:
                        commit_order(OrderDirection.long_entry, symbol, info[3:])
                    elif not choose_from_two_direction(orders_ur, OrderDirection.short_entry,
                                                       OrderDirection.short_exit):
                        break
                elif position.type == POSITION_TYPE_NONE:
                    if not choose_from_two_direction(orders_ur, OrderDirection.long_entry, OrderDirection.short_entry):
                        break
        self.__orders_ur.clear()

    def place_order(self, symbol, volume=1, price=None, stop=False, limit=False, strategy=None, signal=None,
                    lineno=None, col_offset=None, direction=None):
        if not self.config.allow_trading:
            return
        if symbol not in self.config.symbols:
            self.logger.warning("订单品种<%s>不在当前交易品种中")
        orders_ur = self.__orders_ur[symbol]
        if (lineno, col_offset) not in orders_ur.flag:
            orders_ur.count += 1
            orders_ur.flag.add((lineno, col_offset))
            orders_ur.queue[direction].put(
                (orders_ur.count, lineno, col_offset, volume, price, stop, limit, strategy, signal))

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
        volume = round(volume, 2)  # 精确到mini手
        if volume == 0 or not direction:  # direction 对应多空头，1为多头，-1为空头
            return -1
        position = self.__current_positions.get(symbol, None)
        if not position or position.type != direction:
            return -1
        position_volume = round(position.volume, 2)
        if volume > position_volume:
            volume = position_volume
            self.logger.warning("平仓量超出当前持仓")
        order_type = (direction + 1) >> 1  # 平仓，多头时order_type为1(ORDER_TYPE_SELL), 空头时order_type为0(ORDER_TYPE_BUY)
        order = self.__factory.new_order(symbol, order_type, strategy, signal)
        order.volume_initial = volume
        if self.config.running_mode == RunningMode.backtest:
            time_frame = self._engine.strategys[strategy].signals[signal].time_frame
            time_ = self.__quotation_manager.find_quotation(symbol, time_frame).timestamp[0]
        else:
            time_ = time.time()
        order.time_setup = int(time_)
        order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
        return self.send_order(order)

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
        volume = round(volume, 2)  # 精确到mini手
        # 计算下单时间
        if self.config.running_mode == RunningMode.backtest:
            time_frame = self._engine.strategys[strategy].signals[signal].time_frame
            time_ = self.__quotation_manager.find_quotation(symbol, time_frame).timestamp[0]
        else:
            time_ = time.time()
        # 反向开仓先进行平仓处理
        position = self.__current_positions.get(symbol, None)
        order_type = (1 - direction) >> 1  # 开仓，空头时order_type为1(ORDER_TYPE_SELL), 多头时order_type为0(ORDER_TYPE_BUY)

        if position and position.type * direction == -1:
            order = self.__factory.new_order(symbol, order_type, strategy, signal)
            order.volume_initial = position.volume
            order.time_setup = int(time_)
            order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
            # TODO 这里应该要支持事务性的下单操作
            self.send_order(order)
        # 正向开仓
        if volume == 0:
            return -1
        order = self.__factory.new_order(symbol, order_type, strategy, signal)
        order.volume_initial = volume
        order.time_setup = int(time_)
        order.time_setup_msc = int((time_ - int(time_)) * (10 ** 6))
        return self.send_order(order)

    def get_APIs(self, strategy=None, signal=None, symbol=None) -> Globals:
        const = dict(
            Buy=partial(self.place_order, strategy=strategy, signal=signal, direction=OrderDirection.long_entry),
            Sell=partial(self.place_order, strategy=strategy, signal=signal, direction=OrderDirection.long_exit),
            SellShort=partial(self.place_order, strategy=strategy, signal=signal,
                              direction=OrderDirection.short_entry),
            BuyToCover=partial(self.place_order, strategy=strategy, signal=signal,
                               direction=OrderDirection.short_exit),
            Positions=self.current_positions)
        var = dict(
            Pos=lambda: self.current_positions[symbol],
            MarketPosition=lambda: self.current_positions[symbol].type,
            CurrentContracts=lambda: self.current_positions[symbol].volume,
        )
        return Globals(const, var)


class StrategyEngine(LoggerInterface, Runnable, ConfigInterface, APIInterface):
    """策略引擎"""

    def __init__(self, parent=None):
        """Constructor"""
        LoggerInterface.__init__(self)
        Runnable.__init__(self)
        ConfigInterface.__init__(self, parent=parent)
        self.__event_engine = EventEngine()  # 事件处理引擎
        self.__quotation_manager = QuotationManager(self, parent=self)  # 行情数据管理器
        if self.config.running_mode == RunningMode.backtest:
            self.__account_manager = BfAccountManager(parent=self)  # 账户管理
        else:
            self.__account_manager = FDTAccountManager(parent=self)
            self.mongo_user = MongoUser(self.config.user)
        self.__trading_manager = TradingManager(self, self.__quotation_manager, self.__account_manager,
                                                parent=self)  # 交易管理器
        if self.config.running_mode == RunningMode.backtest:
            self.__account_manager.set_trading_manager(self.__trading_manager)
        self.__strategys = {}  # 策略管理器
        self.__profit_records = []  # 保存账户净值的列表
        self._logger_child = {self.__event_engine: "EventEngine",
                              self.__trading_manager: "TradeManager",
                              self.__quotation_manager: "DataCache",
                              self.__account_manager: "AccountManager"}

    def set_account(self, account):
        assert isinstance(account, AccountManager)
        self.__account_manager = account

    @property
    def current_time(self):
        return self.__quotation_manager.current_time

    @property
    def positions(self):
        return self.__trading_manager.positions

    @property
    def deals(self):
        return self.__trading_manager.deals

    @property
    def strategys(self):
        return self.__strategys

    @property
    def profit_records(self):
        """获取平仓收益记录"""
        return self.__profit_records

    @property
    def max_margin(self):
        return self.__trading_manager.max_margin

    def profit_record(self, *args, **kwargs):
        return self.__account_manager.profit_record(*args, **kwargs)

    def realize_order(self):
        self.__trading_manager.realize_order()

    def add_cache_info(self, *args, **kwargs):
        self.__quotation_manager.add_cache_info(*args, **kwargs)
        # TODO 从全局的品种池中查询

    def add_file(self, file):
        self.__event_engine.add_file(file)

    def add_strategy(self, strategy):
        """添加已创建的策略实例"""
        self.__strategys[strategy.get_id()] = strategy
        strategy.engine = self

    def put_event(self, event):
        # TODO 加入验证
        # TODO 多了一层函数调用，尝试用绑定的形式
        self.__event_engine.put(event)

    def register_event(self, event_type, handle):
        """注册事件监听"""
        # TODO  加入验证
        self.__event_engine.register(event_type, handle)

    def unregister_event(self, event_type, handle):
        """取消事件监听"""
        self.__event_engine.unregister(event_type, handle)

    def write_log(self, log):
        """写日志"""
        self.__event_engine.put(Event(type=EVENT_LOG, log=log))

    def _start(self):
        """启动所有策略"""
        self.__profit_records.clear()
        self.__quotation_manager.start()
        self.__trading_manager.init()
        self.__event_engine.start()
        self.__account_manager.initialize()
        for strategy in self.__strategys.values():
            strategy.start()

    def _stop(self):
        """停止所有策略"""
        for strategy in self.__strategys.values():
            strategy.stop()
        self.__event_engine.stop()
        self.__quotation_manager.stop()
        self._recycle()  # 释放资源

    def _recycle(self):
        self.__quotation_manager.stop()
        self.__trading_manager.recycle()

    # TODO finished的参数设计有点问题
    def wait(self, call_back=None, finished=True, *args, **kwargs):
        """等待所有事件处理完毕
        :param call_back: 运行完成时的回调函数
        :param finished: 向下兼容，finish为True时，事件队列处理完成时结束整个回测引擎；为False时只是调用回调函数，继续挂起回测引擎。
        """
        self.__event_engine.wait()
        if call_back:
            result = call_back(*args, **kwargs)
        else:
            result = None
        if finished:
            self.stop()
        return result

    def get_APIs(self, strategy=None, signal=None, symbols=None, time_frame=None) -> Globals:
        APIs = Globals({}, {})
        APIs.update(self.__account_manager.get_APIs())
        APIs.update(self.__quotation_manager.get_APIs(symbols=symbols, time_frame=time_frame))
        APIs.update(self.__trading_manager.get_APIs(strategy=strategy, signal=signal, symbol=symbols[0]))
        return APIs
