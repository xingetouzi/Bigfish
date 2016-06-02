import bisect
from dateutil.parser import parse
from Bigfish.performance.performance import StrategyPerformanceManagerOnline


class SharpeCalculator:
    def __init__(self, pnl: list):
        self.__pnl = pnl.copy()
        self.__pnl.sort(key=lambda x: x["x"])
        self.__pnl_index = list(map(lambda x: x["x"], self.__pnl))

    def get_sharpe(self, start_time, end_time, simple=True):
        si, ei = self.get_index(start_time, end_time)
        if si >= len(self.__pnl):
            return 0
        records = self.__pnl[si:ei]
        manager = StrategyPerformanceManagerOnline(records, {}, {})
        performance = manager.get_performance()
        if simple:
            return performance.sharpe_ratio.total
        else:
            return performance.sharpe_ratio_compound.total

    def get_performance(self, start_time, end_time):
        si, ei = self.get_index(start_time, end_time)
        if si >= len(self.__pnl):
            return None
        records = self.__pnl[si:ei]
        return StrategyPerformanceManagerOnline(records, {}, {})

    def get_index(self, start_time, end_time):
        st = int(parse(start_time).timestamp())
        et = int(parse(end_time).timestamp())
        si = bisect.bisect_left(self.__pnl_index, st)
        ei = bisect.bisect_right(self.__pnl_index, et)
        return si, ei
