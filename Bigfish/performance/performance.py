# -*- coding: utf-8 -*-

import operator
import math
from collections import OrderedDict, deque
from functools import partial, wraps, reduce
from weakref import WeakKeyDictionary, proxy

import numpy as np
import pandas as pd
import pytz
# import tushare
from pandas.tseries.offsets import MonthBegin

from Bigfish.models.quote import Bar
from Bigfish.models.trade import *
from Bigfish.utils.memory_profiler import profile as m_profile
from Bigfish.utils.pandas_util import rolling_apply_2d

# ——————————————————————————————————————————————————————————————————————————————————————————————————————————————————————
pd.set_option('display.precision', 6)
pd.set_option('display.width', 200)
pd.set_option('display.max_columns', 30)
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
    _manager = None
    _dict_name = {}

    def __init__(self, manager=None):
        if manager:
            self._manager = proxy(manager)  # 避免循环引用
        self._dict = None

    def __getattr__(self, item):
        if item in self._dict_name:
            if self._manager is not None:
                return getattr(self._manager, item)
            else:
                return None
        else:
            return self.__getattribute__(item)

    @property
    def __dict__(self):
        if self._dict is None:
            self._dict = {field: getattr(self, field) for field in self._dict_name.keys()}
        return self._dict


class PerformanceManager:
    def __init__(self, cls):
        assert issubclass(cls, Performance)
        self.__cls = cls
        self.__performance = self.__cls(self)

    def get_performance(self):
        return self.__performance


class StrategyPerformance(Performance):
    """只需定义performance中应该有的属性"""

    _dict_name = {'yield_curve': '收益曲线', 'trade_positions': '交易仓位线', 'is_negative': '是否爆仓'}
    __factor_info = OrderedDict()
    for k, v in [('ar', '策略年化收益率(%)'), ('sharpe_ratio', '夏普比率'), ('volatility', '收益波动率'),
                 ('max_drawdown', '最大回撤(%)')]:
        __factor_info[k] = v
    __trade_info = {'trade_summary': '总体交易概要', 'trade_details': '分笔交易详情'}
    __strategy_info = {'strategy_summary': '策略绩效概要'}
    __optimize_info = {'optimize_info': '优化信息'}
    _dict_name.update(__factor_info)
    _dict_name.update(__trade_info)
    _dict_name.update(__strategy_info)
    _dict_name.update(__optimize_info)
    _dict_name.update({'info_on_home_page': '首页信息', "yield_rate": "收益率"})

    @classmethod
    def get_factor_list(cls):
        return cls.__factor_info

    @classmethod
    def get_trade_info_list(cls):
        return cls.__trade_info

    @classmethod
    def get_strategy_info_list(cls):
        return cls.__strategy_info

    def __init__(self, manager=None):
        super(StrategyPerformance, self).__init__(manager)


# -----------------------------------------------------------------------------------------------------------------------
def _get_percent_from_log(n, factor=1):
    return (math.exp(n * factor) - 1) * 100


def _deal_float_error(dataframe, fill=0):
    dataframe[abs(dataframe) <= FLOAT_ERR] = fill
    return dataframe


class StrategyPerformanceManager(PerformanceManager):
    _column_names = {}
    _column_names['M'] = (lambda x: OrderedDict(sorted(x.items(), key=lambda t: t[0])))(
        {1: ('month1', '1个月'), 3: ('month3', '3个月'), 6: ('month6', '6个月'), 12: ('month12', '1年')})

    def __init__(self, deals, positions, currency_symbol='$', capital_base=100000):
        super(StrategyPerformanceManager, self).__init__(StrategyPerformance)
        self._deals_raw = pd.DataFrame(list(map(lambda x: x.to_dict(), deals.values())), index=deals.keys(),
                                       columns=Deal.get_keys())  # deals in dataframe format
        self._positions_raw = pd.DataFrame(list(map(lambda x: x.to_dict(), positions.values())),
                                           index=positions.keys(),
                                           columns=Position.get_keys())  # positions in dataframe format
        self._deals_raw['number_id'] = self._deals_raw['id'].apply(lambda x: int(x.split('-')[-1]))
        self._deals_raw.sort_values(['time', 'number_id'], kind='mergesort', inplace=True)
        (lambda x: x.rename(pd.Series(range(1, x.shape[0] + 1), index=x.index).to_dict(), inplace=True))(
            self._deals_raw)  # 成交重新用数字编号
        self._positions_raw.sort_values('time_update', kind='mergesort', inplace=True)
        self._currency_symbol = currency_symbol  # 账户的结算货币类型
        self._annual_factor = 250  # 年化因子
        self._capital_base = capital_base
        self._precision = 4
        self._cache = {}  # 用于存放将要在函数中复用的变量
        self._units = {}  # 用于存储计算中需要用到的单位信息

    # @profile
    @property
    @cache_calculator
    def _rate_of_return_raw(self):
        raise NotImplementedError

    def with_units(self, x):
        return x + self._units[x]

    def _update_units(self, d):
        for key, value in d.items():
            self._units.update(dict.fromkeys(value, key))

    @property
    @cache_calculator
    def is_negative(self):
        return bool(self._rate_of_return['R'].min() <= 0)

    @property
    @cache_calculator
    def _rate_of_return(self):
        result = {}
        result['R'] = self._rate_of_return_raw  # 'R' means raw
        # TODO 对爆仓情况的考虑
        if result['R'].min() <= 0:
            result['D'], self.__index_daily = \
                (lambda x, y: (pd.DataFrame({x.name: x, 'trade_days': y}).dropna(), x.index))(
                    *(lambda x: (x - x.shift(1).fillna(method='ffill').fillna(0), x.notnull().astype('int')))(
                        result['R'].resample('D', how='last', label='left') * 0))

        else:
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
    def _rate_of_return_percent(self):
        result = {}
        result['D'] = \
            (lambda x: pd.DataFrame(
                {'rate': x['rate'].apply(partial(_get_percent_from_log)),
                 'trade_days': x['trade_days']}))(
                self._rate_of_return['D']
            )
        result['W'] = result['D'].resample('W-MON', how='sum').dropna()
        result['M'] = result['D'].resample('MS', how='sum').dropna()
        return result

    @property
    @cache_calculator
    def _risk_free_rate(self):
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
    def _excess_return(self):
        result = {}
        result['D'] = \
            (lambda x, y: pd.DataFrame(
                {'rate': x['rate'].apply(partial(_get_percent_from_log, factor=self._annual_factor)) - y[
                    'rate'].reindex(x.index),
                 'trade_days': x['trade_days']}))(
                self._rate_of_return['D'], self._risk_free_rate['D']
            )
        result['W'] = result['D'].resample('W-MON', how='sum')
        result['M'] = result['D'].resample('MS', how='sum')
        return result

    @property
    @cache_calculator
    def yield_curve(self):
        rate_of_return = ((self._rate_of_return['R'] - 1) * 100).apply(lambda x: round(x, self._precision))
        return [{'x': int(x.timestamp()), 'y': y} for x, y in zip(rate_of_return.index, rate_of_return.tolist())]

    @property
    @cache_calculator
    def optimize_info(self):
        temp = pd.Series()  # TODO 把这两项也加入策略的概要
        temp['夏普比率'] = self.sharpe_ratio.total
        temp['R平方'] = self.r_square.total
        result = pd.concat([temp, self.strategy_summary['_'], self.trade_summary['total']])
        result.name = '_'
        result.index.name = 'index'
        return result

    @property
    @cache_calculator
    def strategy_summary(self):
        def nan2num(num, default=0):
            """
            处理计算结果为nan的情况
            :param num: 计算结果
            :param default: 默认值
            :return: 如果为nan则返回默认值否则返回原值
            """
            return default if np.isnan(num) else num

        self._update_units(
            {'(%s)' % self._currency_symbol: ['净利', '盈利', '亏损', '平仓交易最大亏损', ],
             '(%)': ['账户资金收益率', '年化收益率', '最大回撤', '策略最大潜在亏损', ],
             '': ['最大潜在亏损收益比']}
        )
        names = ['净利', '盈利', '亏损', '账户资金收益率', '年化收益率', '最大回撤', '策略最大潜在亏损', '平仓交易最大亏损', '最大潜在亏损收益比']
        with_units = self.with_units
        trade_summary = self.trade_summary
        net_profit = trade_summary['total'][with_units('平均净利')] * trade_summary['total'][with_units('总交易数')]
        winning = trade_summary['total'][with_units('平均盈利')] * trade_summary['total'][with_units('盈利交易数')]
        losing = trade_summary['total'][with_units('平均亏损')] * trade_summary['total'][with_units('亏损交易数')]
        rate_of_return = (net_profit / self._capital_base) if self._capital_base else 0
        trade_days = self._rate_of_return['D']['trade_days'].sum()
        # TODO 交易日计算是否正确
        annual_rate_of_return = _get_percent_from_log(math.log(rate_of_return + 1),
                                                      self._annual_factor / trade_days) if trade_days else 0
        max_potential_losing = min(self._rate_of_return['R'].min() - 1, 0)
        max_losing = trade_summary['total'][with_units('最大亏损')]
        result = pd.DataFrame({
            '净利': nan2num(net_profit),
            '盈利': nan2num(winning),
            '亏损': nan2num(losing),
            '账户资金收益率': nan2num(rate_of_return * 100),
            '年化收益率': nan2num(annual_rate_of_return),
            '最大回撤': self.max_drawdown.total if not self.is_negative else 100,
            '策略最大潜在亏损': max_potential_losing * 100,
            '平仓交易最大亏损': nan2num(max_losing),
            '最大潜在亏损收益比': nan2num(rate_of_return) / -max_potential_losing if abs(
                max_potential_losing) > FLOAT_ERR else np.nan
        }, index=['_']).T.reindex(names).rename(lambda x: self.with_units(x))
        result.index.name = 'index'
        return result

    @property
    @cache_calculator
    @m_profile
    def trade_info(self):
        positions = self._positions_raw[['symbol', 'type', 'price_current', 'volume']]
        deals = self._deals_raw[
            ['position', 'time', 'type', 'price', 'volume', 'profit', 'entry', 'strategy', 'signal', 'id']]
        trade = pd.merge(deals, positions, how='left', left_on='position', right_index=True, suffixes=('_d', '_p'))
        # XXX dataframe的groupby方法计算结果是dataframe的视图，所以当dataframe的结构没有变化，groupby的结果依然可用
        if trade.empty:  # 依旧丑陋的补丁
            trade = pd.DataFrame(columns=['symbol', 'type_d', 'price_current', 'volume_d', 'position', 'time',
                                          'type_p', 'price', 'volume_p', 'profit', 'entry', 'strategy', 'signal',
                                          'trade_number', 'trade_type'])
            trade.index.name = 'deal_number'
            return trade
        trade_grouped = trade.groupby('symbol')
        self._cache['trade_grouped_by_symbol'] = trade_grouped
        # XXX 此操作在trade为空时会报错
        trade['trade_number'] = trade_grouped.apply(
            lambda x: pd.DataFrame((x['volume_p'] == 0).astype(int).cumsum().shift(1).fillna(0) + 1, x.index))
        # TODO 在多品种交易下进行测试
        temp = trade_grouped['trade_number'].last().cumsum().shift(1).fillna(0)
        trade['trade_number'] = trade['trade_number'] + trade['symbol'].apply(lambda x: temp[x])
        temp = trade.groupby('trade_number')['type_p'].first()
        trade['trade_type'] = trade['trade_number'].apply(lambda x: temp[x])
        trade['profit'] = trade['profit'].fillna(0)
        trade.index.name = 'deal_number'
        del positions
        del deals
        del temp
        return trade

    @property
    @cache_calculator
    @m_profile
    def trade_summary(self):
        self._update_units(
            {'(%s)' % self._currency_symbol: ['平均净利', '平均盈利', '平均亏损', '平均盈利/平均亏损', '最大盈利', '最大亏损'],
             '(%)': ['胜率'],
             '': ['总交易数', '未平仓交易数', '盈利交易数', '亏损交易数']})
        columns = ['total', 'long_position', 'short_position']
        result = pd.DataFrame(index=columns)
        trade = {}
        trade_grouped = {}
        trade['total'] = self.trade_info
        trade['long_position'] = trade['total'].query('trade_type>0')
        trade['short_position'] = trade['total'].query('trade_type<0')
        for key in columns:
            trade_grouped[key] = trade[key].groupby(['symbol', 'trade_number'])
        result['总交易数'] = [trade_grouped[key].ngroups for key in columns]
        last_trade = trade['total'].tail(1)
        if not last_trade.empty and (last_trade.volume_p != 0).bool():  # XXX last_trade为空的情况
            result['总交易数']['total'] -= 1
            if (last_trade.type_p > 0).bool():
                result['未平仓交易数'] = [1, 1, 0]
                result['总交易数']['long_position'] -= 1
            else:
                result['未平仓交易数'] = [1, 0, 1]
                result['总交易数']['short_position'] -= 1
        else:
            result['未平仓交易数'] = [0, 0, 0]
        profits = [(lambda x: x[:-1] if result['未平仓交易数'][key] else x)(trade_grouped[key]['profit'].sum())
                   for key in columns]
        winnings = list(map(lambda x: x[x > 0], profits))
        losings = list(map(lambda x: x[x < 0], profits))
        result['盈利交易数'] = list(map(len, winnings))
        result['亏损交易数'] = list(map(len, losings))
        result['胜率'] = result['盈利交易数'] / result['总交易数'] * 100
        result['平均净利'] = list(map(lambda x: x.mean(), profits))
        result['平均盈利'] = list(map(lambda x: x.mean(), winnings))
        result['平均亏损'] = list(map(lambda x: x.mean(), losings))
        result['平均盈利/平均亏损'] = result['平均盈利'] / -result['平均亏损']
        result['最大盈利'] = list(map(lambda x: x.max(), profits))
        result['最大亏损'] = list(map(lambda x: x.min(), profits))
        result = result.T.rename(lambda x: self.with_units(x))
        result.index.name = 'index'
        trade.clear()
        trade_grouped.clear()
        return result

    @property
    @cache_calculator
    def trade_details(self):
        columns = ['trade_type', 'entry', 'time', 'volume_d', 'price', 'volume_p', 'price_current', 'profit', 'id']

        if not self.trade_info.empty:
            trade = self.trade_info.groupby(['symbol', 'trade_number', self.trade_info.index])[columns].last()
        else:  # 丑陋补丁X3
            trade = pd.DataFrame(columns=columns)
            trade.index.name = '_'
        trade['entry'] = trade['entry'].map(lambda x: '入场(加仓)' if x == 1 else '出场(减仓)')
        trade['trade_type'] = trade['trade_type'].map(lambda x: '空头' if x < 0 else '多头' if x > 0 else '无持仓')
        trade['trade_time'] = trade['time'].map(
            partial(pd.datetime.fromtimestamp, tz=pytz.timezone('Asia/Shanghai'))).astype(str) \
            .map(lambda x: x.split('+')[0])
        trade['trade_profit'] = trade['profit']
        trade['deal_id'] = trade['id']
        del trade['time'], trade['profit'], trade['id']
        return trade

    @property
    @cache_calculator
    def trade_positions(self):
        trade = self.trade_details
        result = {}

        def condition2num(bool_):
            return (bool_ << 1) - 1

        def is_win(price1, price2, trade_type):
            return condition2num(price2 >= price1) * condition2num(trade_type == '多头')

        def get_position_lines(out, queue, row):
            if row['entry'] == '入场(加仓)':
                queue.append([row['volume_d'], row['price'], row['trade_time']])
            else:
                volume = row['volume_d']
                while volume > 0:
                    try:
                        entry = queue.popleft()
                    except IndexError:
                        break
                    out.append({'x1': entry[2], 'y1': entry[1],
                                'x2': row['trade_time'], 'y2': row['price'],
                                'type': is_win(entry[1], row['price'], row['trade_type'])})
                    volume -= entry[0]
                if volume < 0:
                    queue.appendleft([-volume, entry[1], entry[2]])

        def get_position_lines_raw(out, queue, row):
            if row[3] == '入场(加仓)':
                queue.append(row[0:2])
            else:
                volume = row[0]
                while volume > 0:
                    entry = queue.popleft()
                    out.append({'x1': entry[2], 'y1': entry[1],
                                'x2': row[2], 'y2': row[1],
                                'type': is_win(entry[1], row[1], row[4])})
                    volume -= entry[0]
                if volume < 0:
                    queue.appendleft([-volume, entry[1], entry[2]])

        for name, data in trade[['volume_d', 'price', 'trade_time', 'entry', 'trade_type']].groupby(level=0):
            result[name] = {}
            result[name]['lines'] = []
            deal_queue = deque([])
            data.apply(partial(get_position_lines, result[name]['lines'], deal_queue), axis=1)
            # TODO 比较两者的速度差距，看看是否有必要把所有的apply都加上RAW=TRUE
            # data.apply(partial(get_position_lines_raw, result[name]['lines'], deal_queue), axis=1， raw=True)
            result[name]['points'] = list(map(lambda x: {'x': x[2], 'y': x[1]}, deal_queue))
        return result

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
        # TODO numpy.sqrt np自带有开根号运算
        for key, value in self._column_names['M'].items():
            # XXX 开根号运算会将精度缩小一半，必须在此之前就处理先前浮点运算带来的浮点误差
            result[value[0]] = _deal_float_error(pd.rolling_sum(ts, key).apply(calculator, axis=1)) ** 0.5 * (
                self._annual_factor ** 0.5)
        result.total = (lambda x: int(abs(x) > FLOAT_ERR) * x)(calculator(ts.sum())) ** 0.5 * (
            self._annual_factor ** 0.5)
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
        calculator = lambda x: _get_percent_from_log(x['rate'], factor=self._annual_factor / x['trade_days'])
        ts = self._rate_of_return['M']
        result = DataFrameExtended([], index=ts.index.rename('time'))
        for key, value in self._column_names['M'].items():
            result[value[0]] = pd.rolling_sum(ts, key).apply(calculator, axis=1)
        result.total = calculator(ts.sum())
        return result

    @property
    @cache_calculator
    def yield_rate(self):
        calculator = lambda x: (x['rate'] / x['trade_days']) * self._annual_factor
        ts = self._rate_of_return_percent['M']
        result = DataFrameExtended([], index=ts.index.rename('time'))
        for key, value in self._column_names['M'].items():
            result[value[0]] = pd.rolling_sum(ts, key).apply(calculator, axis=1)
        result.total = calculator(ts.sum())
        return result

    @property
    @cache_calculator
    def risk_free_rate(self):
        return self._roll_exp(self._risk_free_rate['M'])

    @property
    @cache_calculator
    # @profile
    def volatility(self):
        # TODO pandas好像并不支持分组上的移动窗口函数
        return self._roll_std(self._rate_of_return_percent['D'])

    @property
    @cache_calculator
    def sharpe_ratio(self):
        expected = self.yield_rate
        # expected = self.ar
        # XXX作为分母的列需要特殊判断为零的情况，同时要考虑由于浮点计算引起的误差
        std = _deal_float_error(self.volatility, fill=np.nan) * (self._annual_factor ** 0.5)  # 年化标准差
        std.total = self.volatility.total * (self._annual_factor ** 0.5)
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
                        self._rate_of_return['D']))))
        result = DataFrameExtended([], index=ts.index.rename('time'))
        for key, value in self._column_names['M'].items():
            result[value[0]] = -(rolling_apply_2d(ts, key, calculator)['max_drawdown'].apply(_get_percent_from_log))
        result.total = -_get_percent_from_log(calculator(ts.values)[2])
        return _deal_float_error(result)

    @property
    @cache_calculator
    def r_square(self):
        result = DataFrameExtended()
        matrix = (lambda x, y: np.cov(x, y))(
            *(lambda x: (np.array(range(len(x))), x))(
                self._rate_of_return_raw.resample('D', how='last').fillna(method='ffill')
            )
        )
        result.total = matrix[0][1] * matrix[1][0] / (matrix[0][0] * matrix[1][1])
        return result

    @property
    @cache_calculator
    def info_on_home_page(self):
        fields = ["净利", "策略最大潜在亏损", "账户资金收益率", "平仓交易最大亏损", "年化收益率", "最大潜在亏损收益比"]
        self.strategy_summary  # 先进行计算把单位更新了
        return [(self.with_units(field),
                 self.strategy_summary['_'].fillna(0).to_dict()[self.with_units(field)])
                for field in fields]


class StrategyPerformanceManagerOffline(StrategyPerformanceManager):
    """只需要写根据输入计算输出的逻辑"""

    def __init__(self, quotes, deals, positions, symbols_pool, currency_symbol='$', capital_base=100000, period=86400,
                 num=20, **config):  # 1day = 86400seconds
        super(StrategyPerformanceManagerOffline, self).__init__(deals, positions,
                                                                currency_symbol=currency_symbol,
                                                                capital_base=capital_base)
        self._symbols_pool = symbols_pool
        self._config = config
        if quotes is not None:
            self._quotes_raw = quotes
        else:
            self._quotes_raw = pd.DataFrame(columns=Bar.get_keys())
        self._num = num
        self._period = period
        self._rate_of_return_raw
        self._quotes_raw = None  # 计算完毕折后就可以释放资源了

    # @profile
    @property
    @cache_calculator
    def _rate_of_return_raw(self):
        interval = self._period // self._num
        time_index_calculator = lambda x: ((x - 1) // interval + 1) * interval
        self._quotes_raw['time_index'] = self._quotes_raw['close_time'].map(time_index_calculator)
        self._deals_raw['time_index'] = self._deals_raw['time'].map(time_index_calculator)
        self._positions_raw = self._positions_raw[self._positions_raw['time_update'].notnull()]
        # XXX 去掉初始时的零仓位,因为仓位信息中其他的一些None值也算na所以不能直接用dropna
        self._positions_raw['time_index'] = self._positions_raw['time_update'].map(time_index_calculator)
        quotes = {k: v.groupby(['time_index'])[['close', 'symbol', 'base_price']].last() for k, v in
                  self._quotes_raw.groupby('symbol')}
        # TODO 计算交叉盘报价货币的汇率
        deals_profit = self._deals_raw['profit'].fillna(0).groupby(
            self._deals_raw['time_index']).sum().cumsum()
        # XXX deals_profit为空，即没有下单的情况，非常丑陋的补丁 @ ^ @
        if deals_profit.empty:
            deals_profit = pd.DataFrame(columns=['profit'])
            deals_profit.index.name = 'time_index'
        # XXX 注意初始时加入的未指明交易时间的”零“仓位的特殊处理,这里groupby中把time_index为NaN的行自动去除了
        positions = {k: v.groupby('time_index')['type', 'price_current', 'volume'].last() for k, v in
                     self._positions_raw.groupby("symbol")}
        # TODO 检查outer连接是否会影响交易日的计算
        calculator = lambda x: self._symbols_pool[x.symbol].lot_value((x.close - x.price_current) * x.type, x.volume,
                                                                      commission=self._config['commission'],
                                                                      slippage=self._config['slippage'],
                                                                      base_price=x.base_price)
        float_profits = {}
        for symbol in self._symbols_pool.keys():
            if symbol in quotes:
                if symbol in positions:
                    float_profits[symbol] = quotes[symbol].join(positions[symbol], how='outer').fillna(
                        method='ffill').fillna(0).apply(calculator, axis=1).fillna(0)
                else:
                    float_profits[symbol] = pd.Series(0, index=quotes[symbol].index)
        float_profit = reduce(lambda x, y: operator.add(*map(lambda t: t.fillna(0), x.align(y))),
                              float_profits.values(), pd.Series())
        # XXX 多品种情况这里还要测试一下正确性
        rate_of_return = pd.DataFrame(float_profit).join(deals_profit, how='outer').fillna(method='ffill').fillna(
            0).sum(axis=1).apply(
            lambda x: x / self._capital_base + 1)  # rate_of_return represent net yield now / capital base
        rate_of_return.index = rate_of_return.index.map(pd.datetime.fromtimestamp)
        rate_of_return.name = 'rate'
        return rate_of_return


class StrategyPerformanceManagerOnline(StrategyPerformanceManager):
    def __init__(self, yield_raw, deals, positions, currency_symbol='$', capital_base=100000):
        super(StrategyPerformanceManagerOnline, self).__init__(deals, positions,
                                                               currency_symbol=currency_symbol,
                                                               capital_base=capital_base)
        self._precision = 4
        self._yield_raw = yield_raw

    # @profile
    @property
    @cache_calculator
    def _rate_of_return_raw(self):
        if not self._yield_raw:
            return pd.Series(name='rate')
        temp = pd.DataFrame(self._yield_raw)
        rate_of_return = pd.Series(temp['y'].values, name='rate',
                                   index=temp['x'].map(pd.datetime.fromtimestamp)) / 100 + 1
        rate_of_return.index.name = 'time_index'
        return rate_of_return

    @property
    @cache_calculator
    def yield_curve(self):
        return self._yield_raw


class AccountPerformance(Performance):
    pass


class AccountPerformanceManager(PerformanceManager):
    pass


if __name__ == '__main__':
    pass
