# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:41:04 2015

@author: BurdenBear
"""
import gc

from Bigfish.config import *
from Bigfish.core import DataGenerator, StrategyEngine, Strategy
from Bigfish.data.bf_config import BfConfig
from Bigfish.event.event import Event, EVENT_FINISH
from Bigfish.performance.performance import StrategyPerformanceManagerOnline
from Bigfish.utils.common import get_datetime
from Bigfish.utils.log import LoggerInterface
from Bigfish.utils.memory_profiler import profile
from Bigfish.utils.timer import Timer

if MEMORY_DEBUG:
    import sys


class Backtesting(LoggerInterface):
    def __init__(self, user=None, name=None, code=None, symbols=None, time_frame=None, start_time=None, end_time=None,
                 commission=0, slippage=0):
        super().__init__()
        self.__config = {'user': user, 'name': name, 'symbols': symbols, 'time_frame': time_frame,
                         'start_time': start_time, 'end_time': end_time, 'commission': commission,
                         'slippage': slippage}
        self.__code = code
        self.__strategy = None
        self.__strategy_engine = None
        self.__data_generator = None
        self.__strategy_parameters = None
        self.__performance_manager = None
        self.__timer = Timer()
        self.__is_alive = False
        self.__initialized = False
        self._logger_name = "Backtesting"

    def init(self):
        if self.__initialized:
            return None
        bf_config = BfConfig(**self.__config)
        self.__strategy_engine = StrategyEngine(is_backtest=True, **self.__config)
        self.__strategy = Strategy(self.__strategy_engine, code=self.__code, **self.__config)
        self.__strategy_engine.add_strategy(self.__strategy)
        self.__data_generator = DataGenerator(bf_config,
                                              lambda x: self.__strategy_engine.put_event(x.to_event()),
                                              lambda: self.__strategy_engine.put_event(Event(EVENT_FINISH)))
        self._logger_child = {self.__strategy_engine: "StrategyEngine",
                              self.__strategy: "Strategy",
                              self.__data_generator: "DataGenerator"}
        self.logger_name = 'Backtesting'
        if DEBUG:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.__initialized = True

    def set_config(self, **kwargs):
        self.__config.update(kwargs)

    def set_code(self, code):
        self.__code = code.replace('\t', '    ')

    @property
    def is_finished(self):
        return self.__is_alive

    @property
    def progress(self):
        if not self.__is_alive:
            return 0
        et = get_datetime(self.__config['end_time']).timestamp()
        st = get_datetime(self.__config['start_time']).timestamp()
        ct = self.__strategy_engine.current_time
        if ct:
            return min((ct - st) / (et - st) * 100, 100)
        else:
            return 0

    @profile
    def start(self, paras=None, refresh=True):
        """

        :param paras:
        :param refresh: True表示刷新绩效且需要释放资源，即用户一个完整的请求已经结束；False的情况主要是参数优化时批量运行回测。
        """
        self.logger.info("<%s>策略运算开始" % self.__config['name'])
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
        self.logger.info(self.__timer.time("<%s>策略运算完成，耗时:{0}" % self.__config['name']))
        return result

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
                                                self.__strategy_engine.get_positions())

    def get_profit_records(self):
        return self.__strategy_engine.get_profit_records()

    def get_performance(self):
        return self.__performance_manager.get_performance()

    def get_output(self):
        return self.__strategy.get_output()

    def get_setting(self):
        setting = self.__config.copy()
        setting.pop('user')
        return setting

    def time(self, *args):
        return self.__timer.time(*args)


if __name__ == '__main__':
    import time
    import os
    import codecs
    import logging
    import sys


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
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test', 'IKH_testCase.py')
    with codecs.open(path, 'r', 'utf-8') as f:
        code = f.read()
    user = '10032'  # 用户名
    name = 'test'  # 策略名
    backtest = Backtesting()
    backtest.set_code(code)
    config = dict(user=user, name='test', symbols=['EURUSD'], time_frame='M1', start_time='2015-01-01',
                  end_time='2015-01-03')
    backtest.set_config(**config)
    backtest.init()
    handle = set_handle(backtest.logger)
    # print(backtest.progress)
    backtest.start()
    performance = backtest.get_performance()  # 获取策略的各项指标
    # translator = DataframeTranslator()
    # user_dir = UserDirectory(user)
    # print(user_dir.get_sys_func_list())
    print(backtest.get_profit_records())  # 获取浮动收益曲线
    # print(backtest.get_parameters())  # 获取策略中的参数（用于优化）
    # print(performance._dict_name)
    # for k, v in performance.__dict__.items():
    #     print("%s\n%s" % (k, v))
    # print('trade_info:\n%s' % performance._manager.trade_info)
    # print('trade_summary:\n%s' % performance.trade_summary)
    print('trade_details:\n%s' % performance.trade_details)
    # print(translator.dumps(performance._manager.trade_info))
    # print(translator.dumps(performance.trade_details))
    # print('strategy_summary:\n%s' % performance.strategy_summary)
    # print('optimize_info:\n%s' % performance.optimize_info)
    # print('info_on_home_page\n%s' % performance.info_on_home_page())
    # print(performance.get_factor_list())
    # print(performance.yield_curve)
    # print('ar:\n%s' % performance.ar)  # 年化收益率
    # print('risk_free_rate:\n%s' % performance._manager.risk_free_rate)  # 无风险收益率
    # print('volatility:\n%s' % performance.volatility)  # 波动率
    # print('sharpe_ratio:\n%s' % performance.sharpe_ratio)  # sharpe比率
    # print('max_drawdown:\n%s' % performance.max_drawdown)  # 最大回测
    # print('trade_position\n%s' % performance.trade_positions)  # 交易仓位
    # print(time.time() - start_time)
    # print('output:\n%s' % get_first_n_lines(backtest.get_output(), 100))
    # print(time.time() - start_time)
    # print(backtest.progress)
    # print(performance.trade_details)
    # print(Strategy.API_FUNCTION)
    # print(Strategy.API_VARIABLES)
    # start_time = time.time()
    # # paras = {
    # #     'handle': {'TakeProfit': {'start': 46, 'end': 54, 'step': 1},
    # #                'StopLoss': {'start': 96, 'end': 104, 'step': 1}
    # #                }
    # # }
    # paras = {
    #     'handle': {'fastlength': {'start': 6, 'end': 14, 'step': 1},
    #                'slowlength': {'start': 16, 'end': 24, 'step': 1}
    #                }
    # }
    # optimize = backtest.optimize(paras, None, None)
    # print('optimize\n%s' % optimize)
    # print("优化完成，耗时:{0} seconds".format(time.time() - start_time))
