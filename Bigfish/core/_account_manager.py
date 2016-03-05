# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:46:00 2015

@author: BurdenBear
"""

from Bigfish.utils.base import Currency


###################################################################
class AccountManager:
    """交易账户对象"""

    def __init__(self, capital_base=100000, name="", currency=Currency("USD"), leverage=1):
        self.__capital_base = capital_base
        self.__name = name
        self.__currency = currency
        self.__leverage = leverage
        self.__capital_net = self.__capital_base
        self.__capital_cash = self.__capital_base
        self.__records = []
        self.initialize()

    def initialize(self):
        self.__capital_net = self.__capital_base
        self.__capital_cash = self.__capital_base
        self.__records.clear()

    def set_capital_base(self, capital_base):
        if isinstance(capital_base, int) and capital_base > 0:
            self.__capital_base = capital_base
            self.initialize
        else:
            raise (ValueError("不合法的base值%s" % capital_base))

    def is_margin_enough(self, price):
        """判断账户保证金是否足够"""
        return self.__capital_cash * self.__leverage >= price

    def update_deal(self, deal):
        if not deal.profit:
            return
        self.__capital_cash += deal.profit
        self.__records.append({'x': deal.time + deal.time_msc / (10 ** 6),
                               'y': float('%.2f' % ((self.__capital_cash / self.__capital_base - 1) * 100))})

    def get_profit_records(self):
        return self.__records
