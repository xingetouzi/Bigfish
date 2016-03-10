# -*- coding: utf-8 -*-
"""
Created on Fri Nov 27 22:42:54 2015

@author: BurdenBear
"""
from collections import OrderedDict

from Bigfish.event.event import EventsPacker, EVENT_SYMBOL_BAR_UPDATE, EVENT_SYMBOL_BAR_COMPLETED, Event
from Bigfish.models.common import FactoryWithList


class SymbolBarUpdateEventsPacker(EventsPacker):
    def __init__(self, engine, symbols, time_frame, out, type='all'):
        events = [EVENT_SYMBOL_BAR_UPDATE[symbol][time_frame] for symbol in symbols]
        super(SymbolBarUpdateEventsPacker, self).__init__(engine, events, out, type)


class SymbolBarCompletedEventsPacker(EventsPacker):
    def __init__(self, engine, symbols, time_frame, out=None, type='all'):
        events = [EVENT_SYMBOL_BAR_COMPLETED[symbol][time_frame] for symbol in symbols]
        super(SymbolBarCompletedEventsPacker, self).__init__(engine, events, out, type)


class Signal:

    def __init__(self, engine, symbols, time_frame, id=None):
        """
        信号对象，每一个信号即为策略代码中不以init为名的任意最外层函数，订阅某些品种的行情数据，运行于特定时间框架下。
        通过两个EventPacker(事件打包器)接受StrategyEngine中的DataCache(数据中转器)发出的行情事件来管理Bar数据的结构。
        :param engine:挂载运行的策略引擎
        :param symbols:所订阅行情数据的品种列表
        :param time_frame:所订阅行情数据的事件框架
        :param id:不需要传入，由SignalFactory自动管理。
        """
        self._id = id
        self._event_update = Event.create_event_type('SignalUpdate.%s' % self._id, priority=1).get_id()
        self._event_completed = Event.create_event_type('SignalCompleted.%s' % self._id, priority=2).get_id()
        self._update = SymbolBarUpdateEventsPacker(engine, symbols, time_frame, self._event_update)
        self._completed = SymbolBarCompletedEventsPacker(engine, symbols, time_frame, self._event_completed)
        self._parameters = OrderedDict()
        self._symbols = symbols
        self._time_frame = time_frame
        self._engine = engine
        self._handler = None
        self._generator = None
        self._gene_instance = None
        self._bar_num = 0  # 暂时使用在LocalsInjector中改写的方式

    @property
    def symbols(self):
        return self._symbols

    @property
    def time_frame(self):
        return self._time_frame

    @property
    def id(self):
        return self._id

    def get_current_bar(self):
        return self._bar_num

    def add_parameters(self, key, value):
        self._parameters[key] = value

    def set_parameters(self, **kwargs):
        self._parameters = kwargs

    def get_parameters(self):
        return self._parameters.copy()

    def get_time_frame(self):
        return self._time_frame

    def set_generator(self, generator):
        self._generator = generator

    def get_bar_num(self):
        return self._bar_num

    bar_num = property(get_bar_num, None, None)

    def __handle(self):
        while True:
            event = yield
            if event.type == self._event_completed:
                self._bar_num += 1
            self._gene_instance.__next__()

    def start(self):
        self._bar_num = 0
        if self._generator:
            self._handler = self.__handle()
            self._gene_instance = self._generator(**self._parameters)
            self._engine.register_event(self._event_update, self._handler.send)
            self._engine.register_event(self._event_completed, self._handler.send)
            self._update.start()
            self._completed.start()
            self._handler.send(None)  # start it

    def stop(self):
        if self._generator:
            self._gene_instance.close()
            self._handler.close()  # stop it
            self._update.stop()
            self._completed.stop()
            self._engine.unregister_event(self._event_update, self._handler.send)
            self._engine.unregister_event(self._event_completed, self._handler.send)


class SignalFactory(FactoryWithList):
    _class = Signal
