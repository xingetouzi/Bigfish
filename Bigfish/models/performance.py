# -*- coding: utf-8 -*-

import math
from copy import deepcopy
from collections import OrderedDict
from functools import partial, wraps, reduce
from weakref import WeakKeyDictionary, proxy

import pandas as pd
import numpy as np
from pandas.tseries.offsets import MonthBegin
import tushare
from Bigfish.models.trade import *
from Bigfish.utils.pandas_util import rolling_apply_2d

# ——————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
pd.set_option('display.precision', 12)
pd.set_option('display.width', 200)
# ——————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
# math utils
FLOAT_ERR = 1e-7


class DataFrameExtended(pd.DataFrame):
    def __init__(self, data=None, index=None, columns=None, dtype=None,
                 copy=False, total=None, title=''):
        super().__init__(data=data, index=index, columns=columns, dtype=dtype, copy=copy)
        self.__total = total
        self.__title = title

    def __get_total(self):
        return self.__total

    def __set_total(self, value):
        self.__total = value

    def __get_title(self):
        return self.__title

    def __set_title(self, value):
        self.__title = value

    total = property(__get_total, __set_total)
    titie = property(__get_title, __set_title)


def cache_calculator(func):
    # XXX 由于python的垃圾回收机制只有引用计数，不像java一样也使用缩圈的拓扑算法，需要用弱引用防止内存泄漏,弱引用字典还会在垃圾回收发生时自动删除字典中所对应的键值对
    cache = WeakKeyDictionary()

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        nonlocal cache
        if self not in cache:
            cache[self] = func(self, *args, **kwargs)
        return cache[self]

    return wrapper


class Performance:
    _manager = None  # 避免循环引用
    _dict = {}

    def __init__(self, manager=None):
        self._manager = manager

    def __getattr__(self, item):
        if item in self._dict:
            return getattr(self._manager, item)
        else:
            raise AttributeError


class PerformanceManager:
    def __init__(self, cls):
        assert issubclass(cls, Performance)
        self.__cls = cls
        self.__performance = self.__cls(self)

    def get_performance(self):
        return self.__performance


class StrategyPerformance(Performance):
    """只需定义performance中应该有的属性"""

    _dict = {'yield_curve': '收益曲线'}
    __factor_info = {'ar': '策略年化收益率', 'sharpe_ratio': '夏普比率', 'volatility': '收益波动率',
                     'max_drawdown': '最大回撤'}
    __trade_info = {'trade_summary': '总体交易概要', 'trade_details': '分笔交易详情'}
    __strategy_info = {'strategy_summary': '策略绩效概要'}

    _dict.update(__factor_info)
    _dict.update(__trade_info)
    _dict.update(__strategy_info)

    @classmethod
    def get_factor_list(cls):
        return list(cls.__factor_info.items())

    @classmethod
    def get_trade_info_list(cls):
        return list(cls.__trade_info.items())

    @classmethod
    def get_strategy_info_list(cls):
        return list(cls.__strategy_info.items())

    def __init__(self, manager):
        super(StrategyPerformance, self).__init__(manager)

    def get_info_on_home_page(self):
        return self._manager.strategy_summary['_'].to_dict()


# -----------------------------------------------------------------------------------------------------------------------
def _get_percent_from_log(n, factor=1):
    return (math.exp(n * factor) - 1) * 100


def _deal_float_error(dataframe, fill=0):
    dataframe[abs(dataframe) <= FLOAT_ERR] = fill
    return dataframe


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
        self.__capital_base = capital_base
        self.__period = period
        self.__num = num
        self.__precision = 4
        self.__cache = {}  # 用于存放将要在函数中复用的变量

    # @profile
    def __get_rate_of_return_raw(self):
        interval = self.__period // self.__num
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
                0).sum(axis=1).apply(
                lambda x: x / self.__capital_base + 1)  # rate_of_return represent net yield now / capital base
        rate_of_return.index = rate_of_return.index.map(pd.datetime.fromtimestamp)
        rate_of_return.name = 'rate'
        return rate_of_return

    @property
    @cache_calculator
    def __rate_of_return(self):
        result = {}
        result['R'] = self.__get_rate_of_return_raw()  # 'R' means raw
        result['D'], self.__index_daily = \
            (lambda x, y: (pd.DataFrame({x.name: x, 'trade_days': y}).dropna(), x.index))(
                    *(lambda x: (x - x.shift(1).fillna(method='ffill').fillna(0), x.notnull().astype('int')))(
                            result['R'].resample('D', how='last', label='left').apply(math.log)
                    )
            )
        result['W'] = result['D'].resample('W-MON', how='sum').dropna()
        result['M'] = result['D'].resample('MS', how='sum').dropna()
        return result

    @property
    @cache_calculator
    def __rate_of_return_percent(self):
        result = {}
        result['D'] = \
            (lambda x: pd.DataFrame(
                    {'rate': x['rate'].apply(partial(_get_percent_from_log, factor=self.__annual_factor)),
                     'trade_days': x['trade_days']}))(
                    self.__rate_of_return['D']
            )
        result['W'] = result['D'].resample('W-MON', how='sum').dropna()
        result['M'] = result['D'].resample('MS', how='sum').dropna()
        return result

    @property
    @cache_calculator
    def __risk_free_rate(self):
        result = {}
        result['D'] = \
            (lambda x: pd.DataFrame({'rate': x, 'trade_days': np.ones(x.shape)}, index=x.index))(
                    (lambda x: pd.Series(x['rate'].apply(float).values, index=pd.DatetimeIndex(x['date'])).reindex(
                            self.__index_daily).fillna(method='ffill').fillna(method='bfill'))(
                            (lambda x: x[(x['deposit_type'] == '定期存款整存整取(一年)') & (x['rate'] != '--')])(
                                    tushare.get_deposit_rate()
                            )
                    )
            )
        # TODO 最后一个bfill本应是填入最近的上一个值
        result['W'] = result['D'].resample('W-MON', how='sum')
        result['M'] = result['D'].resample('MS', how='sum')
        return result

    @property
    @cache_calculator
    # @profile
    def __excess_return(self):
        result = {}
        result['D'] = \
            (lambda x, y: pd.DataFrame(
                    {'rate': x['rate'].apply(partial(_get_percent_from_log, factor=self.__annual_factor)) - y[
                        'rate'].reindex(x.index),
                     'trade_days': x['trade_days']}))(
                    self.__rate_of_return['D'], self.__risk_free_rate['D']
            )
        result['W'] = result['D'].resample('W-MON', how='sum')
        result['M'] = result['D'].resample('MS', how='sum')
        return result

    @property
    @cache_calculator
    def yield_curve(self):
        rate_of_return = ((self.__rate_of_return['R'] - 1) * 100).apply(lambda x: round(x, self.__precision))
        return [{'x': int(x.timestamp()), 'y': y} for x, y in zip(rate_of_return.index, rate_of_return.tolist())]

    @property
    @cache_calculator
    def strategy_summary(self):
        trade_summary = self.trade_summary
        net_profit = trade_summary['total']['平均净利'] * trade_summary['total']['总交易数']
        winning = trade_summary['total']['平均盈利'] * trade_summary['total']['盈利交易数']
        losing = trade_summary['total']['平均亏损'] * trade_summary['total']['亏损交易数']
        rate_of_return = self.__rate_of_return['R'].tail(1).sum()
        annual_rate_of_return = _get_percent_from_log(math.log(rate_of_return), self.__annual_factor)
        max_potential_losing = (self.__rate_of_return['R'].min() - 1) * 100
        max_losing = trade_summary['total']['最大亏损']
        result = pd.DataFrame({
            '净利': net_profit,
            '盈利': winning,
            '亏损': losing,
            '账户资金收益率': (rate_of_return - 1) * 100,
            '年化收益率': annual_rate_of_return,
            '最大回撤': self.max_drawdown.total,
            '策略最大潜在亏损': max_potential_losing,
            '平仓交易最大亏损': max_losing,
            '最大潜在亏损收益比': net_profit / max_potential_losing,
        }, index=['_']).T
        result.index.name = '_'
        return result

    @property
    @cache_calculator
    def trade_info(self):
        positions = self.__positions_raw[['symbol', 'type', 'price_current', 'volume']]
        deals = self.__deals_raw[
            ['position', 'time', 'type', 'price', 'volume', 'profit', 'entry', 'strategy', 'handle']]
        trade = pd.merge(deals, positions, how='left', left_on='position', right_index=True, suffixes=('_d', '_p'))
        # XXX dataframe的groupby方法计算结果是dataframe的视图，所以当dataframe的结构没有变化，groupby的结果依然可用
        trade_grouped = trade.groupby('symbol')
        self.__cache['trade_grouped_by_symbol'] = trade_grouped
        trade['trade_number'] = trade_grouped.apply(
                lambda x: pd.DataFrame((x['volume_p'] == 0).astype(int).cumsum().shift(1).fillna(0) + 1, x.index))
        # TODO 在多品种交易下进行测试
        temp = trade_grouped['trade_number'].last().cumsum().shift(1).fillna(0)
        trade['trade_number'] = trade['trade_number'] + trade['symbol'].apply(lambda x: temp[x])
        temp = trade.groupby('trade_number')['type_p'].first()
        trade['trade_type'] = trade['trade_number'].apply(lambda x: temp[x])
        trade['profit'] = trade['profit'].fillna(0)
        trade.index.name = 'deal_number'
        return trade

    @property
    @cache_calculator
    def trade_summary(self):
        columns = ['total', 'long_position', 'short_position']
        result = pd.DataFrame(index=columns)
        result.index.name = ''
        trade = {}
        trade_grouped = {}
        trade['total'] = self.trade_info
        trade['long_position'] = trade['total'].query('trade_type>0')
        trade['short_position'] = trade['total'].query('trade_type<0')
        for key in columns:
            trade_grouped[key] = trade[key].groupby(['symbol', 'trade_number'])
        result['总交易数'] = [trade_grouped[key].ngroups for key in columns]
        last_trade = trade['total'].tail(1)
        if (last_trade.volume_p == 0).bool():
            result['总交易数']['total'] -= 1
            if (last_trade.type_p > 0).bool():
                result['未平仓交易数'] = [1, 1, 0]
                result['总交易数']['long_position'] -= 1
            else:
                result['未平仓交易数'] = [1, 0, 1]
                result['总交易数']['short_position'] -= 1
        else:
            result['未平仓交易数'] = [0, 0, 0]
        profits = [trade_grouped[key]['profit'].sum().dropna() for key in columns]
        winnings = list(map(lambda x: x[x > 0], profits))
        losings = list(map(lambda x: x[x < 0], profits))
        result['盈利交易数'] = list(map(len, winnings))
        result['亏损交易数'] = list(map(len, losings))
        result['胜率'] = result['盈利交易数'] / result['总交易数']
        result['平均净利'] = list(map(lambda x: x.mean(), profits))
        result['平均盈利'] = list(map(lambda x: x.mean(), winnings))
        result['平均亏损'] = list(map(lambda x: x.mean(), losings))
        result['平均盈利/平均亏损'] = result['平均盈利'] / -result['平均亏损']
        result['最大盈利'] = list(map(lambda x: x.max(), profits))
        result['最大亏损'] = list(map(lambda x: x.min(), profits))
        return result.T

    @property
    @cache_calculator
    def trade_details(self):
        columns = ['symbol', 'trade_type', 'entry', 'time', 'volume_d', 'price', 'volume_p', 'price_current']
        trade = (
            lambda x: DataFrameExtended(x.pivot_table(index=[x['symbol'], 'trade_number', x.index], values=columns)))(
                self.trade_info)
        trade['entry'] = trade['entry'].map(lambda x: '入场(加仓)' if x == 0 else '出场(减仓)')
        trade['trade_type'] = trade['trade_type'].map(lambda x: '空头' if x < 0 else '多头')
        trade['time'] = trade['time'].map(pd.datetime.fromtimestamp)
        return trade
        # quotes = self.__quotes_raw.groupby(['close_time', 'symbol'])[['close']].last().swaplevel(0, 1)
        # print(quotes)
        # trade = self.trade_info.groupby(['symbol', 'trade_number'])
        # pd.merge(trade, quotes, how='outer', left_on='time', right_index=True)
        # return pd.DataFrame()

    @property
    @cache_calculator
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
            return self.__positions_raw.get(position.next_id, None)

        def prev_position(position):
            return self.__positions_raw.get(position.prev_id, None)

        deal_profits = self.__quotes_raw.groupby(['close_time', 'symbol'])['close'].last().swaplevel(0, 1)
        trade, _ = self.trade_info
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
        result = DataFrameExtended([], index=ts.index.rename('time'))
        for key, value in self._column_names['M'].items():
            result[value[0]] = pd.rolling_sum(ts, key).apply(calculator, axis=1)
        result.total = calculator(ts.sum())
        return result

    def _roll_std(self, sample):
        calculator = lambda x: (x['rate_square'] - x['rate'] * x['rate'] / x['trade_days']) \
                               / (x['trade_days'] - (x['trade_days'] > 1))
        ts = (lambda x: pd.DataFrame(
                dict(rate=x['rate'],
                     rate_square=(x['rate'] * x['rate']),
                     trade_days=x['trade_days']))
              .resample('MS', how='sum'))(sample)
        result = DataFrameExtended([], index=ts.index.rename('time'))
        for key, value in self._column_names['M'].items():
            # XXX 开根号运算会将精度缩小一半，必须在此之前就处理先前浮点运算带来的浮点误差
            result[value[0]] = _deal_float_error(pd.rolling_sum(ts, key).apply(calculator, axis=1)) ** 0.5
        result.total = (lambda x: int(abs(x) > FLOAT_ERR) * x)(calculator(ts.sum())) ** 0.5
        return _deal_float_error(result)

    def alpha(self):
        pass

    def beta(self):
        pass

    @property
    @cache_calculator
    # @profile
    def ar(self):
        # TODO 可以抽象为日分析，周分析，月分析之类的
        calculator = lambda x: _get_percent_from_log(x['rate'], factor=self.__annual_factor / x['trade_days'])
        ts = self.__rate_of_return['M']
        result = DataFrameExtended([], index=ts.index.rename('time'))
        for key, value in self._column_names['M'].items():
            result[value[0]] = pd.rolling_sum(ts, key).apply(calculator, axis=1)
        result.total = calculator(ts.sum())
        return result

    @property
    @cache_calculator
    def risk_free_rate(self):
        return self._roll_exp(self.__risk_free_rate['M'])

    @property
    @cache_calculator
    # @profile
    def volatility(self):
        # TODO pandas好像并不支持分组上的移动窗口函数
        return self._roll_std(self.__rate_of_return_percent['M'])

    @property
    @cache_calculator
    def sharpe_ratio(self):
        expected = self._roll_exp(self.__excess_return['M'])
        # XXX作为分母的列需要特殊判断为零的情况，同时要考虑由于浮点计算引起的误差
        std = _deal_float_error(self._roll_std(self.__excess_return['M']), fill=np.nan)
        result = expected / std
        result.total = expected.total / std.total
        return result

    def sortino_ratio(self):
        pass

    def information_ratio(self):
        pass

    @property
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
            result[value[0]] = -(rolling_apply_2d(ts, key, calculator)['max_drawdown'].apply(_get_percent_from_log))
        result.total = -_get_percent_from_log(calculator(ts.values)[2])
        return _deal_float_error(result)


class StrategyPerformanceManageOnline(PerformanceManager):
    pass


class AccountPerformance(Performance):
    pass


class AccountPerformanceManager(PerformanceManager):
    pass


if __name__ == '__main__':
    pass
