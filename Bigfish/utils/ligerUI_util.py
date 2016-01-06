# -*- coding: utf-8 -*-
from Bigfish.models.performance import StrategyPerformance, StrategyPerformanceManagerOffline
from functools import reduce


class LigerUITranslator:
    __display_dict = dict(
            reduce(StrategyPerformanceManagerOffline.column_names.values(), lambda x, y: dict(x, **y), initial={}),
            **StrategyPerformance.factor_keys)

    def __init__(self, options={}):
        self.__options = options

    def set_options(self, options):
        self.__options = options

    def set_columns(self, options, columns):
        self.__columns_options[columns] = options

    def dateframe_to_ligerUI(self, dataframe):
        columns = [{'display': '时间', 'name': 'time'}] + list(
                map(lambda x: {'display': self.__display_dict[x], 'name': x}, dataframe.index))

        data = {'Rows': dataframe.to_dict('records')}
        return dict(columns=columns, data=data, **self.__options)
