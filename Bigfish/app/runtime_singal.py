# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:41:04 2015

@author: BurdenBear
"""
import traceback
import logging

from Bigfish.core import TickDataGenerator, StrategyEngine, Strategy
from Bigfish.models.base import RunningMode, TradingMode
from Bigfish.models.config import BfConfig, ConfigInterface
from Bigfish.event.event import Event, EVENT_FINISH
from Bigfish.utils.log import LoggerInterface
from Bigfish.config import DEBUG


class RuntimeSignal(LoggerInterface, ConfigInterface):
    def __init__(self):
        LoggerInterface.__init__(self)
        ConfigInterface.__init__(self)
        self.__code = None
        self.__strategy = None
        self.__strategy_engine = None
        self.__data_generator = None
        self.__strategy_parameters = None
        self.__performance_manager = None
        self.__is_alive = False
        self.__initialized = False
        self.logger_name = 'RuntimeSignal'

    def init(self):
        if self.__initialized:
            return True
        assert isinstance(self._config, BfConfig)  # 判断初始化前是否设置好了基本参数
        self.__strategy_engine = StrategyEngine(parent=self)
        self.__strategy = Strategy(self.__strategy_engine, self.__code, parent=self)
        self.__strategy_engine.add_strategy(self.__strategy)
        self.__data_generator = TickDataGenerator(lambda x: self.__strategy_engine.put_event(x.to_event()),
                                                  lambda: self.__strategy_engine.put_event(Event(EVENT_FINISH)),
                                                  parent=self)
        if DEBUG:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.__initialized = True

    def set_config(self, config):
        assert isinstance(config, BfConfig)
        self._config = config
        self._config.running_mode = RunningMode.runtime

    @property
    def code(self):
        return self.__code

    @code.setter
    def code(self, value):
        assert isinstance(value, str)
        self.__code = value.replace('\t', '    ')

    def register_event(self, event_type, func):
        if self.__initialized:
            self.__strategy_engine.register_event(event_type, func)
        else:
            self.logger.warning("无效的事件注册，原因：未初始化")

    @property
    def is_finished(self):
        return self.__is_alive

    def start(self, paras=None):
        """

        :param paras:
        :param refresh: True表示刷新绩效且需要释放资源，即用户一个完整的请求已经结束；False的情况主要是参数优化时批量运行回测。
        """
        try:
            self.logger.info("<%s>策略运算开始" % self._config["name"])
            if not self.__initialized:
                self.init()
            self.__is_alive = True
            if paras is not None:
                self.__strategy.set_parameters(paras)
            self.__strategy_engine.start()
            self.__data_generator.start()
            self.__strategy_engine.wait()
        except:
            self.logger.error("\n" + traceback.format_exc())
        finally:
            self.stop()

    def stop(self):
        self.__is_alive = False
        self.__data_generator.stop()
        self.__strategy_engine.stop()
        self.logger.info("<%s>策略运算停止" % self._config["name"])

    def get_output(self):
        return self.__strategy.get_output()

    def get_setting(self):
        return self._config.to_dict()

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
    import signal
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
    file = "testcode10.py"
    file = "testcode22.py"
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test', file)
    with codecs.open(path, 'r', 'utf-8') as f:
        code = f.read()
    config = BfConfig(user='10032', name=file.split(".")[0], account="mb000004296",
                      password="Morrisonwudi520", time_frame='M1', symbols=['EURUSD'],
                      trading_mode=TradingMode.on_bar)
    # config = BfConfig(user='10032', name=file.split(".")[0], account="mb000000949",
    #                   password="trq8075667", time_frame='M1', symbols=['EURUSD'],
    #                   trading_mode=TradingMode.on_bar)
    runtime_signal = RuntimeSignal()
    runtime_signal.code = code
    runtime_signal.set_config(config)
    runtime_signal.init()
    set_handle(runtime_signal.logger)


    def terminate(signum, frame):
        print("terminate")
        runtime_signal.stop()

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    runtime_signal.start()
