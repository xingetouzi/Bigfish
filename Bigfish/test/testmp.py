import codecs
import operator
import time
import logging
import pandas as pd
from multiprocessing import Queue, Pool

from Bigfish.app.backtest import Backtesting


class g:
    def __init__(self, n):
        self.n = n

    def get_n(self, n):
        return self.n


def f(q):
    print(1)
    q.put(g(2))
    print(q.get())


def run_backest(**parameters):
    with codecs.open('../test/testcode9.py', 'r', 'utf-8') as f:
        code = f.read()
    user = '10032'
    backtest = Backtesting(user, 'test', code, ['EURUSD'], 'M30', '2015-01-02', '2015-03-01')
    backtest.start(paras=parameters)
    performance = backtest.get_performance()
    result = performance.optimize_info
    temp = pd.Series({signal + '.' + k: v for signal, paras in parameters.items() for k, v in paras.items()})
    result = pd.concat([temp, result])
    backtest.log(backtest.time("绩效计算完毕，耗时：{0}"), logging.INFO)
    return result


if __name__ == '__main__':
    q = Queue()
    n = 10
    m = 10
    T = 50
    S = 100
    process_num = 16
    print(run_backest(**{'handle': dict(TakeProfit=T, StopLoss=S)}))
    t1 = time.time()
    p = Pool(processes=process_num)
    result = []
    for i in range(n):
        for j in range(m):
            result.append(p.apply_async(func=run_backest,
                                        kwds={'handle': dict(TakeProfit=T - n // 2 + i, StopLoss=S - m // 2 + j)}))
    p.close()
    t2 = time.time()
    print('进程池创建完毕，大小:<%s>，总耗时：<%s> s' % (n * m, t2 - t1))
    # prints "[42, None, 'hello']"
    p.join()
    output = pd.DataFrame(list(map(operator.methodcaller('get'), result)))
    print(output.sort_values('净利($)', ascending=True).iloc[:50])
    t3 = time.time()
    print('运行完毕，总耗时：%s' % (t3 - t1))
