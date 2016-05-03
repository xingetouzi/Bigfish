from Bigfish.performance.performance import StrategyPerformanceManagerOnline
from Bigfish.models.trade import Position, Deal
from Bigfish.data.mongo_utils import MongoUser


class RuntimePerformance:
    def __init__(self, user):
        self._user = user
        self._mongo_user = MongoUser(user)
        self._performance = None
        self._performance_manager = None

    @property
    def positions(self):
        return {item.id: item for item in map(Position.from_dict, self._mongo_user.collection.positions.find())}

    @property
    def deals(self):
        return {item.id: item for item in map(Deal.from_dict, self._mongo_user.collection.deals.find())}

    @property
    def profit_records(self):
        return list(self._mongo_user.collection.PnLs.find())

    @property
    def performance(self):
        if self._performance is None:
            self._performance_manager = StrategyPerformanceManagerOnline(self.profit_records, self.deals,
                                                                         self.positions)
            self._performance = self._performance_manager.get_performance()
        return self._performance


if __name__ == '__main__':
    user = '10032'
    p = RuntimePerformance(user)
    print(p.performance.trade_details)
