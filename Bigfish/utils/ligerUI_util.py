# -*- coding: utf-8 -*-
from functools import reduce
from numbers import Number

from Bigfish.models.performance import StrategyPerformance, StrategyPerformanceManagerOffline
import pandas as pd


class LigerUITranslator:
    _display_dict = dict(
            reduce(lambda x, y: dict(x, **{t[0]: t[1] for t in y.values()}),
                   (lambda x: list(x.values()))(StrategyPerformanceManagerOffline._column_names),
                   dict()),
            time='起始时间',
            **StrategyPerformance._dict)
    _display_dict.update(
            {'index': '', 'total': '总体', 'long_position': '多仓', 'short_position': '空仓', 'total_trades': '总交易数',
             'winnings': '盈利交易数', 'losings': '亏损交易数', 'winning_percentage': '胜率',
             'average_profit': '平均净利', 'average_winning': '平均盈利', 'average_losing': '平均亏损',
             'average_winning_losing_ratio': '平均盈利/平均亏损', 'max_winning': '最大盈利',
             'max_losing': '最大亏损', '_': '', 'trade_number': '交易编号', 'deal_number': '成交编号', 'volume_d': '成交手数',
             'volume_p': '现有仓位', 'price': '成交价格', 'price_current': '持仓均价', 'entry': '成交方向',
             'trade_type': '持仓类型', 'symbol': '品种', 'trade_time': '成交时间', 'trade_profit': '平仓收益'})

    def __init__(self, options={}):
        self._options = options
        self._column_options = {}
        self._precision = 6

    def _get_column_dict(self, name):
        display = self._display_dict.get(name, name)
        return dict(display=display, name=name, weight=max(12 * len(display), 120),
                    minWeight=120, **self._column_options.get(name, {}))

    def set_options(self, options):
        self._options = options

    def get_options(self):
        return self._options.copy()

    def set_column(self, column, options):
        self._column_options[column] = options

    def set_precision(self, n):
        assert isinstance(n, int) and n >= 0
        self._precision = n

    def dumps(self, dataframe, display_index=True):
        temp = dataframe.fillna('/')
        if display_index:
            index = temp.index
            if isinstance(index, pd.MultiIndex):
                columns = []
                for name, label, level in zip(index.names, index.labels, index.levels):
                    columns.append(self._get_column_dict(name))
                    # TODO 此处应有更优方法
                    temp[name] = list(map(lambda x: level[x], label))
            else:
                columns = [self._get_column_dict(temp.index.name)]
                temp[temp.index.name] = temp.index.to_series().astype(str)
        columns += list(map(lambda x: self._get_column_dict(x), dataframe.columns))

        def deal_with_float(dict_):
            for key, values in dict_.items():
                if isinstance(values, float):
                    if values.is_integer():
                        dict_[key] = int(values)
                    else:
                        dict_[key] = round(values, self._precision)
            return dict_

        data = {'Rows': list(map(deal_with_float, temp.to_dict('records')))}
        return dict(columns=columns, data=data, **self._options)


class ParametersParser(LigerUITranslator):
    _display_dict = {'signal': '信号名', 'parameter': '参数名', 'default': '默认值', 'start': '起始值', 'end': '结束值',
                     'step': '步长'}
    _columns = ['signal', 'parameter', 'default', 'start', 'end', 'step']

    def __init__(self, option={}):
        super(ParametersParser, self).__init__(dict(option, enabledEdit='true'))
        self.set_column('start', {'editor': {'type': 'int'}})
        self.set_column('end', {'editor': {'type': 'int'}})
        self.set_column('step', {'editor': {'type': 'int'}})

    def dumps(self, data):
        columns = [self._get_column_dict(key) for key in self._columns]
        rows = {'Rows': []}
        for signal, paras in data.items():
            for para, value in paras.items():
                rows['Rows'].append({'signal': signal, 'parameter': para, 'default': value['default'],
                                     'start': value['default'], 'end': value['default'], 'step': 1})
        return dict(columns=columns, data=rows, **self._options)

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
    import numpy as np

    index = pd.Series(np.arange(9, 2), name='index')
    a = pd.DataFrame(np.random.randn(4, 4), columns=['a', 'b', 'c', 'd'])
    translator = LigerUITranslator({'Height': 200})
    translator.set_precision(4)
    translator.set_column('a', {'Weight': 10})
    print(translator.dumps(a))
