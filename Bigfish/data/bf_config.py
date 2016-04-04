"""
策略运行配置
"""
from Bigfish.setting import PRICE_PER_LOTS


class BfConfig:
    """
    运行一个策略所需的配置类
    """
    def __init__(self, symbol, time_frame, start_time, end_time=0, capital_base=100000):
        self.capital_base = capital_base
        self.time_frame = time_frame
        self.symbol = symbol
        self.start_time = start_time
        self.end_time = end_time
