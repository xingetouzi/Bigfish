# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:41:04 2015

@author: BurdenBear
"""
import gc
import logging

from Bigfish.config import *
from Bigfish.core import TickDataGenerator, StrategyEngine, Strategy
from Bigfish.data.bf_config import BfConfig
from Bigfish.event.event import Event, EVENT_FINISH
from Bigfish.performance.performance import StrategyPerformanceManagerOnline
from Bigfish.utils.log import LoggerInterface
from Bigfish.utils.memory_profiler import profile
from Bigfish.utils.timer import Timer

if MEMORY_DEBUG:
    import sys


class RuntimeSignal(LoggerInterface):
    def __init__(self, user, name, code, symbols=None, time_frame=None):
        super().__init__()
        self.__config = {'user': user, 'name': name, 'symbols': symbols, 'time_frame': time_frame}
        self.__code = code
        self.__strategy = None
        self.__strategy_engine = None
        self.__data_generator = None
        self.__strategy_parameters = None
        self._logger = None
        self.__performance_manager = None
        self.__timer = Timer()
        self.__is_alive = False
        self.__initialized = False

    def init(self):
        if self.__initialized:
            return True
        bf_config = BfConfig(**self.__config)
        self.__strategy_engine = StrategyEngine(is_backtest=False, **self.__config)
        self.__strategy = Strategy(self.__strategy_engine, code=self.__code, logger=self._logger, **self.__config)
        self.__strategy_engine.add_strategy(self.__strategy)
        self.__data_generator = TickDataGenerator(bf_config,
                                                  lambda x: self.__strategy_engine.put_event(x.to_event()),
                                                  lambda: self.__strategy_engine.put_event(Event(EVENT_FINISH)))
        self.__initialized = True

    def set_config(self, **kwargs):
        self.__config.update(kwargs)

    def set_logger(self, logger):
        self._logger = logger

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
            if not self.__initialized:
                self.init()
            gc.collect()
            self.__is_alive = True
            if paras is not None:
                self.__strategy.set_parameters(paras)
            self.__strategy_engine.start()
            self.__data_generator.start()
            if refresh:
                self.__performance_manager = self.__strategy_engine.wait(self.__get_performance_manager)
                self.__data_generator.stop()
                if MEMORY_DEBUG:
                    print('gb:\n%s' % sys.getsizeof(gc.garbage))  # 写日志，计算垃圾占用的内存等
                    gb_log = {}
                    for gb in gc.garbage:
                        type_ = type(gb)
                        if type_ not in gb_log:
                            gb_log[type_] = 0
                        gb_log[type_] += sys.getsizeof(gb)
                    print(gb_log)
                result = self.__performance_manager
            else:
                result = self.__strategy_engine.wait()
            self.log(self.__timer.time("策略运算完成，耗时:{0}"), logging.INFO)
            return result
        except Exception as e:
            self.stop()
            raise e

    def stop(self):
        self.__is_alive = False
        self.__timer.reset()
        self.__data_generator.stop()
        self.__strategy_engine.stop()

    def __get_performance_manager(self):
        # TODO 加入回测是否运行的判断
        if False:
            raise ValueError('please run the backtest first')
        return StrategyPerformanceManagerOnline(self.__strategy_engine.get_profit_records(),
                                                self.__strategy_engine.get_deals(),
                                                self.__strategy_engine.get_positions(),
                                                self.__strategy_engine.symbol_pool,
                                                **self.__config)

    def get_profit_records(self):
        return self.__strategy_engine.get_profit_records()

    def get_performance(self):
        return self.__performance_manager.get_performance()

    def get_output(self):
        return self.__strategy.get_output()

    def get_setting(self):
        setting = self.__config.copy()
        return setting

    def get_parameters(self):
        if self.__strategy_parameters is None:
            temp = self.__strategy.get_parameters()
            for handle_name in temp.keys():
                for para_name, values in temp[handle_name].items():
                    temp[handle_name][para_name] = {'default': values, 'type': str(type(values))}
            self.__strategy_parameters = temp
        return self.__strategy_parameters

    def time(self, *args):
        return self.__timer.time(*args)


if __name__ == '__main__':
    from Bigfish.store.directory import UserDirectory
    from Bigfish.utils.ligerUI_util import DataframeTranslator
    import codecs
    import time


    def get_first_n_lines(string, n):
        lines = string.splitlines()
        n = min(n, len(lines))
        return '\n'.join(lines[:n])


    start_time = time.time()
    with codecs.open('../test/testcode1.py', 'r', 'utf-8') as f:
        code = f.read()
    user = '10032'
    backtest = RuntimeSignal(user, 'test', code, ['EURUSD'], 'M15')
    # print(backtest.progress)
    backtest.start()
    performance = backtest.get_performance()  # 获取策略的各项指标
    translator = DataframeTranslator()
    user_dir = UserDirectory(user)
