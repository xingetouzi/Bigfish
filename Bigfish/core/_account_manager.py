# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:46:00 2015

@author: BurdenBear
"""
from functools import wraps
from dateutil.parser import parse
from weakref import proxy

from Bigfish.utils.log import LoggerInterface
from Bigfish.models.base import Currency
from Bigfish.fdt.account import FDTAccount
from Bigfish.models.trade import *

BASE_DEFAULT = 100000


###################################################################
class AccountManager(LoggerInterface):
    """交易账户对象"""

    def __init__(self, engine, config, currency=Currency("USD")):
        super().__init__()
        self._engine = proxy(engine)
        self._config = config
        self._capital_base = None
        self._capital_net = None
        self._capital_cash = None
        self._capital_available = None
        self._capital_margin = None
        self._currency = currency
        self.initialize()

    @property
    def capital_base(self):
        if self._capital_base is None:
            self._capital_base = self._config.capital_base
        return self._capital_base

    @capital_base.setter
    def capital_base(self, capital_base):
        if isinstance(capital_base, int) and capital_base > 0:
            self._capital_base = capital_base
            self.initialize()
        else:
            raise (ValueError("不合法的base值%s" % capital_base))

    @property
    def capital_cash(self):
        return self._capital_cash

    @property
    def capital_net(self):
        symbol_pool = self._engine.symbol_pool
        float_pnl = 0
        time_frame = self._config['time_frame']
        if not time_frame:
            time_frame = self._config['time_frame']
        for symbol, position in self._engine.current_positions.items():
            price = self._engine.data[time_frame]['close'][symbol][0]
            base_price = self._engine.get_counter_price(symbol, time_frame)
            float_pnl += symbol_pool[symbol].lot_value((price - position.price_current) * position.type,
                                                       position.volume,
                                                       commission=self._config['commission'],
                                                       slippage=self._config['slippage'],
                                                       base_price=base_price)
        self._capital_net = self._capital_cash + float_pnl
        return self._capital_net

    @property
    def capital_available(self):
        self._capital_available = self.capital_net - self.capital_margin
        return self._capital_available

    @property
    def capital_margin(self):
        self._capital_margin = 0
        symbol_pool = self._engine.symbol_pool
        for symbol, positions in self._engine.current_positions.items():
            if symbol.startswith('USD'):
                self._capital_margin += positions.volume * 100000 / symbol_pool[symbol].leverage
            elif symbol.endswith('USD'):
                self._capital_margin += positions.volume * 100000 * positions.price_current / symbol_pool[
                    symbol].leverage
        return self._capital_margin

    def initialize(self):
        self._capital_base = None
        self._capital_net = self.capital_base
        self._capital_cash = self.capital_base

    def update_cash(self, deal):
        if not deal.profit:
            return
        self._capital_cash += deal.profit

    def profit_record(self, time):
        return {'x': time, 'y': float('%.2f' % ((self.capital_net / self.capital_base - 1) * 100))}

    def get_api(self):
        class Capital:
            def __init__(self, manager):
                self.__manager = proxy(manager)

            @property
            def base(self):
                return self.__manager.capital_base

            @property
            def net(self):
                return self.__manager.capital_net

            @property
            def cash(self):
                return self.__manager.capital_cash

            @property
            def available(self):
                return self.__manager.capital_available

            @property
            def margin(self):
                return self.__manager.capital_margin

        return Capital(self)


def with_login(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.login():
            return func(self, *args, **kwargs)
        else:
            raise RuntimeError('账户验证失败')

    return wrapper


class FDTAccountManager(AccountManager):
    def __init__(self, engine, config):
        self._username = config.account
        self._password = config.password
        if self._username is not None and self._password is not None:
            self._account = FDTAccount(self._username, self._password)
        super().__init__(engine, config)

    def set_account(self, username, password):
        self._username = username
        self._password = password
        self._account = FDTAccount(self._username, self._password)
        self.initialize()

    @property
    def fx_account(self):
        for account in self._account.info['accounts']:
            if 'FX' in account['id']:
                return account

    @property
    @with_login
    def capital_base(self):
        self._capital_base = self.fx_account['cashDeposited']
        return self._capital_base

    @capital_base.setter
    def capital_base(self, capital_base):
        pass

    @property
    @with_login
    def capital_cash(self):
        self._capital_cash = self.fx_account['cash']
        return self._capital_cash

    @property
    @with_login
    def capital_available(self):
        self._capital_available = self.fx_account['cashAvailable']
        return self._capital_available

    @property
    @with_login
    def capital_margin(self):
        self._capital_margin = self.fx_account['marginHeld']
        return self._capital_margin

    @property
    @with_login
    def capital_net(self):
        fx_account = self.fx_account
        self._capital_net = fx_account['cash'] + fx_account['urPnL']
        return self._capital_net

    def login(self):
        return self._account.login()

    def send_order_to_broker(self, order):
        res = {}
        if order.type == ORDER_TYPE_BUY:
            res = self._account.market_order('Buy', int(order.volume_initial * 100000), order.symbol)
        elif order.type == ORDER_TYPE_SELL:
            res = self._account.market_order('Sell', int(order.volume_initial * 100000), order.symbol)
        if not res.get('ok', False):
            return -1
        else:
            return res.get('orderId')

    def order_status(self):
        return self._account.order_status()

    def update_cash(self, *args, **kwargs):
        self.capital_cash

    @with_login
    def profit_record(self):
        time = parse(self._account.info['user']['lastLogin']).timestamp()
        return super().profit_record(time)

    def position_status(self, symbol=None):
        res = self._account.open_positions()
        if res['ok']:
            positions = res['openPositions']
            if symbol is None:
                return positions
            else:
                for position in positions:
                    if position['symbol'] == symbol:
                        return position
                return None
        else:
            return None
