import pandas as pd
from Bigfish.performance.performance import StrategyPerformanceManagerOnline
from Bigfish.models.trade import Position, Deal
from Bigfish.data.mongo_utils import MongoUser
from Bigfish.utils.ligerUI_util import DataframeTranslator


class PerformanceAfterTranslate:
    def __init__(self, performance):
        self._performance = performance
        self._translator = DataframeTranslator(
            {'height': 'auto', 'width': '98%', 'pageSize': 20, 'where': 'f_getWhere()'})

    def __getattr__(self, item):
        result = getattr(self._performance, item)
        if isinstance(result, pd.DataFrame):
            return self._translator.dumps(result)
        elif isinstance(result, pd.Series):
            return self._translator.dumps(pd.DataFrame(result))
        else:
            return result


class RuntimePerformance:
    def __init__(self, user):
        self._user = user
        self._mongo_user = MongoUser(user)
        self._performance = None
        self._performance_manager = None
        self._positions = None
        self._deals = None
        self._profit_records = None

    @property
    def positions(self):
        if self._positions is None:
            self._positions = {item.id: item for item in
                               map(Position.from_dict, self._mongo_user.collection.positions.find())}
        return self._positions

    @property
    def deals(self):
        if self._deals is None:
            self._deals = {item.id: item for item in map(Deal.from_dict, self._mongo_user.collection.deals.find())}
        return self._deals

    @property
    def profit_records(self):
        if self._profit_records is None:
            self._profit_records = list(self._mongo_user.collection.PnLs.find())
        return self._profit_records

    @property
    def performance(self):
        if self._performance is None:
            self._performance_manager = StrategyPerformanceManagerOnline(self.profit_records, self.deals,
                                                                         self.positions)
            self._performance = self._performance_manager.get_performance()
        return self._performance

    @property
    def empty(self):
        return not (self.positions and self.deals and self.profit_records)


if __name__ == '__main__':
    user = '10032'
    p = RuntimePerformance(user)
    print(p.performance.trade_details)
