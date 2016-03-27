import threading
import queue
import codecs
import time

from Bigfish.app.backtest import Backtesting
from Bigfish.models.model import User


class ThreadPoolManager:
    def __init__(self, threads=20):
        self.work_queue = queue.Queue()
        self.thread_pool = []
        self.__init_thread_pool(threads)

    def __init_thread_pool(self, thread_num):
        for i in range(thread_num):
            self.thread_pool.append(ThreadPoolThread(work_queue=self.work_queue))

    def add_work(self, func=None, args=(), kwargs={}):
        self.work_queue.put((func, args, kwargs))

    def join_all(self):
        for i in self.thread_pool:
            if i.isAlive():
                i.join()


class ThreadPoolThread(threading.Thread):
    threadSleepTime = 0.01

    def __init__(self, work_queue=None, **kwargs):
        threading.Thread.__init__(self, **kwargs)
        self.work_queue = work_queue
        self.start()

    def run(self):
        while True:
            if self.work_queue.qsize():
                do, args, kwargs = self.work_queue.get(block=False)
                do(*args, **kwargs)
                self.work_queue.task_done()
            else:
                time.sleep(ThreadPoolThread.threadSleepTime)


def run_backest(**parameters):
    with codecs.open('../test/testcode9.py', 'r', 'utf-8') as f:
        code = f.read()
    user = User('10032')
    backtest = Backtesting(user, 'test', code, ['EURUSD'], 'M30', '2015-01-02', '2015-03-01')
    backtest.start(paras=parameters)
    performance = backtest.get_performance()
    print(performance.trade_summary)


if __name__ == '__main__':
    n = 10
    m = 10
    T = 50
    S = 100
    thread_num = 16
    # run_backest(**{'handle': dict(TakeProfit=T, StopLoss=S)})
    t1 = time.time()
    p = ThreadPoolManager(threads=thread_num)
    for i in range(n):
        for j in range(m):
            p.add_work(func=run_backest, kwargs={'handle': dict(TakeProfit=T - n // 2 + i, StopLoss=S - m // 2 + j)})
    t2 = time.time()
    print('线程池创建完毕，大小:<%s>，总耗时：<%s> s' % (n * m, t2 - t1))
    # prints "[42, None, 'hello']"
    p.join_all()
    t3 = time.time()
    print('运行完毕，总耗时：%s' % (t3 - t1))
