import threading
import time
from queue import Queue

import pymysql
from Bigfish.core.models import Bar
from Bigfish.setting import TF_PERIODS

from Bigfish.data.connection import MySql


# 定义两个线程执行接口
def produce(generator):
    """
    生产者,不断的从后台数据库取数据
    :param generator:
    """
    while not generator.finished:
        generator.get_bars()


def consume(generator):
    """
    消费者,不断的从数据队列中取数据,并通知监听函数
    :param generator: 数据生产器对象
    """
    # 只有对列为空,并且状态是已完成时才标志数据取完了
    while (not generator.empty()) or (not generator.finished):
        generator.consume()
    generator.finish()


class DataGenerator:
    """
    这个对象包括两个线程,一个生产者,一段一段的不断从数据库中查询记录,并存入缓存队列.
    另一个消费者,不断的从缓存队列中取数据,这样做的好处是避免一次回测的数据太多占用太多的内存
    基本使用:
    dg = DataGenerator(config, self.process, self.finished)  # 数据生成器
    dg.start()
    """
    def __init__(self, config, process, finish, maxsize=500):
        """

        Parameters
        ----------
        config: BfConfig对象
        process: 每个数据bar事件来时的回调方法
        finish: 数据结束的回调方法
        maxsize: 缓存大小,默认500
        """
        # assert isinstance(config, Config)
        self.__check_tf(config.time_frame)
        self.__maxsize = maxsize
        self.__dq = Queue(maxsize=maxsize * 2)  # 数据缓存器,避免数据在内存里过大,造成内存不足的错误
        self.__config = config
        self.__start_time = config.start_time
        if config.end_time:
            self.__end_time = config.end_time
        else:  # 如果没有指定结束时间,默认查询到最近的数据
            self.__end_time = int(time.time())
        self.__handle = process  # 行情数据监听函数(可以想象成java的interface)
        self.__finish = finish  # 数据结束函数

        self.finished = False

    def empty(self):
        return self.__dq.empty()

    def consume(self):
        """
        从缓存队列中消费数据(生产行情信号)
        :return:
        """
        self.__handle(self.__dq.get())

    def start(self):
        # 启动生产者
        t1 = threading.Thread(target=produce, args=(self, ))
        # t1.setDaemon(True)
        # 启动消费者
        t2 = threading.Thread(target=consume, args=(self, ))
        # t2.setDaemon(True)
        t1.start()
        t2.start()

    def finish(self):
        self.__finish()

    def get_bars(self):
        """
        从数据库中取出数据
        """
        conn = MySql().get_connection()  # 得到连接

        # 构造查询条件
        query_params = " where ctime >= '%s'" % (self.__start_time,)
        query_params += " and ctime < '%s'" % (self.__end_time,)

        coll = "%s_%s" % (self.__config.symbol, self.__config.time_frame)

        cur = conn.cursor(pymysql.cursors.DictCursor)

        cur.execute("select * from %s " % coll + query_params + " limit %d " % self.__maxsize)

        for row in cur.fetchall():
            bar = Bar()
            bar.close = row["close"]
            bar.ctime = row["ctime"]
            bar.high = row["high"]
            bar.low = row["low"]
            bar.open = row["open"]
            bar.volume = row["volume"]
            self.__dq.put(bar)
            self.__start_time = bar.ctime

        cur.close()
        # 如果开始时间距结束时间的距离不超过当前时间尺度,证明数据查询完成
        if self.__end_time - self.__start_time <= TF_PERIODS[self.__config.time_frame]:
            self.finished = True

    @classmethod
    def __check_tf(cls, time_frame):
        if not (time_frame in TF_PERIODS.keys()):
            raise ValueError("Not supported time_frame: %s" % time_frame)
