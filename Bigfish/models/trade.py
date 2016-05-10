# -*- coding: utf-8 -*-
"""
Created on Fri Nov 27 09:59:13 2015

@author: BurdenBear
"""

from Bigfish.models.common import DictLike, FactoryWithTimestampPrefixID
from enum import Enum

"""所有的数据结构都继承HasID，通过ID来访问，以便于以后在数据库中存储"""

# ENUM_POSITION_TYPE
POSITION_TYPE_BUY = 1
POSITION_TYPE_NONE = 0
POSITION_TYPE_SELL = -1


class Position(DictLike):
    """仓位对象"""

    __slots__ = ["symbol", "deal", "id", "prev_id", "next_id", "time_open", "time_open_msc", "time_update",
                 "time_update_msc", "type", "volume", "price_open", "price_current", "price_profit", "strategy",
                 "signal"]

    def __init__(self, symbol=None, strategy=None, signal=None, id=None):
        self.symbol = symbol
        self.deal = None
        self.id = id
        self.prev_id = None
        self.next_id = None
        self.time_open = None
        self.time_open_msc = None
        self.time_update = None
        self.time_update_msc = None
        self.type = 0
        self.volume = 0
        self.price_open = 0
        self.price_current = 0
        self.price_profit = None
        self.strategy = strategy
        self.signal = signal

    def __ne__(self, x):
        return self.type.__ne__(x)

    def __eq__(self, x):
        return self.type.__eq__(x)

    def __le__(self, x):
        return self.type.__le__(x)

    def __lt__(self, x):
        return self.type.__lt__(x)

    def __gt__(self, x):
        return self.type.__gt__(x)

    def __ge__(self, x):
        return self.type.__ge__(x)

    def get_id(self):
        return self.id


class PositionFactory(FactoryWithTimestampPrefixID):
    _class = Position

    def __init__(self, prefix='', timestamp=False):
        super().__init__(prefix, timestamp=timestamp)


class OrderDirection(Enum):
    long_entry = 0
    short_entry = 1
    long_exit = 2
    short_exit = 3


# ENUM_ORDER_STATE
ORDER_STATE_STARTED = 0  # Order checked, but not yet accepted by broker
ORDER_STATE_PLACED = 1  # Order accepted
ORDER_STATE_CANCELED = 2  # Order canceled by client
ORDER_STATE_PARTIAL = 3  # Order partially executed
ORDER_STATE_FILLED = 4  # Order fully executed
ORDER_STATE_REJECTED = 5  # Order rejected
ORDER_STATE_EXPIRED = 6  # Order expired
ORDER_STATE_REQUEST_ADD = 7  # Order is being registered (placing to the trading system)
ORDER_STATE_REQUEST_MODIFY = 8  # Order is being modified (changing its parameters)
ORDER_STATE_REQUEST_CANCEL = 9  # Order is being deleted (deleting from the trading system)

# ENUM_ORDER_TYPE
ORDER_TYPE_BUY = 0  # Market Buy order
ORDER_TYPE_SELL = 1  # Market Sell order
ORDER_TYPE_BUY_LIMIT = 2  # Buy Limit pending order
ORDER_TYPE_SELL_LIMIT = 3  # Sell Limit pending order
ORDER_TYPE_BUY_STOP = 4  # Buy Stop pending order
ORDER_TYPE_SELL_STOP = 5  # Sell Stop pending order
ORDER_TYPE_BUY_STOP_LIMIT = 6  # Upon reaching the order price, a pending Buy Limit order is placed at the StopLimit price
ORDER_TYPE_SELL_STOP_LIMIT = 7  # Upon reaching the order price, a pending Sell Limit order is placed at the StopLimit price

# ENUM_ORDER_TYPE_FILLING
ORDER_FILLING_FOK = 0
ORDER_FILLING_IOC = 1
ORDER_FILLING_RETURN = 2

# ENUM_ORDER_TYPE_LIFE
ORDER_LIFE_GTC = 0  # Good till cancel order
ORDER_LIFE_DAY = 1  # Good till current trade day order
ORDER_LIFE_SPECIFIED = 2  # Good till expired order
ORDER_LIFE_SPECIFIED_DAY = 3  # The order will be effective till 23:59:59 of the specified day. If this time is outside a trading session, the order expires in the nearest trading time.


class Order(DictLike):
    """订单对象"""
    __slots__ = ["symbol", "id", "deal", "time_setup", "time_expiration", "time_done",
                 "time_setup_msc", "time_expiration_msc", "time_done_msc",
                 "type", "state", "type_filling", "type_life", "volume_initial",
                 "volume_current", "price_open", "price_stop_limit", "stop_loss",
                 "take_profit", "strategy", "signal"]

    def __init__(self, symbol=None, type_=None, strategy=None, signal=None, id=None):
        self.symbol = symbol
        self.deal = None
        self.id = id
        self.time_setup = None
        self.time_expiration = None
        self.time_done = None
        self.time_setup_msc = None
        self.time_expiration_msc = None
        self.time_done_msc = None
        self.type = type_
        self.state = None
        self.type_filling = None
        self.type_life = None
        self.volume_initial = 0
        self.volume_current = 0
        self.price_open = 0
        self.price_stop_limit = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.strategy = strategy
        self.signal = signal

    def get_id(self):
        return self.id


class OrderFactory(FactoryWithTimestampPrefixID):
    _class = Order

    def __init__(self, prefix='', timestamp=False):
        super().__init__(prefix, timestamp=timestamp)


# ENUM_DEAL_TYPE
DEAL_TYPE_BUY = 1
DEAL_TYPE_SELL = -1
# ENUM_DEAL_ENTRY
DEAL_ENTRY_IN = 1  # Entry in
DEAL_ENTRY_OUT = 0  # Entry out
DEAL_ENTRY_INOUT = -1  # Reverse


class Deal(DictLike):
    """成交对象"""
    __slots__ = ["symbol", "id", "order", "position", "time", "time_msc", "type", "entry",
                 "volume", "price", "commission", "profit", "strategy", "signal"]

    def __init__(self, symbol=None, strategy=None, signal=None, id=None):
        self.symbol = symbol
        self.id = id
        self.order = None
        self.position = None
        self.time = None
        self.time_msc = None
        self.type = None
        self.entry = None
        self.volume = 0
        self.price = 0
        self.commission = 0
        self.profit = None
        self.strategy = strategy
        self.signal = signal

    def get_id(self):  # 向下兼容
        return self.id


class DealFactory(FactoryWithTimestampPrefixID):
    _class = Deal

    def __init__(self, prefix='', timestamp=False):
        super().__init__(prefix, timestamp=timestamp)
