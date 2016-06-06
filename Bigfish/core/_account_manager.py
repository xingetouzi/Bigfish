# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:46:00 2015

@author: BurdenBear
"""
import time
from weakref import proxy
from Bigfish.fdt.account import FDTAccount
from Bigfish.models.base import Currency
from Bigfish.models.config import ConfigInterface
from Bigfish.models.enviroment import APIInterface, Globals
from Bigfish.models.trade import *
from Bigfish.utils.log import LoggerInterface

__all__ = ["AccountManager", "BfAccountManager", "FDTAccountManager"]


class AccountManager(LoggerInterface, ConfigInterface, APIInterface):
    """交易账户对象"""

    def __init__(self, currency=Currency("USD"), parent=None):
        LoggerInterface.__init__(self, parent=parent)
        ConfigInterface.__init__(self, parent=parent)
        self._capital_base = None
        self._capital_net = None
        self._capital_cash = None
        self._capital_available = None
        self._capital_margin = None
        self._currency = currency
        self.logger_name = "AccountManager"

    @property
    def capital_base(self):
        return self._capital_base

    @capital_base.setter
    def capital_base(self, value):
        raise NotImplementedError

    @property
    def capital_cash(self):
        return self._capital_cash

    @capital_cash.setter
    def capital_cash(self, value):
        raise NotImplementedError

    @property
    def capital_net(self):
        return self._capital_net

    @capital_net.setter
    def capital_net(self, value):
        raise NotImplementedError

    @property
    def capital_available(self):
        return self._capital_available

    @capital_available.setter
    def capital_available(self, value):
        raise NotImplementedError

    @property
    def capital_margin(self):
        return self._capital_margin

    @capital_margin.setter
    def capital_margin(self):
        self._capital_margin = 0

    def initialize(self):
        self._capital_base = self.config.capital_base
        self._capital_net = self.capital_base
        self._capital_cash = self.capital_base

    def profit_record(self, time):
        return {'x': time, 'y': float('%.2f' % ((self.capital_net / self.capital_base - 1) * 100))}

    def get_APIs(self) -> Globals:
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

        return Globals({"Cap": Capital(self)}, {})


class BfAccountManager(AccountManager):
    def __init__(self, trading_manager=None, parent=None):
        super().__init__(parent=parent)
        self.__trading_manager = trading_manager

    def set_trading_manager(self, trading_manager):
        self.__trading_manager = trading_manager

    @property
    def capital_base(self):
        return self._capital_base

    @capital_base.setter
    def capital_base(self, value):
        if isinstance(value, float) and value > 0:
            self._capital_base = value
            self.initialize()
        else:
            raise (ValueError("不合法的base值%s" % value))

    @property
    def capital_cash(self):
        return self._capital_cash

    @capital_cash.setter
    def capital_cash(self, value):
        self._capital_cash = value

    @property
    def capital_net(self):
        float_pnl = self.__trading_manager.float_pnl
        self._capital_net = self._capital_cash + float_pnl
        return self._capital_net

    @property
    def capital_available(self):
        self._capital_available = self.capital_net - self.capital_margin
        return self._capital_available

    @property
    def capital_margin(self):
        self._capital_margin = self.__trading_manager.margin
        return self._capital_margin


class FDTAccountManager(AccountManager):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._username = self.config.account
        self._password = self.config.password
        if self._username is not None and self._password is not None:
            self._account = FDTAccount(self._username, self._password)

    def set_account(self, username, password):
        self._username = username
        self._password = password
        self._account = FDTAccount(self._username, self._password)

    @property
    def fx_account(self):
        accounts = []
        retry_time = 0
        while not accounts and retry_time < 3:
            accounts = self._account.account_status()["accounts"]
            retry_time += 1
        for account in accounts:
            if 'FX' in account['id']:
                return account
        raise RuntimeError("回去账户信息失败")

    @property
    def capital_base(self):
        self._capital_base = self.fx_account['cashDeposited']
        return self._capital_base

    @property
    def capital_cash(self):
        self._capital_cash = self.fx_account['cash']
        return self._capital_cash

    @property
    def capital_available(self):
        self._capital_available = self.fx_account['cashAvailable']
        return self._capital_available

    @property
    def capital_margin(self):
        self._capital_margin = self.fx_account['marginHeld']
        return self._capital_margin

    @property
    def capital_net(self):
        fx_account = self.fx_account
        self._capital_net = fx_account['cash'] + fx_account['urPnL']
        return self._capital_net

    def initialize(self):
        pass

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

    def profit_record(self, *args):
        time_ = time.time()
        return super().profit_record(time_)

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
