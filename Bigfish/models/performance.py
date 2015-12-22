# -*- coding: utf-8 -*-

class Performance():

    def __init__(self, curves={}, factors={}, manager=None):
        self.curves = curves
        self.factors = factors
        self.__manager = manager
        self.__set_attrs()

    @staticmethod
    def __get_attr_fget(field, type_):
        def wrapper(self):
            dict_ = getattr(self, type_)
            if field not in dict_:
                dict_[field] = getattr(self.__manager, 'cal_' + field)()
            return dict_[field]

        return wrapper
    def __setattr__(self, name, value):
        if super().__setattr__()
    def __getattr__(self,):


class PerformanceManager():
    def __init__(self, cls):
        assert issubclass(cls, Performance)
        self.__cls = cls
        self.__performance = None

    def get_perfomance(self):
        if self.__performance is None:
            self.__performance = self.__cls(self)
        return self.__performance


class StrategyPerformance(Performance):
    """只需定义performance中应该有的属性"""
    __curve_keys = {'yield_curve': '收益曲线'}
    __factor_keys = {'ar': '年化收益率'}

    def __init__(self, manager):
        super(StrategyPerformance, self).__init__(self.__curve_keys, self.__factor_keys, manager)


class StrategyPerformanceManager(PerformanceManager):
    """只需要写根据输入计算输出的逻辑"""
    def __init__(self, deals, positions):
        super(StrategyPerformanceManager, self).__init__(StrategyPerformance)
        self.__deals = deals
        self.__positions = positions

    def cal_yield_curve(self):
        return('cal yield_curve')

    def cal_ar(self):
        return('cal ar')