# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:41:04 2015

@author: BurdenBear
"""
import logging
import codecs
import gc
from functools import partial

import numpy as np
import pandas as pd

from Bigfish.config import *
from Bigfish.core import DataGenerator, StrategyEngine, Strategy
from Bigfish.models.performance import StrategyPerformanceManagerOnline
from Bigfish.models.quote import Bar
from Bigfish.utils.common import get_datetime
from Bigfish.utils.memory_profiler import profile
from Bigfish.utils.timer import Timer
from Bigfish.utils.log import LoggerInterface

if MEMORY_DEBUG:
    import sys


def _get_bar_from_dataframe(symbol, time_frame, data):
    bar = Bar(symbol)
    bar.time_frame = time_frame
    for field in ['open', 'high', 'low', 'close', 'volume']:
        setattr(bar, field, data[field])
    bar.timestamp = get_datetime(data.name).timestamp()
    return bar


def _get_bar_from_dict(symbol, time_frame, data):
    bar = Bar(symbol)
    bar.time_frame = time_frame
    for field in ['open', 'high', 'low', 'close', 'volume']:
        setattr(bar, field, data[field])
    bar.timestamp = data['ctime']
    return bar


if DATABASE == 'tushare':
    import tushare as ts


    class DataGeneratorTushare(DataGenerator):
        def _get_data(self, symbol, time_frame, start_time=None, end_time=None):
            if time_frame == 'D1':
                data = self.with_time_cost_count(ts.get_hist_data)(symbol, start_time, end_time)
                return data.apply(partial(_get_bar_from_dataframe, symbol, time_frame), axis=1).tolist()
            else:
                raise ValueError


    data_generator_default = DataGeneratorTushare
elif DATABASE == 'mongodb':
    import Bigfish.data.forex_data as fx_mongo


    class DataGeneratorMongoDB(DataGenerator):

        def _get_data(self, symbol, time_frame, start_time=None, end_time=None):
            data = self.with_time_cost_count(fx_mongo.get_period_bars)(symbol, time_frame,
                                                                       get_datetime(start_time).timestamp(),
                                                                       get_datetime(end_time).timestamp())
            result = list(map(partial(_get_bar_from_dict, symbol, time_frame), data))
            data.clear()
            return result


    data_generator_default = DataGeneratorMongoDB
elif DATABASE == 'mysql':
    if ASYNC:
        from Bigfish.trial.twisted_server import TwistAsyncDataGenerator

        data_generator_default = TwistAsyncDataGenerator
    else:
        import Bigfish.data.mysql_forex_data as fx_mysql


        class DataGeneratorMysql(DataGenerator):
            @profile
            def _get_data(self, symbol, time_frame, start_time=None, end_time=None):
                data = self.with_time_cost_count(fx_mysql.get_period_bars)(symbol, time_frame,
                                                                           get_datetime(start_time).timestamp(),
                                                                           get_datetime(end_time).timestamp())
                result = list(map(partial(_get_bar_from_dict, symbol, time_frame), data))
                data.clear()
                return result


        data_generator_default = DataGeneratorMysql


class Backtesting(LoggerInterface):
    dg_cls = data_generator_default

    def __init__(self, user, name, code, symbols=None, time_frame=None, start_time=None, end_time=None, commission=0,
                 slippage=0):
        super().__init__()
        self.__config = {'user': user, 'name': name, 'symbols': symbols, 'time_frame': time_frame,
                         'start_time': start_time, 'end_time': end_time, 'commission': commission,
                         'slippage': slippage}
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
        self.__strategy_engine = StrategyEngine(is_backtest=True, **self.__config)
        self.__strategy = Strategy(self.__strategy_engine, code=self.__code, logger=self._logger, **self.__config)
        self.__strategy_engine.add_strategy(self.__strategy)
        self.__data_generator = self.dg_cls(self.__strategy_engine, logger=self._logger, timer=self.__timer)
        self.__initialized = True

    @classmethod
    def set_data_generator(cls, data_generator):
        cls.dg_cls = data_generator

    def set_config(self, **kwargs):
        self.__config.update(kwargs)

    def set_logger(self, logger):
        self._logger = logger

    @property
    def is_finished(self):
        return self.__is_alive

    @property
    def progress(self):
        if not self.__initialized:
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
        if not self.__initialized:
            self.init()
        gc.collect()
        self.__is_alive = True
        if paras is not None:
            self.__strategy.set_parameters(paras)
        self.__strategy_engine.start()
        self.__data_generator.start(**self.__config)
        self.log(self.__timer.time("数据回放完成，耗时:{0}"), logging.INFO)
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
            result = self.__strategy_engine.wait(self.__get_performance_manager)
        self.log(self.__timer.time("策略运算完成，耗时:{0}"), logging.INFO)
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
        setting.pop('user')
        return setting

    @staticmethod
    def get_optimize_goals():
        return {'net_profit': '净利'}

    @staticmethod
    def get_optimize_types():
        return {'enumerate': '枚举', 'genetic': '遗传'}

    def get_parameters(self):
        if self.__strategy_parameters is None:
            temp = self.__strategy.get_parameters()
            for handle_name in temp.keys():
                for para_name, values in temp[handle_name].items():
                    temp[handle_name][para_name] = {'default': values, 'type': str(type(values))}
            self.__strategy_parameters = temp
        return self.__strategy_parameters

    def _enumerate_optimize(self, ranges, goal, num):
        stack = []
        range_length = []
        parameters = {}
        result = []
        head_index = []

        def get_range(range_info):
            return np.arange(range_info['start'], range_info['end'] + range_info['step'], range_info['step'])

        for handle, paras in ranges.items():
            parameters[handle] = {}
            for para, value in paras.items():
                range_value = get_range(value)
                stack.append({'handle': handle, 'para': para, 'range': range_value})
                head_index.append('%s(%s)' % (para, handle))
                range_length.append(len(range_value))
        n = len(stack)
        index = [-1] * n
        head = [0] * n

        def set_paras(n, handle=None, para=None, range=None):
            nonlocal parameters, head, index
            parameters[handle][para] = head[n] = range[index[n]]

        i = 0
        finished = False
        while 1:
            index[i] += 1
            while index[i] >= range_length[i]:
                if i == 0:
                    finished = True
                    break
                index[i] = -1
                i -= 1
                index[i] += 1
            if finished:
                break
            set_paras(i, **stack[i])
            if i == n - 1:
                performance_manager = self.start(parameters, refresh=False)
                head = pd.Series(head, index=head_index)
                optimize_info = performance_manager.get_performance().optimize_info.copy()
                target = optimize_info[goal]
                del optimize_info[goal]
                result.append(pd.concat([head, pd.Series([target], index=[goal]), optimize_info]))
            else:
                i += 1
        self.__data_generator.stop()  # 释放数据资源
        output = pd.DataFrame(result).sort_values(goal, ascending=False)
        result.clear()  # 释放资源
        output.index.name = '_'
        output = output.iloc[:num]
        return output

    def _genetic_optimize(self, ranges, goal):
        pass

    def optimize(self, ranges, type, goal, num=50):
        if not ranges:
            return
        if type is None:
            type = "enumerate"
        # TODO 不要使用硬编码
        if goal is None:
            goal = "净利($)"
        goal = "净利($)"
        optimizer = getattr(self, '_%s_optimize' % type)
        return optimizer(ranges, goal, num)

    def time(self, *args):
        return self.__timer.time(*args)


if __name__ == '__main__':
    from Bigfish.store.directory import UserDirectory
    from Bigfish.utils.ligerUI_util import DataframeTranslator
    import time


    def get_first_n_lines(string, n):
        lines = string.splitlines()
        n = min(n, len(lines))
        return '\n'.join(lines[:n])


    start_time = time.time()
    with codecs.open('../test/testcode4.py', 'r', 'utf-8') as f:
        code = f.read()
    user = '10032'
    backtest = Backtesting(user, 'test', code, ['USDJPY'], 'M15', '2015-01-01', '2015-12-01')
    print(backtest.progress)
    backtest.start()
    translator = DataframeTranslator()
    user_dir = UserDirectory(user)
    # print(user_dir.get_sys_func_list())
    print(backtest.get_profit_records())  # 获取浮动收益曲线
    # print(backtest.get_parameters())  # 获取策略中的参数（用于优化）
    performance = backtest.get_performance()  # 获取策略的各项指标
    # print('trade_info:\n%s' % performance._manager.trade_info)
    # print('trade_summary:\n%s' % performance.trade_summary)
    # print('trade_details:\n%s' % performance.trade_details)
    # print(translator.dumps(performance._manager.trade_info))
    # print(translator.dumps(performance.trade_details))
    # print('strategy_summary:\n%s' % performance.strategy_summary)
    # print('optimize_info:\n%s' % performance.optimize_info)
    # print('info_on_home_page\n%s' % performance.get_info_on_home_page())
    # print(performance.get_factor_list())
    print(performance.yield_curve)
    # print('ar:\n%s' % performance.ar)  # 年化收益率
    # print('risk_free_rate:\n%s' % performance._manager.risk_free_rate)  # 无风险收益率
    # print('volatility:\n%s' % performance.volatility)  # 波动率
    # print('sharpe_ratio:\n%s' % performance.sharpe_ratio)  # sharpe比率
    # print('max_drawdown:\n%s' % performance.max_drawdown)  # 最大回测
    # print('trade_position\n%s' % performance.trade_positions)  # 交易仓位
    # print(time.time() - start_time)
    print('output:\n%s' % get_first_n_lines(backtest.get_output(), 100))
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
