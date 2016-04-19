# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:46:00 2015

@author: BurdenBear
"""
from dateutil.parser import parse
from weakref import proxy
from Bigfish.models.base import Currency
from Bigfish.fdt.account import FDTAccount
from Bigfish.models.trade import *

BASE_DEFAULT = 100000


###################################################################
class AccountManager:
    """交易账户对象"""

    def __init__(self, engine, currency=Currency("USD"), **config):
        self._engine = proxy(engine)
        self._config = config
        self._capital_base = None
        self._capital_net = None
        self._capital_cash = None
        self._currency = currency

        self._records = []
        self.initialize()

    def _get_capital_base(self):
        if self._capital_base is None:
            self._capital_base = self._config.get('base', BASE_DEFAULT)
        return self._capital_base

    def _set_capital_base(self, capital_base):
        if isinstance(capital_base, int) and capital_base > 0:
            self._capital_base = capital_base
            self.initialize()
        else:
            raise (ValueError("不合法的base值%s" % capital_base))

    def _get_capital_cash(self):
        return self._capital_cash

    def _get_capital_net(self):
        return self._capital_net

    capital_base = property(_get_capital_base, _set_capital_base)
    capital_cash = property(_get_capital_cash)
    capital_net = property(_get_capital_net)

    def initialize(self):
        self._capital_base = None
        self._capital_net = self.capital_base
        self._capital_cash = self.capital_base
        self._records.clear()

    def is_margin_enough(self, price):
        """判断账户保证金是否足够"""
        return self._capital_cash >= price

    def update_cash(self, deal):
        if not deal.profit:
            return
        self._capital_cash += deal.profit

    def update_net(self, positions, time, time_frame=None):
        symbol_pool = self._engine.symbol_pool
        float_pnl = 0
        if not time_frame:
            time_frame = self._config['time_frame']
        for symbol, position in positions.items():
            price = self._engine.data[time_frame]['close'][symbol][0]
            base_price = self._engine.get_base_price(symbol, time_frame)
            float_pnl += symbol_pool[symbol].lot_value((price - position.price_current) * position.type,
                                                       position.volume,
                                                       commission=self._config['commission'],
                                                       slippage=self._config['slippage'],
                                                       base_price=base_price)
        self._capital_net = self._capital_cash + float_pnl
        self.update_records(time)

    def update_records(self, time):
        self._records.append({'x': time,
                              'y': float(
                                  '%.2f' % ((self.capital_net / self.capital_base - 1) * 100))})

    def get_profit_records(self):
        return self._records


class FDTAccountManager(AccountManager):
    def __init__(self, *args, **kwargs):
        self._username = kwargs.pop('username', None)
        self._password = kwargs.pop('password', None)
        super().__init__(*args, **kwargs)
        self._account = FDTAccount(self._username, self._password)

    def set_account(self, username, password):
        self._username = username
        self._password = password

    def _get_capital_base(self):
        if self.login():
            self._capital_base = self._account.info['accounts']['cashDeposited']
        else:
            raise RuntimeError('账户验证失败')
        return self._capital_base

    def _set_capital_base(self, capital_base):
        pass

    def _get_capital_cash(self):
        if self.login():
            self._capital_cash = self._account.info['accounts']['cash']
        else:
            raise RuntimeError('账户验证失败')
        return self._capital_cash

    def _get_capital_net(self):
        if self.login():
            self._capital_net = self._account.info['account']['cash']
            res = self._account.open_positions()
            if res['ok']:
                for position in res['openPositions']:
                    self._capital_net += position['acPnL'] - 2  # XXX 每笔两元手续费
        else:
            raise RuntimeError('账户验证失败')
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

    def update_net(self, *args, **kwargs):
        self.capital_net

    def update_records(self, *args, **kwargs):
        if self.login():
            time = parse(self._account.info['user']['lastLogin']).timestamp()
            super().update_records(time)
