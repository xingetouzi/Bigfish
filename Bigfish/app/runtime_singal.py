# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:41:04 2015

@author: BurdenBear
"""
import traceback
import logging

from Bigfish.core import TickDataGenerator, StrategyEngine, Strategy
from Bigfish.models.base import RunningMode, TradingMode
from Bigfish.models.config import BfConfig
from Bigfish.event.event import Event, EVENT_FINISH
from Bigfish.performance.performance import StrategyPerformanceManagerOnline
from Bigfish.utils.log import LoggerInterface
from Bigfish.utils.memory_profiler import profile
from Bigfish.config import DEBUG


class RuntimeSignal(LoggerInterface):
    def __init__(self):
        super().__init__()
        self.__config = None
        self.__code = None
        self.__strategy = None
        self.__strategy_engine = None
        self.__data_generator = None
        self.__strategy_parameters = None
        self.__performance_manager = None
        self.__is_alive = False
        self.__initialized = False

    def init(self):
        if self.__initialized:
            return True
        assert isinstance(self.__config, BfConfig)  # 判断初始化前是否设置好了基本参数
        self.__strategy_engine = StrategyEngine(self.__config)
        self.__strategy = Strategy(self.__strategy_engine, self.__code, self.__config)
        self.__strategy_engine.add_strategy(self.__strategy)
        self.__data_generator = TickDataGenerator(self.__config,
                                                  lambda x: self.__strategy_engine.put_event(x.to_event()),
                                                  lambda: self.__strategy_engine.put_event(Event(EVENT_FINISH)))
        self._logger_child = {self.__strategy_engine: "StrategyEngine",
                              self.__strategy: "Strategy",
                              self.__data_generator: "DataGenerator"}
        self.logger_name = 'RuntimeSignal'
        if DEBUG:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.__initialized = True

    def set_config(self, config):
        assert isinstance(config, BfConfig)
        self.__config = config
        self.__config.running_mode = RunningMode.runtime

    def get_config(self, name):
        return getattr(self.__config, name)

    @property
    def code(self):
        return self.__code

    @code.setter
    def code(self, code):
        assert isinstance(code, str)
        self.__code = code.replace('\t', '    ')

    def register_event(self, event_type, func):
        if self.__initialized:
            self.__strategy_engine.register_event(event_type, func)
        else:
            self.logger.warning("无效的事件注册，原因：未初始化")

    @property
    def is_finished(self):
        return self.__is_alive

    @profile
    def start(self, paras=None, refresh=True):
        """

        :param paras:
        :param refresh: True表示刷新绩效且需要释放资源，即用户一个完整的请求已经结束；False的情况主要是参数优化时批量运行回测。
        """
        try:
            self.logger.info("<%s>策略运算开始" % self.__config["name"])
            if not self.__initialized:
                self.init()
            self.__is_alive = True
            if paras is not None:
                self.__strategy.set_parameters(paras)
            self.__strategy_engine.start()
            self.__data_generator.start()
            if refresh:
                self.__performance_manager = self.__strategy_engine.wait(self.__get_performance_manager)
                self.__data_generator.stop()
                result = self.__performance_manager
            else:
                result = self.__strategy_engine.wait()
            return result
        except:
            self.logger.error("\n" + traceback.format_exc())
            self.stop()

    def stop(self):
        self.logger.info("<%s>策略运算停止" % self.__config["name"])
        self.__is_alive = False
        self.__data_generator.stop()
        self.__strategy_engine.stop()

    def __get_performance_manager(self):
        # TODO 加入回测是否运行的判断
        if False:
            raise ValueError('please run the backtest first')
        return StrategyPerformanceManagerOnline(self.__strategy_engine.get_profit_records(),
                                                self.__strategy_engine.get_deals(),
                                                self.__strategy_engine.get_positions())

    def get_profit_records(self):
        return self.__strategy_engine.get_profit_records()

    def get_performance(self):
        return self.__performance_manager.get_performance()

    def get_output(self):
        return self.__strategy.get_output()

    def get_setting(self):
        return self.__config.to_dict()

    def get_parameters(self):
        if self.__strategy_parameters is None:
            temp = self.__strategy.get_parameters()
            for handle_name in temp.keys():
                for para_name, values in temp[handle_name].items():
                    temp[handle_name][para_name] = {'default': values, 'type': str(type(values))}
            self.__strategy_parameters = temp
        return self.__strategy_parameters


if __name__ == '__main__':
    import codecs
    import time

    import sys
    import os


    def get_first_n_lines(string, n):
        lines = string.splitlines()
        n = min(n, len(lines))
        return '\n'.join(lines[:n])


    def set_handle(logger):
        console = logging.StreamHandler(stream=sys.stdout)
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(filename)-20s[line:%(lineno)-3d] %(levelname)-8s %(message)s')
        console.setFormatter(formatter)
        logger.addHandler(console)
        return console


    start_time = time.time()
    file = "testcode17.py"
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test', file)
    with codecs.open(path, 'r', 'utf-8') as f:
        code = f.read()
    config = BfConfig(user='10032', name=file.split(".")[0], account="mb000004296",
                      password="Morrisonwudi520", time_frame='M1', symbols=['EURUSD'],
                      trading_mode=TradingMode.on_tick)
    signal = RuntimeSignal()
    signal.code = code
    signal.set_config(config)
    signal.init()
    set_handle(signal.logger)
    signal.start()
