# -*- coding:utf-8 -*-
import time
import codecs
import gc

from Bigfish.models.model import User
from Bigfish.store.directory import UserDirectory
from Bigfish.utils.ligerUI_util import DataframeTranslator
from Bigfish.app.backtest import Backtesting
from Bigfish.utils.memory_profiler import profile


@profile
def test(detail):
    def get_first_n_lines(string, n):
        lines = string.splitlines()
        n = min(n, len(lines))
        return '\n'.join(lines[:n])

    #gc.set_debug(gc.DEBUG_UNCOLLECTABLE | gc.DEBUG_SAVEALL)
    start_time = time.time()
    with codecs.open('../test/testcode6.py', 'r', 'utf-8') as f:
        code = f.read()
    user = User('10032')
    backtest = Backtesting(user, 'test', code, ['EURUSD'], 'M30', '2015-01-01', '2016-01-01')
    print(backtest.progress)
    for _ in range(6):
        backtest.start()
        print(backtest.get_performance().trade_summary)
    if detail:
        translator = DataframeTranslator()
        user_dir = UserDirectory(user)
        print(user_dir.get_sys_func_list())
        print(backtest.get_profit_records())  # 获取浮动收益曲线
        print(backtest.get_parameters())  # 获取策略中的参数（用于优化）
        performance = backtest.get_performance()  # 获取策略的各项指标
        print('trade_info:\n%s' % performance._manager.trade_info)
        print('trade_summary:\n%s' % performance.trade_summary)
        print('trade_details:\n%s' % performance.trade_details)
        print(translator.dumps(performance._manager.trade_info))
        print(translator.dumps(performance.trade_details))
        print('strategy_summary:\n%s' % performance.strategy_summary)
        print('optimize_info:\n%s' % performance.optimize_info)
        print('info_on_home_page\n%s' % performance.get_info_on_home_page())
        print(performance.get_factor_list())
        # print(performance.yield_curve)
        print('ar:\n%s' % performance.ar)  # 年化收益率
        print('risk_free_rate:\n%s' % performance._manager.risk_free_rate)  # 无风险收益率
        print('volatility:\n%s' % performance.volatility)  # 波动率
        print('sharpe_ratio:\n%s' % performance.sharpe_ratio)  # sharpe比率
        print('max_drawdown:\n%s' % performance.max_drawdown)  # 最大回测
        print('trade_position\n%s' % performance.trade_positions)  # 交易仓位
        print(time.time() - start_time)
        # print('output:\n%s' % get_first_n_lines(backtest.get_output(), 100))
        print(time.time() - start_time)
        print(backtest.progress)
    paras = {'handle': {'times': {'start': 7, 'end': 10, 'step': 1}}}
    optimize = backtest.optimize(paras, None, None)
    print('optimize\n%s' % optimize)
    print(time.time() - start_time)
    del backtest
    performance = None
    optimize = None
    # print('\n'.join(map(str, gc.garbage)).replace('\n', '\r\n'), file=codecs.open('garbage', "w", 'utf-8'), flush=True)
    # gc.collect()


if __name__ == '__main__':
    test(False)
