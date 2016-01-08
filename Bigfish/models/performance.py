# -*- coding: utf-8 -*-

import math
from copy import deepcopy
from collections import OrderedDict
from functools import partial, wraps, reduce

import pandas as pd
import numpy as np
from pandas.tseries.offsets import MonthBegin
import tushare
from Bigfish.models.trade import *
from Bigfish.utils.pandas_util import rolling_apply_2d


def cache_calculator(func, obj=None):
    cache = None

    @wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal cache

        if cache is not None:
            return cache
        if obj is not None:
            cache = getattr(obj, '_%s__%s' % (obj.__class__, __name__, func.__name__))
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
                    'volatility': '收益波动率', 'information_ratio': '信息比率', 'max_drawdown': '最大回撤',
                    'excess_return': '超额收益率'}

    @staticmethod
    def get_factor_list():
        result = {'ar': '策略年化收益率', 'sharpe_ratio': '夏普比率', 'volatility': '收益波动率', 'max_drawdown': '最大回撤'}
        return list(result.items())

    def __init__(self, manager):
        super(StrategyPerformance, self).__init__(manager)

    @property
    def factor_keys(self):
        return self._factor_keys


def get_percent_from_log(n, factor=1):
    return (math.exp(n * factor) - 1) * 100


class StrategyPerformanceManagerOffline(PerformanceManager):
    """只需要写根据输入计算输出的逻辑"""
    _column_names = {}
    _column_names['M'] = (lambda x: OrderedDict(sorted(x.items(), key=lambda t: t[0])))(
            {1: ('month1', '1个月'), 3: ('month3', '3个月'), 6: ('month6', '6个月'), 12: ('month12', '1年')})

    def __init__(self, quotes, deals, positions, capital_base=100000, period=86400, num=20):  # 1day = 86400seconds
        super(StrategyPerformanceManagerOffline, self).__init__(StrategyPerformance)
        self.__quotes_raw = quotes
        self.__deals_raw = pd.DataFrame(list(map(lambda x: x.to_dict(), deals.values())), index=deals.keys(),
                                        columns=Deal.get_fields())  # deals in dataframe format
        self.__positions_raw = pd.DataFrame(list(map(lambda x: x.to_dict(), positions.values())),
                                            index=positions.keys(),
                                            columns=Position.get_fields())  # positions in dataframe format
        self.__annual_factor = 250  # 年化因子
        self.initialize = partial(self.__initialize, capital_base, period, num)
        self.__initialized = False

    # @profile
    def __initialize(self, capital_base, period, num):
        if self.__initialized:
            return

        self.__rate_of_return = {}
        self.__rate_of_return['R'] = self.__get_rate_of_return_raw(capital_base, period, num)  # 'R' means raw
        self.__rate_of_return['D'], self.__index_daily = \
            (lambda x, y: (pd.DataFrame({x.name: x, 'trade_days': y}).dropna(), x.index))(
                    *(lambda x: (x - x.shift(1).fillna(method='ffill').fillna(0), x.notnull().astype('int')))(
                            self.__rate_of_return['R'].resample('D', how='last', label='left').apply(math.log)
                    )
            )
        self.__rate_of_return['W'] = self.__rate_of_return['D'].resample('W-MON', how='sum').dropna()
        self.__rate_of_return['M'] = self.__rate_of_return['D'].resample('MS', how='sum').dropna()
        self.__rate_of_return_percent = {}
        self.__rate_of_return_percent['D'] = \
            (lambda x: pd.DataFrame(
                    {'rate': x['rate'].apply(partial(get_percent_from_log, factor=self.__annual_factor)),
                     'trade_days': x['trade_days']}))(
                    self.__rate_of_return['D']
            )
        self.__rate_of_return_percent['W'] = self.__rate_of_return_percent['D'].resample('W-MON', how='sum').dropna()
        self.__rate_of_return_percent['M'] = self.__rate_of_return_percent['D'].resample('MS', how='sum').dropna()
        # TODO 最后一个bfill本应是填入最近的上一个值
        self.__risk_free_rate = {}
        self.__risk_free_rate['D'] = \
            (lambda x: pd.DataFrame({'rate': x, 'trade_days': np.ones(x.shape)}, index=x.index))(
                    (lambda x: pd.Series(x['rate'].apply(float).values, index=pd.DatetimeIndex(x['date'])).reindex(
                            self.__index_daily).fillna(method='ffill').fillna(method='bfill'))(
                            (lambda x: x[(x['deposit_type'] == '定期存款整存整取(一年)') & (x['rate'] != '--')])(
                                    tushare.get_deposit_rate()
                            )
                    )
            )
        self.__risk_free_rate['W'] = self.__risk_free_rate['D'].resample('W-MON', how='sum')
        self.__risk_free_rate['M'] = self.__risk_free_rate['D'].resample('MS', how='sum')
        self.__excess_return = {}
        self.__excess_return['D'] = \
            (lambda x, y: pd.DataFrame(
                    {'rate': x['rate'].apply(partial(get_percent_from_log, factor=self.__annual_factor)) - y[
                        'rate'].reindex(x.index),
                     'trade_days': x['trade_days']}))(
                    self.__rate_of_return['D'], self.__risk_free_rate['D']
            )
        self.__excess_return['W'] = self.__excess_return['D'].resample('W-MON', how='sum')
        self.__excess_return['M'] = self.__excess_return['D'].resample('MS', how='sum')
        self.__initialized = True

    def yield_curve(self):
        rate_of_return = (self.__rate_of_return['R'] - 1) * 100
        return [{'x': int(x.timestamp()), 'y': y} for x, y in zip(rate_of_return.index, rate_of_return.tolist())]

    # @profile
    def __get_rate_of_return_raw(self, capital_base, period, num):
        interval = period // num
        time_index_calculator = lambda x: ((x - 1) // interval + 1) * interval
        self.__deals_raw.sort_values('time', inplace=True)
        self.__positions_raw.sort_values('time_update', inplace=True)
        self.__quotes_raw['time_index'] = self.__quotes_raw['close_time'].map(time_index_calculator)
        self.__deals_raw['time_index'] = self.__deals_raw['time'].map(time_index_calculator)
        self.__positions_raw['time_index'] = self.__positions_raw['time_update'].map(time_index_calculator)
        quotes = self.__quotes_raw.groupby(['time_index', 'symbol'])['close'].last()
        deals_profit = self.__deals_raw['profit'].fillna(0).groupby(
                self.__deals_raw['time_index']).sum().cumsum()
        # XXX 注意初始时加入的未指明交易时间的”零“仓位的特殊处理,这里groupby中把time_index为NaN的行自动去除了
        positions = self.__positions_raw.groupby(['time_index', 'symbol'])[
            ['type', 'price_current', 'volume']].last()
        # TODO 检查outer连接是否会影响交易日的计算
        float_profit = pd.DataFrame(quotes).join(positions, how='outer').fillna(method='ffill').apply(
                lambda x: (x.close - x.price_current) * x.volume * x.type, axis=1).sum(level='time_index').fillna(0)
        rate_of_return = pd.DataFrame(float_profit).join(deals_profit, how='outer').fillna(method='ffill').fillna(
                0).sum(
                axis=1).apply(lambda x: x / capital_base + 1)  # rate_of_return represent net yield now / capital base
        rate_of_return.index = rate_of_return.index.map(pd.datetime.fromtimestamp)
        rate_of_return.name = 'rate'
        return rate_of_return

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
            deal_start = self.__deals_raw[position_start.deal]
            deal_end = self.__deals_raw[position_end.deal]
            start_time = deal_start.time + deal_start.time_msc / (10 ** 6)
            end_time = deal_end.time + deal_end.time_msc / (10 ** 6)
            result = {'type': 'line', 'x_start': start_time, 'x_end': end_time, 'y_start': deal_start.price,
                      'y_end': deal_end.price}
            if (deal_end.type == DEAL_TYPE_BUY) ^ (deal_start.price >= deal_end.price):
                result['color'] = 'win'
            else:
                result['color'] = 'lose'

        def next_position(position):
            return (self.__positions_raw.get(position.next_id, None))

        def prev_position(position):
            return (self.__positions_raw.get(position.prev_id, None))

        deal_profits = self.__quotes_raw.groupby(['close_time', 'symbol'])['close'].last().swaplevel(0, 1)
        positions = self.__positions_raw[['type', 'price_current', 'volume', 'deal']]
        deals = self.__deals_raw[['time', 'price', 'volume', 'profit', 'entry']]
        ts = pd.merge(positions, deals, how='right', left_on='deal', right_index=True, suffixes=('_p', '_d'))
        print(deals)
        print(self.__positions_raw)
        print(ts)
        """
        result = []
        stack = []
        for symbol in {symbol for (symbol, _) in self.__symbols}:
            position = next_position(self.__init_positions[symbol])
            while (position != None):
                deal = self.__deals_raw[position.deal]
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
        """

    # -----------------------------------------------------------------------------------------------------------------------
    def _roll_exp(self, sample):
        calculator = lambda x: x['rate'] / x['trade_days']
        ts = sample
        result = pd.DataFrame([], index=ts.index.rename('time'))
        for key, value in self._column_names['M'].items():
            result[value[0]] = pd.rolling_sum(ts, key).apply(calculator, axis=1)
        return result

    def _roll_std(self, sample):
        calculator = lambda x: math.sqrt(
                max((x['rate_square'] - x['rate'] * x['rate'] / x['trade_days']) / (
                    x['trade_days'] - (x['trade_days'] > 1)), 0))
        ts = (lambda x: pd.DataFrame(
                dict(rate=x['rate'],
                     rate_square=(x['rate'] * x['rate']),
                     trade_days=x['trade_days']))
              .resample('MS', how='sum'))(sample)
        result = pd.DataFrame([], index=ts.index.rename('time'))
        for key, value in self._column_names['M'].items():
            result[value[0]] = pd.rolling_sum(ts, key).apply(calculator, axis=1)
        return result

    def alpha(self):
        pass

    def beta(self):
        pass

    @cache_calculator
    # @profile
    def ar(self):
        # TODO 可以抽象为日分析，周分析，月分析之类的
        calculator = lambda x: (math.exp(self.__annual_factor / x['trade_days'] * x['rate']) - 1) * 100
        ts = self.__rate_of_return['M']
        result = pd.DataFrame([], index=ts.index.rename('time'))
        for key, value in self._column_names['M'].items():
            result[value[0]] = pd.rolling_sum(ts, key).apply(calculator, axis=1)
        return result

    @cache_calculator
    def risk_free_rate(self):
        return self._roll_exp(self.__risk_free_rate['M'])

    @cache_calculator
    # @profile
    def volatility(self):
        # TODO pandas好像并不支持分组上的移动窗口函数

        return self._roll_std(self.__rate_of_return_percent['M'])

    @cache_calculator
    def sharpe_ratio(self):
        expected = self._roll_exp(self.__excess_return['M'])
        std = self._roll_std(self.__excess_return['M'])
        return expected / std

    def sortino_ratio(self):
        pass

    def information_ratio(self):
        pass

    @cache_calculator
    # @profile
    def max_drawdown(self):
        # TODO o(nk)算法，k较大时可以利用分治做成o(nlog(n))，月分析K最大为12
        columns = ['high', 'low', 'max_drawdown']
        calculator = partial(reduce, lambda u, v: [max(u[0], v[0]), min(u[1], v[1]), min(u[2], v[2], v[1] - u[0])])
        ts = (lambda x: x.groupby(MonthBegin().rollback).apply(
                lambda df: pd.Series(calculator(df.values), index=columns)))(
                (lambda x, y, z: pd.DataFrame(
                        {'high': np.maximum(y, z), 'low': np.minimum(y, z), 'max_drawdown': x},
                        columns=columns))(
                        *(lambda x, y: (x, y, y.shift(1).fillna(0)))(
                                *(lambda x: (x['rate'] * (x['rate'] < 0), x['rate'].cumsum()))(
                                        self.__rate_of_return['D']))))
        result = pd.DataFrame([], index=ts.index.rename('time'))
        for key, value in self._column_names['M'].items():
            result[value[0]] = -(rolling_apply_2d(ts, key, calculator)['max_drawdown'].apply(get_percent_from_log))
        self._max_drawdown = -get_percent_from_log(calculator(ts.values)[2])
        print(self._max_drawdown)
        return result

    @property
    def column_names(self):
        return self._column_names


class StrategyPerformanceManageOnline(PerformanceManager):
    pass


class AccountPerformance(Performance):
    pass


class AccountPerformanceManager(PerformanceManager):
    pass


if __name__ == '__main__':
    pass
