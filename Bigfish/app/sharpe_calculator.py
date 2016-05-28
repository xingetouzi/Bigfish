import bisect
from dateutil.parser import parse
from Bigfish.performance.performance import StrategyPerformanceManagerOnline


class SharpeCalculator:
    def __init__(self, pnl: list):
        self.__pnl = pnl.copy()
        self.__pnl.sort(key=lambda x: x["x"])
        self.__pnl_index = list(map(lambda x: x["x"], self.__pnl))

    def get_sharpe(self, start_time, end_time):
        st = int(parse(start_time).timestamp())
        et = int(parse(end_time).timestamp())
        si = bisect.bisect_left(self.__pnl_index, st)
        ei = bisect.bisect_right(self.__pnl_index, et)
        base = self.__pnl[si]["y"]
        records = [{"x": item["x"], "y": item["y"] - base} for item in self.__pnl[si:ei]]
        manager = StrategyPerformanceManagerOnline(records, {}, {})
        performance = manager.get_performance()
        return performance.sharpe_ratio.total
