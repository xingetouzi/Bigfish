# -*- coding: utf-8 -*-
from functools import reduce
from numbers import Number

from Bigfish.models.performance import StrategyPerformance, StrategyPerformanceManagerOffline
import pandas as pd
import numpy as np


class LigerUITranslator:
    _display = {}

    def __init__(self, options={}):
        self._options = options
        self._column_options = {}
        self._units = {}

    def set_options(self, options):
        self._options = options

    def get_options(self):
        return self._options.copy()

    def set_column(self, column, options):
        self._column_options[column] = options

    def _get_column(self, name):
        display = (lambda x: x+self._units.get(x, ''))(self._display.get(name, name))
        return dict(display=display, name=name, minWidth=max(20 * len(display), 80),
                    **self._column_options.get(name, {}))

    def _get_content(self, data, *args, **kwargs):
        raise NotImplementedError

    def dumps(self, data, *args, **kwargs):
        columns, rows = self._get_content(data, *args, **kwargs)
        return dict(columns=columns, data=rows, **self._options)


class DataframeTranslator(LigerUITranslator):
    _display = dict(
            reduce(lambda x, y: dict(x, **{t[0]: t[1] for t in y.values()}),
                   (lambda x: list(x.values()))(StrategyPerformanceManagerOffline._column_names),
                   dict()),
            time='起始时间',
            **StrategyPerformance._dict)
    _display.update(
            {'index': '', 'total': '总体', 'long_position': '多仓', 'short_position': '空仓', 'total_trades': '总交易数',
             'winnings': '盈利交易数', 'losings': '亏损交易数', 'winning_percentage': '胜率',
             'average_profit': '平均净利', 'average_winning': '平均盈利', 'average_losing': '平均亏损',
             'average_winning_losing_ratio': '平均盈利/平均亏损', 'max_winning': '最大盈利',
             'max_losing': '最大亏损', '_': '', 'trade_number': '交易编号', 'deal_number': '成交编号', 'volume_d': '成交手数',
             'volume_p': '现有仓位', 'price': '成交价格', 'price_current': '持仓均价', 'entry': '成交方向',
             'trade_type': '持仓类型', 'symbol': '品种', 'trade_time': '成交时间', 'trade_profit': '平仓收益'})

    def __init__(self, options={}, currency='$'):
        super().__init__(options)
        self._precision = 6
        self._units = (lambda d: reduce(lambda x, y: dict(x, **dict.fromkeys(y[1], y[0])), d.items(), {}))(
                {'(%s)' % currency: ['平仓收益'],
                 '(手)': ['成交手数', '现有仓位', ]}
        )
        print(self._units)

    def set_precision(self, n):
        assert isinstance(n, int) and n >= 0
        self._precision = n

    def _get_column(self, series):
        name = series.name
        return dict(super()._get_column(name), type='float' if issubclass(series.dtype.type, np.number) else 'string')

    def _get_content(self, dataframe, display_index=True):
        temp = dataframe.fillna('/')
        columns = []
        if display_index:
            index = temp.index
            if isinstance(index, pd.MultiIndex):
                for name, label, level in zip(index.names, index.labels, index.levels):
                    # TODO 此处应有更优方法
                    temp[name] = list(map(lambda x: level[x], label))
                    columns.append(self._get_column(temp[name]))
            else:
                temp[temp.index.name] = temp.index.to_series().astype(str)
                columns.append(self._get_column(temp.index))
        columns += list(map(lambda x: self._get_column(temp[x]), dataframe.columns))

        def deal_with_float(dict_):
            for key, values in dict_.items():
                if isinstance(values, float):
                    if values.is_integer():
                        dict_[key] = int(values)
                    else:
                        dict_[key] = round(values, self._precision)
            return dict_

        rows = {'Rows': list(map(deal_with_float, temp.to_dict('records')))}
        return columns, rows


class ParametersParser(LigerUITranslator):
    _display = {'signal': '信号名', 'parameter': '参数名', 'default': '默认值', 'start': '起始值', 'end': '结束值',
                     'step': '步长'}
    _columns = ['signal', 'parameter', 'default', 'start', 'end', 'step']

    def __init__(self, option={}):
        super().__init__(dict(option, enabledEdit='true'))
        self.set_column('start', {'editor': {'type': 'int'}})
        self.set_column('end', {'editor': {'type': 'int'}})
        self.set_column('step', {'editor': {'type': 'int'}})

    def _get_content(self, data):
        columns = [self._get_column(key) for key in self._columns]
        rows = {'Rows': []}
        for signal, paras in data.items():
            for para, value in paras.items():
                rows['Rows'].append({'signal': signal, 'parameter': para, 'default': value['default'],
                                     'start': value['default'], 'end': value['default'], 'step': 1})
        return columns, rows

    @staticmethod
    def loads(data):
        result = {}
        for item in data:
            if item['signal'] not in result:
                result[item['signal']] = {}
            result[item['signal']][item['parameter']] = {'start': item['start'], 'end': item['end'],
                                                         'step': item['step']}
        return result


if __name__ == '__main__':
    index = pd.Series(np.arange(9, 2), name='index')
    a = pd.DataFrame(np.random.randn(4, 4), columns=['a', 'b', 'c', 'd'])
    translator = LigerUITranslator({'Height': 200})
    translator.set_precision(4)
    translator.set_column('a', {'Weight': 10})
    print(translator.dumps(a))
