# -*- coding: utf-8 -*-
from Bigfish.models.performance import StrategyPerformance, StrategyPerformanceManagerOffline
from functools import reduce


class LigerUITranslator:
    __display_dict = dict(
            reduce(StrategyPerformanceManagerOffline.column_names.values(), lambda x, y: dict(x, **y), initial={}),
            **StrategyPerformance.factor_keys)

    def __init__(self, options={}):
        self.__options = options

    def get_column_dict(self, display, name):
        return dict(display=display, name=name, **self.__column_options.get(name, {}))

    def set_options(self, options):
        self.__options = options

    def set_column(self, column, options):
        self.__column_options[column] = options

    def dateframe_to_ligerUI(self, dataframe):
        columns = [self.get_column_dict('时间', 'time')] + list(
                map(lambda x: self.get_column_dict(self.__display_dict[x], x), dataframe.index))
        data = {'Rows': dataframe.to_dict('records')}
        return dict(columns=columns, data=data, **self.__options)
