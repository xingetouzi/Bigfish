from multiprocessing import Queue, Pool
from Bigfish.app.backtest import Backtesting
from Bigfish.models.model import User
import codecs
import time


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
    user = User('10032')
    backtest = Backtesting(user, 'test', code, ['EURUSD'], 'M30', '2015-01-02', '2015-03-01')
    backtest.start(paras=parameters)
    performance = backtest.get_performance()
    print(performance.trade_summary)


if __name__ == '__main__':
    q = Queue()
    n = 10
    m = 10
    T = 50
    S = 100
    process_num = 16
    # run_backest(**{'handle': dict(TakeProfit=T, StopLoss=S)})
    t1 = time.time()
    p = Pool(processes=process_num)
    for i in range(n):
        for j in range(m):
            p.apply_async(func=run_backest, kwds={'handle': dict(TakeProfit=T - n // 2 + i, StopLoss=S - m // 2 + j)})
    p.close()
    t2 = time.time()
    print('进程池创建完毕，大小:<%s>，总耗时：<%s> s' % (n * m, t2 - t1))
    # prints "[42, None, 'hello']"
    p.join()
    t3 = time.time()
    print('运行完毕，总耗时：%s' % (t3 - t1))
