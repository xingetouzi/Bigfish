# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:41:04 2015

@author: BurdenBear
"""
from functools import partial

from Bigfish.core import DataGenerator, StrategyEngine, Strategy
from Bigfish.models.performance import StrategyPerformanceManagerOffline
from Bigfish.utils.quote import Bar
from Bigfish.utils.common import get_datetime
import tushare as ts
import numpy as np


def _get_bar_from_dataframe(symbol, time_frame, data):
    bar = Bar(symbol)
    bar.time_frame = time_frame
    for field in ['open', 'high', 'low', 'close', 'volume']:
        setattr(bar, field, data[field])
    bar.time = get_datetime(data.name).timestamp()
    return bar


class DataGeneratorTushare(DataGenerator):
    def _get_data(self, symbol, time_frame, start_time=None, end_time=None):
        if time_frame == 'D1':
            data = ts.get_hist_data(symbol, start_time, end_time)
            return data.apply(partial(_get_bar_from_dataframe, symbol, time_frame), axis=1).tolist()
        else:
            raise ValueError


class Backtesting:
    def __init__(self, user, name, code):
        self.__strategy_engine = StrategyEngine(backtesting=True)
        self.__strategy = Strategy(self.__strategy_engine, user, name, code)
        self.__strategy_parameters = None
        self.__strategy_engine.add_strategy(self.__strategy)
        self.__data_generator = DataGeneratorTushare(self.__strategy_engine)
        self.__performance_manager = None
        self.__strategy_engine.initialize()

    def start(self, paras=None):
        if paras is not None:
            self.__strategy.set_parameters(paras)
        self.__strategy_engine.start()
        self.__data_generator.start()
        self.__strategy_engine.wait()

    def __get_performance_manager(self):
        # TODO 加入回测是否运行的判断
        if False:
            raise ValueError('please run the backtest first')
        self.__performance_manager = StrategyPerformanceManagerOffline(self.__data_generator.get_dataframe(),
                                                                       self.__strategy_engine.get_deals(),
                                                                       self.__strategy_engine.get_positions())

    def get_profit_records(self):
        return self.__strategy_engine.get_profit_records()

    def get_performance(self):
        if self.__performance_manager is None:
            self.__get_performance_manager()
        return self.__performance_manager.get_performance()

    def get_parameters(self):
        if self.__strategy_parameters is None:
            temp = self.__strategy.get_parameters()
            for handle_name in temp.keys():
                for para_name, values in temp[handle_name].items():
                    temp[handle_name][para_name] = {'default': values, 'type': str(type(values))}
            self.__strategy_parameters = temp
        return self.__strategy_parameters

    def _enumerate_optimize(self, ranges):
        stack = []
        range_length = []
        paras = {}

        def get_range(range_info):
            return np.arange(range_info['start'], range_info['end'] + range_info['step'], range_info['step'])

        for handle, paras in ranges.items():
            paras[handle] = {}
            for para, value in ranges.items():
                range_value = get_range(value)
                stack.append({'handle': handle, 'para': para, 'range': range_value})
                range_length.append(len(range_value))

        def set_paras(paras, index, handle=None, para=None, range=None):
            paras[handle][para] = range[index]

        n = len(stack)
        index = [-1] * n
        i = 0
        finished = False
        while not finished:
            index[i] += 1
            while index[i] >= range_length[i]:
                if i == 0:
                    finished = True
                    break
                index[i] = -1
                i -= 1
            set_paras(paras, index[i], **stack[i])
            if i == n - 1:
                self.start(paras)
            else:
                i += 1

    def _genetic_optimize(self, ranges):
        pass

    def optimize(self, ranges, type):
        if not ranges:
            return
        optimizer = getattr(self, '_%s_optimize' % type)
        optimizer(ranges)


if __name__ == '__main__':
    from Bigfish.models.model import User

    with open('../test/testcode2.py') as f:
        code = f.read()
    backtest = Backtesting(User('10032'), 'test', code)
    backtest.start()
    print(backtest.get_profit_records()) #获取浮动收益曲线
    print(backtest.get_parameters())  #获取策略中的参数（用于优化）
    performance = backtest.get_performance() #获取策略的各项指标
    print('ar:\n%s' % performance.ar) #年化收益率
    print('risk_free_rate:\n%s' % performance.risk_free_rate) #无风险收益率
    print('volatility:\n%s' % performance.volatility) #波动率
    print('sharpe_ratio:\n%s' % performance.sharpe_ratio) #sharpe比率
    print('max_drawdown:\n%s' % performance.max_drawdown) #最大回测
