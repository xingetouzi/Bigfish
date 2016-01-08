# -*- coding: utf-8 -*-
from Bigfish.models.performance import StrategyPerformance, StrategyPerformanceManagerOffline
from functools import reduce


class LigerUITranslator:
    __display_dict = dict(
            reduce(lambda x, y: dict(x, **{t[0]: t[1] for t in y.values()}),
                   (lambda x: list(x.values()))(StrategyPerformanceManagerOffline._column_names),
                   dict()),
            time='起始时间',
            **StrategyPerformance._factor_keys)

    def __init__(self, options={}):
        self.__options = options
        self.__column_options = {}

    def _get_column_dict(self, name):
        return dict(display=self.__display_dict[name], name=name, **self.__column_options.get(name, {}))

    def set_options(self, options):
        self.__options = options

    def get_options(self):
        return self.__options.copy()

    def set_column(self, column, options):
        self.__column_options[column] = options

    def dumps(self, dataframe):
        columns = [self._get_column_dict(dataframe.index.name)] + list(
                map(lambda x: self._get_column_dict(x), dataframe.columns))
        data = {'Rows': dataframe.fillna('/').to_dict('records')}
        return dict(columns=columns, data=data, **self.__options)
