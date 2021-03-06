# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:41:04 2015

@author: BurdenBear
"""
import gc
import logging
from Bigfish.config import *
from Bigfish.core import DataGenerator, StrategyEngine, Strategy
from Bigfish.event.event import Event, EVENT_FINISH
from Bigfish.performance.performance import StrategyPerformanceManagerOnline
from Bigfish.utils.common import get_datetime
from Bigfish.utils.log import LoggerInterface
from Bigfish.utils.memory_profiler import profile
from Bigfish.utils.timer import Timer
from Bigfish.models.base import RunningMode, TradingMode
from Bigfish.models.config import BfConfig, ConfigInterface

if MEMORY_DEBUG:
    import sys


class Backtesting(LoggerInterface, ConfigInterface):
    def __init__(self):
        LoggerInterface.__init__(self)
        ConfigInterface.__init__(self)
        self.__code = None
        self.__strategy = None
        self.__strategy_engine = None
        self.__data_generator = None
        self.__strategy_parameters = None
        self.__performance_manager = None
        self.__timer = Timer()
        self.__is_alive = False
        self.__initialized = False
        self.logger_name = "Backtesting"

    def init(self):
        if self.__initialized:
            return None
        assert self._config is not None  # 判断初始化前是否设置好了基本参数
        self.__strategy_engine = StrategyEngine(parent=self)
        self.__strategy = Strategy(self.__strategy_engine, self.__code, parent=self)
        self.__strategy_engine.add_strategy(self.__strategy)
        self.__data_generator = DataGenerator(lambda x: self.__strategy_engine.put_event(x.to_event()),
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
        self._config.running_mode = RunningMode.backtest

    def set_code(self, code):
        assert isinstance(code, str)
        self.__code = code.replace('\t', '    ')

    @property
    def is_finished(self):
        return self.__is_alive

    @property
    def progress(self):
        if not self.__is_alive:
            return 0
        et = get_datetime(self._config['end_time']).timestamp()
        st = get_datetime(self._config['start_time']).timestamp()
        ct = self.__strategy_engine.current_time
        if ct:
            return min((ct - st) / (et - st) * 100, 100)
        else:
            return 0

    @property
    def max_margin(self):
        return self.__strategy_engine.max_margin

    @profile
    def start(self, paras=None, refresh=True):
        """

        :param paras:
        :param refresh: True表示刷新绩效且需要释放资源，即用户一个完整的请求已经结束；False的情况主要是参数优化时批量运行回测。
        """
        self.logger.info("<%s>策略运算开始" % self._config['name'])
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
        self.logger.info(self.__timer.time("<%s>策略运算完成，耗时:{0}" % self._config['name']))
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
        return StrategyPerformanceManagerOnline(self.__strategy_engine.profit_records,
                                                self.__strategy_engine.deals,
                                                self.__strategy_engine.positions)

    def get_profit_records(self):
        return self.__strategy_engine.profit_records

    def get_performance(self):
        return self.__performance_manager.get_performance()

    def get_output(self):
        return self.__strategy.get_output()

    def get_setting(self):
        return self._config.to_dict()

    def time(self, *args):
        return self.__timer.time(*args)


if __name__ == '__main__':
    import time
    import os
    import codecs
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
    file = "testcode10.py"
    # file = 'IKH_testCase.py'
    # file = "boom.py"
    file = "margin_error.py"
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test', file)
    with codecs.open(path, 'r', 'utf-8') as f:
        code = f.read()
    user = '10032'  # 用户名
    name = 'test'  # 策略名
    backtest = Backtesting()
    backtest.set_code(code)
    config = BfConfig(user=user, name='test', symbols=['USDJPY'], time_frame='M5', start_time='2014-01-01',
                      end_time='2015-05-01', trading_mode=TradingMode.on_tick)
    backtest.set_config(config)
    backtest.init()
    handle = set_handle(backtest.logger)
    # print(backtest.progress)
    backtest.start()
    performance = backtest.get_performance()  # 获取策略的各项指标
    # translator = DataframeTranslator()
    # user_dir = UserDirectory(user)
    # print(user_dir.get_sys_func_list())
    # print(backtest.get_profit_records())  # 获取浮动收益曲线
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
    # print('risk_free_rate:\n%s' % performance._manager.risk_free_rate)  # 无风险收益率
    print('ar_compound:\n%s' % performance.ar_compound)
    print('ar:\n%s' % performance.ar)  # 年化收益率
    print('volatility_compound:\n%s' % performance.volatility_compound)
    print('volatility:\n%s' % performance.volatility)  # 波动率
    print('sharpe_ratio_compound:\n%s' % performance.sharpe_ratio_compound)  # sharpe比率
    print('sharpe_ratio:\n%s' % performance.sharpe_ratio)  # sharpe比率
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
    from Bigfish.app.sharpe_calculator import SharpeCalculator
    start_time = "2015-02-01"
    end_time = "2015-05-01"
    profit_records = backtest.get_profit_records()
    sc = SharpeCalculator(profit_records)
    print(backtest.max_margin)
    pm = sc.get_performance(start_time, end_time)
    p = pm.get_performance()
    print("ar_compound:\n%s" % p.ar_compound)
    print("volatility_compound:\n%s" % p.volatility_compound)
    print(sc.get_sharpe(start_time, end_time, simple=backtest.max_margin < config.capital_base))
    from matplotlib import pyplot, dates
    from datetime import datetime
    si, ei = sc.get_index(start_time, end_time)
    records = profit_records[si: ei]
    profits = list(map(lambda x: x['y'], records))
    datetimes = list(map(lambda x: datetime.fromtimestamp(x['x']), records))
    pyplot.plot_date(dates.date2num(datetimes), profits, linestyle='-')
    x_text = pyplot.xlabel("时间")
    y_text = pyplot.ylabel("收益率(%)")
    t_text = pyplot.title("浮动盈亏")
    pyplot.setp(t_text, size='large', color='r')
    # setp(text, size='medium', name='courier', weight='bold',color='b')
    pyplot.setp(x_text, size='medium', name='courier', weight='bold', color='g')
    pyplot.setp(y_text, size='medium', name='helvetica', weight='light', color='b')
    pyplot.show()
    pyplot.grid(True)
