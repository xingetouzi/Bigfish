from weakref import proxy
from Bigfish.models.base import RunningMode, TradingMode


class BfConfig:
    """
    运行一个策略所需的配置类
    """
    def __init__(self, user='', name='', symbols=None, time_frame='', start_time=None, end_time=None,
                 capital_base=100000, commission=0, slippage=0, account=None, password=None,
                 allow_trading=True,
                 running_mode=RunningMode.backtest.value,
                 trading_mode=TradingMode.on_bar.value):
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
        self.allow_trading = allow_trading
        self.running_mode = RunningMode(running_mode)
        self.trading_mode = TradingMode(trading_mode)

    def __getitem__(self, item):
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError

    def to_dict(self):
        result = {}
        for field in ["user", "name", "capital_base", "time_frame", "symbols", "start_time", "end_time",
                      "commission", "slippage", "account", "password", "allow_trading"]:
            result[field] = getattr(self, field)
        result["running_mode"] = self.running_mode.value
        result["trading_mode"] = self.trading_mode.value
        return result


class ConfigInterface:
    def __init__(self, parent=None):
        if parent is not None:
            assert isinstance(parent, ConfigInterface)
        self._parent = proxy(parent) if parent is not None else None
        self._config = None

    @property
    def config(self) -> BfConfig:
        if self._config is None:
            if self._parent is None:
                return None
            else:
                return self._parent.config
        else:
            return self._config

    @config.setter
    def config(self, config):
        assert isinstance(config, BfConfig)
        self._config = config
