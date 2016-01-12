# -*- coding: utf-8 -*-
from functools import reduce

from Bigfish.models.performance import StrategyPerformance, StrategyPerformanceManagerOffline
import pandas as pd


class LigerUITranslator:
    __display_dict = dict(
            reduce(lambda x, y: dict(x, **{t[0]: t[1] for t in y.values()}),
                   (lambda x: list(x.values()))(StrategyPerformanceManagerOffline._column_names),
                   dict()),
            time='起始时间',
            **StrategyPerformance._factor_keys)
    __display_dict.update({'total': '总体', 'long-position': '多仓', 'short-position': '空仓', 'total_trades': '总交易数',
                           'winnings': '盈利交易数', 'losings': '亏损交易数', 'winning_percentage': '胜率',
                           'average_profit': '平均净利', 'average_winning': '平均盈利', 'average_losing': '平均亏损',
                           'average_winning_losing_ratio': '平均盈利/平均亏损', 'max_winning': '最大盈利',
                           'max_losing': '最大亏损'})

    def __init__(self, options={}):
        self.__options = options
        self.__column_options = {}
        self.__precision = 6

    def _get_column_dict(self, name):
        return dict(display=self.__display_dict.get(name, name), name=name, **self.__column_options.get(name, {}))

    def set_options(self, options):
        self.__options = options

    def get_options(self):
        return self.__options.copy()

    def set_column(self, column, options):
        self.__column_options[column] = options

    def set_precision(self, n):
        assert (n, isinstance(n, int) and n >= 0)
        self.__precision = n

    def dumps(self, dataframe):
        columns = [self._get_column_dict(dataframe.index.name)] + list(
                map(lambda x: self._get_column_dict(x), dataframe.columns))
        temp = dataframe.applymap(lambda x: round(x, self.__precision)).fillna('/')

        def deal_with_float(dict_):
            for key in dict_.keys():
                if isinstance(dict_[key], float) and dict_[key].is_integer():
                    dict_[key] = int(dict_[key])
        temp[temp.index.name] = temp.index.to_series().astype(str)
        data = {'Rows': list(map(deal_with_float, temp.to_dict('records')))}
        return dict(columns=columns, data=data, **self.__options)

if __name__ == '__main__':
    import numpy as np

    index = pd.Series(np.arange(9, 2), name='index')
    a = pd.DataFrame(np.random.randn(4, 4), columns=['a', 'b', 'c', 'd'])
    translator = LigerUITranslator({'Height': 200})
    translator.set_precision(4)
    translator.set_column('a', {'Weight': 10})
    print(translator.dumps(a))
