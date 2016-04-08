# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:46:00 2015

@author: BurdenBear
"""
from weakref import proxy
from Bigfish.models.base import Currency


###################################################################
class AccountManager:
    """交易账户对象"""

    def __init__(self, engine, capital_base=100000, name="", currency=Currency("USD"), **config):
        self.__engine = proxy(engine)
        self.__config = config
        self.__capital_base = capital_base
        self.__name = name
        self.__currency = currency
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
            self.initialize()
        else:
            raise (ValueError("不合法的base值%s" % capital_base))

    def is_margin_enough(self, price):
        """判断账户保证金是否足够"""
        return self.__capital_cash >= price

    def update_deal(self, deal):
        if not deal.profit:
            return
        self.__capital_cash += deal.profit

    def update_records(self, positions, time, time_frame=None):
        symbol_pool = self.__engine.symbol_pool
        float_pnl = 0
        if not time_frame:
            time_frame = self.__config['time_frame']
        for symbol, position in positions.items():
            price = self.__engine.data[time_frame]['close'][symbol][0]
            base_price = self.__engine.get_base_price(symbol, time_frame)
            float_pnl += symbol_pool[symbol].lot_value((price - position.price_current) * position.type,
                                                        position.volume,
                                                        commission=self.__config['commission'],
                                                        slippage=self.__config['slippage'],
                                                        base_price=base_price)
        self.__records.append({'x': time,
                               'y': float(
                                   '%.2f' % (((self.__capital_cash + float_pnl) / self.__capital_base - 1) * 100))})

    def get_profit_records(self):
        return self.__records
