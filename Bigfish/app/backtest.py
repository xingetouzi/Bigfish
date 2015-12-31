# -*- coding: utf-8 -*-
"""
Created on Wed Nov 25 20:41:04 2015

@author: BurdenBear
"""

from Bigfish.core import DataGenerator, StrategyEngine, Strategy
from Bigfish.models.performance import StrategyPerformanceManagerOffline
from Bigfish.utils.quote import Bar
from Bigfish.utils.common import get_datetime
from functools import partial
import tushare as ts


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
        self.__strategy_engine.add_strategy(self.__strategy)
        self.__data_generator = DataGeneratorTushare(self.__strategy_engine)
        self.__performance_manager = None
        self.__strategy_engine.initialize()

    def start(self):
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


if __name__ == '__main__':
    from Bigfish.models.model import User
    with open('../test/testcode2.py') as f:
        code = f.read()
    backtest = Backtesting(User('10032'), 'test', code)
    backtest.start()
    print(backtest.get_profit_records())
    performance = backtest.get_performance()
    print(performance.ar)
    print(performance.risk_free_rate)
    print(performance.volatility)
    print(performance.sharpe_ratio)
