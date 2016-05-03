"""
策略运行配置
"""


class BfConfig:
    """
    运行一个策略所需的配置类
    """

    def __init__(self, user='', name='', symbols=[], time_frame='', start_time=None, end_time=None, capital_base=100000,
                 commission=0, slippage=0, account=None, password=None):
        self.user = user
        self.name = name
        self.capital_base = capital_base
        self.time_frame = time_frame
        self.symbols = symbols
        self.start_time = start_time
        self.end_time = end_time
        self.commission = commission
        self.slippage = slippage
        self.account = account
        self.password = password

    def __getitem__(self, item):
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError


if __name__ == '__main__':
    c = BfConfig(['EURUSD'], 'M15', '2015-12-12', '2016-01-01')
    print(c['symbols'])
    print(c.symbols)
