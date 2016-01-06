# -*- coding: utf-8 -*-
"""
Created on Fri Nov 27 22:42:54 2015

@author: BurdenBear
"""
from collections import OrderedDict

from Bigfish.event.event import EVENT_BAR_SYMBOL
from Bigfish.models.common import HasID


# -----------------------------------------------------------------------
class SymbolsListener(HasID):
    __SymbolsListeners = {}

    def __init__(self, engine, symbols, time_frame):
        self.__id = self.next_auto_inc()
        self.__symbols = {item: n for n, item in enumerate(symbols)}
        self.__count = len(symbols)
        self.__parameters = OrderedDict()
        self.__time_frame = time_frame
        self.__engine = engine
        self.__generator = None
        self.__gene_istance = None
        self.__handler = self.__handle()
        self.__SymbolsListeners[self.__id] = self
        self.__bar_num = 0  # 暂时使用在LocalsInjector中改写的方式

    @classmethod
    def get_by_id(cls, id_):
        return cls.__SymbolsListeners[id_]

    def get_id(self):
        return self.__id

    def add_parameters(self, key, value):
        self.__parameters[key] = value

    def set_parameters(self, **kwargs):
        self.__parameters = kwargs

    def get_parameters(self):
        return self.__parameters.copy()

    def get_time_frame(self):
        return self.__time_frame

    def set_generator(self, generator):
        self.__generator = generator

    def get_bar_num(self):
        return self.__bar_num

    bar_num = property(get_bar_num, None, None)

    def start(self):
        self.__bar_num = 0
        if self.__generator:
            self.__gene_istance = self.__generator(**self.__parameters)
            for symbol in self.__symbols.keys():
                self.__engine.register_event(EVENT_BAR_SYMBOL[symbol][self.__time_frame], self.__handler.send)
            self.__handler.send(None)  # start it

    def stop(self):
        if self.__generator:
            for symbol in self.__symbols.keys():
                self.__engine.unregister_event(EVENT_BAR_SYMBOL[symbol][self.__time_frame], self.__handler.send)
            self.__gene_istance.close()
            self.__handler.close()  # stop it

    def __handle(self):
        bits_ready = (1 << self.__count) - 1
        bits_now = 0
        while True:
            event = yield
            bar = event.content["data"]
            bits_now |= 1 << self.__symbols[bar.symbol]
            if bits_now == bits_ready:
                self.__bar_num += 1
                self.__gene_istance.__next__()
                bits_now = 0
