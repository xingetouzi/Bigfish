# -*- coding: utf-8 -*-
"""
Created on Fri Nov 27 22:42:54 2015

@author: BurdenBear
"""
from collections import OrderedDict
from Bigfish.event.event import EVENT_SYMBOL_BAR_UPDATE, EVENT_SYMBOL_BAR_COMPLETED, Event
from Bigfish.models.common import FactoryWithID
from Bigfish.models.enviroment import APIInterface, Globals, Environment
from Bigfish.models.config import ConfigInterface
from Bigfish.models.base import Runnable,  TradingMode


class EventsPacker:
    def __init__(self, engine, events, out=None, type='all'):
        self.engine = engine  # StrategyEngine对象
        self.events_in = tuple(events)  # 需要打包全部的events
        self._events_enum = {k: n for n, k in enumerate(self.events_in)}
        self.type = type
        self.events_out = out
        self._bits = 0
        self._complete = (1 << len(self.events_in)) - 1
        self._running = False
        self.register()

    def start(self):
        self._bits = 0
        self._running = True

    def stop(self):
        self._running = False

    def out(self):
        if self.events_out:
            self.engine.put_event(Event(type=self.events_out))

    def register(self):
        for event in self.events_in:
            self.engine.register_event(event, self._on_event)

    def unregister(self):
        for event in self.events_in:
            self.engine.unregister_event(event, self._on_event)

    def _on_event(self, event):
        if not self._running:
            return
        if self.type == 'any':
            self.out()
        elif self.type == 'all':
            self._bits |= (1 << self._events_enum[event.type])
            if self._bits == self._complete:
                self.out()
                self._bits = 0


class SymbolBarUpdateEventsPacker(EventsPacker):
    def __init__(self, engine, symbols, time_frame, out=None, type='all'):
        events = [EVENT_SYMBOL_BAR_UPDATE[symbol][time_frame] for symbol in symbols]
        super(SymbolBarUpdateEventsPacker, self).__init__(engine, events, out, type)


class SymbolBarCompletedEventsPacker(EventsPacker):
    def __init__(self, engine, symbols, time_frame, out=None, type='all'):
        events = [EVENT_SYMBOL_BAR_COMPLETED[symbol][time_frame] for symbol in symbols]
        super(SymbolBarCompletedEventsPacker, self).__init__(engine, events, out, type)


class Signal(Runnable, APIInterface, ConfigInterface):
    def __init__(self, engine, user, strategy, name, symbols, time_frame, id=None, parent=None):
        """
        信号对象，每一个信号即为策略代码中不以init为名的任意最外层函数，订阅某些品种的行情数据，运行于特定时间框架下。
        通过两个EventPacker(事件打包器)接受StrategyEngine中的DataCache(数据中转器)发出的行情事件来管理Bar数据的结构。
        :param engine:挂载运行的策略引擎
        :param symbols:所订阅行情数据的品种列表
        :param time_frame:所订阅行情数据的事件框架
        :param id:不需要传入，由SignalFactory自动管理。
        """
        Runnable.__init__(self)
        APIInterface.__init__(self)
        ConfigInterface.__init__(self, parent=parent)
        self._id = id
        self._user = user
        self._strategy = strategy
        self._name = name
        self._event_update = Event.create_event_type('SignalUpdate.%s.%s.%s' % (self._user, self._strategy, self._name),
                                                     priority=1).get_id()
        self._event_completed = Event.create_event_type(
            'SignalCompleted.%s.%s.%s' % (self._user, self._strategy, self._name), priority=2).get_id()
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
        self._environment = None

    @property
    def environment(self):
        return self._environment

    @environment.setter
    def environment(self, value):
        assert isinstance(value, Environment)
        self._environment = Environment

    @property
    def symbols(self):
        return self._symbols

    @property
    def time_frame(self):
        return self._time_frame

    @property
    def id(self):
        return self._id

    def add_parameters(self, key, value):
        self._parameters[key] = value

    def set_parameters(self, **kwargs):
        self._parameters = kwargs

    def get_parameters(self):
        return self._parameters.copy()

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

    def _start(self):
        self._bar_num = 0
        if self._generator:
            self._handler = self.__handle()
            self._gene_instance = self._generator(**self._parameters)
            if self.config.trading_mode == TradingMode.on_tick:
                self._engine.register_event(self._event_update, self._handler.send)
            self._engine.register_event(self._event_completed, self._handler.send)
            self._update.start()
            self._completed.start()
            self._handler.send(None)  # start it

    def _stop(self):
        if self._generator:
            self._gene_instance.close()
            self._handler.close()  # stop it
            self._update.stop()
            self._completed.stop()
            self._engine.unregister_event(self._event_update, self._handler.send)
            self._engine.unregister_event(self._event_completed, self._handler.send)

    def get_APIs(self, **kwargs) -> Globals:
        var = {"BarNum": self.get_bar_num}
        return Globals({}, var)


class SignalFactory(FactoryWithID):
    _class = Signal
