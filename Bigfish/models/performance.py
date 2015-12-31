# -*- coding: utf-8 -*-

import math
import pandas as pd
import numpy as np
from copy import deepcopy
from collections import OrderedDict
from functools import partial, wraps

import tushare
from Bigfish.models.trade import *


def cache_calculator(func):
    cache = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal cache
        if cache is None:
            cache = func(*args, **kwargs)
        return cache

    return wrapper


class LazyCal:
    def __init__(self, name, dict_):
        self.__name = name
        self.__dict_ = dict_

    def __get__(self, instance, owner):
        dict_ = getattr(instance, self.__dict_)
        if self.__name not in dict_:
            instance._manager.initialize()
            dict_[self.__name] = getattr(instance._manager, self.__name)()
        return dict_[self.__name]


class PerformanceMeta(type):
    def __init__(cls, *args, **kwargs):
        def curves(self):
            for field in self._curve_keys:
                if field not in self._curves:
                    getattr(self, field)
            return deepcopy(self._curves)

        def factors(self):
            for field in self._factor_keys:
                if field not in self._factors:
                    getattr(self, field)
            return deepcopy(self._factors)

        for field in cls._curve_keys.keys():
            setattr(cls, field, LazyCal(field, '_curves'))
        for field in cls._factor_keys.keys():
            setattr(cls, field, LazyCal(field, '_factors'))
        setattr(cls, 'curves', property(curves))
        setattr(cls, 'factors', property(factors))
        setattr(cls, 'all', property(lambda self: dict(self.curves, **self.factors)))


class Performance(metaclass=PerformanceMeta):
    _curve_keys = {}
    _factor_keys = {}

    def __init__(self, manager=None):
        self._curves = {}
        self._factors = {}
        self._manager = manager


class PerformanceManager:
    def __init__(self, cls):
        assert issubclass(cls, Performance)
        self.__cls = cls
        self.__performance = self.__cls(self)

    def get_performance(self):
        return self.__performance


class StrategyPerformance(Performance):
    """只需定义performance中应该有的属性"""
    _curve_keys = {'yield_curve': '收益曲线', 'position_curve': '持仓曲线'}
    _factor_keys = {'ar': '策略年化收益率', 'risk_free_rate': '无风险年化收益率', 'alpha': '阿尔法', 'beta': '贝塔', "sharpe_ratio": '夏普比率',
                    'volatility': '收益波动率',
                    'information_ratio': '信息比率', '': '', '': ''}

    def __init__(self, manager):
        super(StrategyPerformance, self).__init__(manager)


class StrategyPerformanceManagerOffline(PerformanceManager):
    """只需要写根据输入计算输出的逻辑"""

    # @profile
    def __init__(self, quotes, deals, positions, capital_base=100000, period=86400, num=20):  # 1day = 86400seconds
        super(StrategyPerformanceManagerOffline, self).__init__(StrategyPerformance)
        self.__quotes = quotes
        self.__deals = pd.DataFrame(list(map(lambda x: x.to_dict(), deals.values())), index=deals.keys(),
                                    columns=Deal.get_fields())  # deals in dataframe format
        self.__positions = pd.DataFrame(list(map(lambda x: x.to_dict(), positions.values())), index=positions.keys(),
                                        columns=Position.get_fields())  # positions in dataframe format
        self.__annual_factor = 250  # 年化因子
        self.initialize = partial(self.__initialize, capital_base, period, num)
        self.__initialized = False

    def __initialize(self, capital_base, period, num):
        if self.__initialized:
            return
        self.__yields = {}
        self.__yields['R'] = self.__get_yields_raw(capital_base, period, num)  # 'R' means raw
        self.__yields['D'], self.__index_daily = \
            (lambda x: (pd.DataFrame({x[0].name: x[0], 'trade_days': x[1]}).dropna(), x[0].index))(
                    (lambda x: (x - x.shift(1).fillna(method='ffill').fillna(0), x.notnull() + 0))(
                            self.__yields['R'].resample('D', how='last', label='left').apply(math.log)))
        self.__yields['W'] = self.__yields['D'].resample('W', how='sum', label='left', loffset='1D').dropna()
        self.__yields['M'] = self.__yields['D'].resample('M', how='sum', label='left', loffset='1D').dropna()
        # TODO 最后一个bfill本应是填入最近的上一个值
        self.__risk_free_rate = {}
        self.__risk_free_rate['D'] = \
            (lambda x: pd.DataFrame({'rate': x, 'days': np.ones(x.shape)}, index=x.index))(
                    (lambda x: pd.Series(x['rate'].apply(float).values, index=pd.DatetimeIndex(x['date'])).reindex(
                            self.__index_daily).fillna(method='ffill').fillna(method='bfill'))(
                            (lambda x: x[(x['deposit_type'] == '定期存款整存整取(一年)') & (x['rate'] != '--')])(
                                    tushare.get_deposit_rate())))
        self.__risk_free_rate['W'] = self.__risk_free_rate['D'].resample('W', how='sum', label='left', loffset='1D')
        self.__risk_free_rate['M'] = self.__risk_free_rate['D'].resample('M', how='sum', label='left', loffset='1D')
        self.__column_names = {}
        self.__column_names['M'] = (lambda x: OrderedDict(sorted(x.items(), key=lambda t: t[0])))(
                {1: 'month1', 3: 'month3', 6: 'month6', 12: 'month12'})
        self.__initialized = True

    # @profile
    @staticmethod
    def __get_risk_free_rate():
        return

    # @profile
    def __get_yields_raw(self, capital_base, period, num):
        interval = period // num
        time_index_calculator = lambda x: ((x - 1) // interval + 1) * interval
        self.__deals.sort('time', inplace=True)
        self.__positions.sort('time_update', inplace=True)
        self.__quotes['time_index'] = self.__quotes['close_time'].map(time_index_calculator)
        self.__deals['time_index'] = self.__deals['time'].map(time_index_calculator)
        self.__positions['time_index'] = self.__positions['time_update'].map(time_index_calculator)
        quotes = self.__quotes.groupby(['time_index', 'symbol'])['close'].last()
        deals_profit = self.__deals['profit'].fillna(0).groupby(self.__deals['time_index']).sum().cumsum()
        positions = self.__positions.groupby(['time_index', 'symbol'])[
            ['type', 'price_current', 'volume']].last()
        # TODO 检查outer连接是否会影响要交易日的计算
        float_profit = pd.DataFrame(quotes).join(positions, how='outer').fillna(method='ffill').apply(
                lambda x: (x.close - x.price_current) * x.volume * x.type, axis=1).sum(level='time_index').fillna(0)
        yields = pd.DataFrame(float_profit).join(deals_profit, how='outer').fillna(method='ffill').fillna(0).sum(
                axis=1).apply(lambda x: x / capital_base + 1)  # yields represent net yield now / capital base
        yields.index = yields.index.map(pd.datetime.fromtimestamp)
        yields.name = 'yields'
        return yields

    def position_curve(self):
        def get_point(deal, entry, volume):
            if entry == DEAL_ENTRY_IN:
                if deal.type == DEAL_TYPE_BUY:
                    return ({'type': 'point', 'x': deal.time + deal.time_msc / (10 ** 6),
                             'y': deal.price, 'color': 'buy', 'text': 'Buy %s' % volume})
                elif deal.type == DEAL_TYPE_SELL:
                    return ({'type': 'point', 'x': deal.time + deal.time_msc / (10 ** 6),
                             'y': deal.price, 'color': 'short', 'text': 'Short %s' % volume})
            elif entry == DEAL_ENTRY_OUT:
                if deal.type == DEAL_TYPE_BUY:
                    return ({'type': 'point', 'x': deal.time + deal.time_msc / (10 ** 6),
                             'y': deal.price, 'color': 'cover', 'text': 'Cover %s' % volume})
                elif deal.type == DEAL_TYPE_SELL:
                    return ({'type': 'point', 'x': deal.time + deal.time_msc / (10 ** 6),
                             'y': deal.price, 'color': 'sell', 'text': 'Sell %s' % volume})

        def get_lines(position_start, position_end):
            deal_start = self.__deals[position_start.deal]
            deal_end = self.__deals[position_end.deal]
            start_time = deal_start.time + deal_start.time_msc / (10 ** 6)
            end_time = deal_end.time + deal_end.time_msc / (10 ** 6)
            result = {'type': 'line', 'x_start': start_time, 'x_end': end_time, 'y_start': deal_start.price,
                      'y_end': deal_end.price}
            if (deal_end.type == DEAL_TYPE_BUY) ^ (deal_start.price >= deal_end.price):
                result['color'] = 'win'
            else:
                result['color'] = 'lose'

        def next_position(position):
            return (self.__positions.get(position.next_id, None))

        def prev_position(position):
            return (self.__positions.get(position.prev_id, None))

        result = []
        stack = []
        for symbol in {symbol for (symbol, _) in self.__symbols}:
            position = next_position(self.__init_positions[symbol])
            while (position != None):
                deal = self.__deals[position.deal]
                if deal.entry == DEAL_ENTRY_IN:  # open or overweight position
                    result.append(get_point(deal, DEAL_ENTRY_IN, deal.volume))
                    stack.append((position, deal.volume))
                else:
                    if deal.entry == DEAL_ENTRY_INOUT:  # reverse position
                        volume_left = deal.volume - position.volume
                        result.append(get_point(deal, DEAL_ENTRY_IN, position.volume))
                    else:  # underweight position
                        volume_left = deal.volume
                    result.append(get_point(deal, DEAL_ENTRY_OUT, volume_left))
                    while volume_left > 0:
                        position_start, volume = stack.pop()
                        result.append(get_lines(position_start, position))
                        volume_left -= volume
                    if volume_left < 0:
                        stack.append(position_start, -volume_left)
                    elif deal.entry == DEAL_ENTRY_INOUT and position.volume > 0:
                        stack.append((position, position.volume))
                position = next_position(position)
        return result

    @cache_calculator
    def ar(self):
        # TODO 可以抽象为日分析，周分析，月分析之类的
        ts = self.__yields['M']
        result = pd.DataFrame([], index=ts.index)
        calculator = lambda x: (math.exp(self.__annual_factor / x['trade_days'] * x['yields']) - 1) * 100
        for key, value in self.__column_names['M'].items():
            result[value] = pd.rolling_sum(ts, key, min_periods=key).apply(calculator, axis=1)
        return result

    def alpha(self):
        pass

    def beta(self):
        pass

    @cache_calculator
    def risk_free_rate(self):
        ts = self.__risk_free_rate['M']
        result = pd.DataFrame([], index=ts.index)
        calculator = lambda x: x['rate'] / x['days']
        for key, value in self.__column_names['M'].items():
            result[value] = pd.rolling_sum(ts, key, min_periods=key).apply(calculator, axis=1)
        return result

    @cache_calculator
    def sharpe_ratio(self):
        ar = self.ar()
        volatility = self.volatility()
        risk_free_rate = self.risk_free_rate()
        return (ar - risk_free_rate) / volatility

    @cache_calculator
    def volatility(self):
        # TODO pandas好像并不支持分组上的移动窗口函数
        # 维护avg(yields)和avg(yields^2)
        ts = (lambda x: pd.DataFrame(
                dict(yields=x['yields'].apply(math.exp),
                     yields_square=(x['yields'] * 2).apply(math.exp),
                     trade_days=x['trade_days'])))(
                self.__yields['D']).resample('M', how='sum', label='left', loffset='1D')
        result = pd.DataFrame([], index=ts.index)
        calculator = lambda x: math.sqrt(
                max((x['yields_square'] - x['yields'] ** 2 / x['trade_days']) / (
                    x['trade_days'] - (x['trade_days'] > 1)), 0)) * 100
        for key, value in self.__column_names['M'].items():
            result[value] = pd.rolling_sum(ts, key, min_periods=key).apply(calculator, axis=1)
        return result

    def information_ratio(self):
        pass

    def max_drawdown(self):
        ts = (lambda x, y, z: pd.DataFrame(dict(high=x[0], low=x[0], max_drawdown=-x[1] * (x[1] < 0))))(
                *(lambda x, y: (x[0], x[1], x[1].shift(1).fillna(0)))(
                    *(lambda x: (x, x.cursum()))(self.__yields['D']['yield'])))
        result = pd.DataFrame([], index=ts.index)
        for key, value in self.__column_names['M']:
            pass


class StrategyPerformanceManageOnline(PerformanceManager):
    pass


class AccountPerformance(Performance):
    pass


class AccountPerformanceManager(PerformanceManager):
    pass


if __name__ == '__main__':
    pass
