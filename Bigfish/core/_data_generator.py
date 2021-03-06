import threading
import time
from queue import Queue, Empty, Full
import traceback

import pymysql
from Bigfish.models.quote import Bar
from Bigfish.utils.common import check_time_frame, tf2s, get_datetime
from Bigfish.utils.log import LoggerInterface
from Bigfish.data.connection import MySql
from Bigfish.data.receiver import TickDataReceiver
from Bigfish.models.config import ConfigInterface


# 定义两个线程执行接口
def produce(generator):
    """
    生产者,不断的从后台数据库取数据
    :param generator:
    """
    while not generator.finished:
        generator.product()


def consume(generator):
    """
    消费者,不断的从数据队列中取数据,并通知监听函数
    :param generator: 数据生产器对象
    """
    # 只有对列为空,并且状态是已完成时才标志数据取完了
    while (not generator.empty()) or (not generator.finished):
        generator.consume()
    generator.finish()


class DataGenerator(LoggerInterface, ConfigInterface):
    """
    这个对象包括两个线程,一个生产者,一段一段的不断从数据库中查询记录,并存入缓存队列.
    另一个消费者,不断的从缓存队列中取数据,这样做的好处是避免一次回测的数据太多占用太多的内存
    基本使用:
    dg = DataGenerator(config, self.process, self.finished)  # 数据生成器
    dg.start()
    """

    def __init__(self, process, finish=None, maxsize=500, parent=None):
        """

        Parameters
        ----------
        process: 每个数据bar事件来时的回调方法
        finish: 数据结束的回调方法
        maxsize: 缓存大小,默认500
        """
        # assert isinstance(config, Config)
        LoggerInterface.__init__(self, parent=parent)
        ConfigInterface.__init__(self, parent=parent)
        self.__check_tf(self.config.time_frame)
        self.__maxsize = maxsize
        self.__dq = Queue(maxsize=maxsize * 2)  # 数据缓存器,避免数据在内存里过大,造成内存不足的错误
        self.__symbol = self.config.symbols[0]
        self.__start_time = int(get_datetime(self.config.start_time).timestamp())
        if self.config.end_time:
            self.__end_time = int(get_datetime(self.config.end_time).timestamp())
        else:  # 如果没有指定结束时间,默认查询到最近的数据
            self.__end_time = int(time.time())
        self.__handle = process  # 行情数据监听函数(可以想象成java的interface)
        self.__finish = finish  # 数据结束函数
        self._finished = False
        self.logger_name = "DataGenerator"

    @property
    def finished(self):
        return self._finished

    def empty(self):
        return self.__dq.empty()

    def consume(self):
        """
        从缓存队列中消费数据(生产行情信号)
        :return:
        """
        try:
            data = self.__dq.get(timeout=0.5)
            self.__handle(data)
        except Empty:
            pass
        except:
            self.logger.error("\n" + traceback.format_exc())
            self.stop()

    def start(self):
        self._finished = False
        self.logger.debug("数据生成器开始运行")
        # 启动生产者
        t1 = threading.Thread(target=produce, args=(self,))
        # t1.setDaemon(True)
        # 启动消费者
        t2 = threading.Thread(target=consume, args=(self,))
        # t2.setDaemon(True)
        t1.start()
        t2.start()

    def stop(self):
        if not self._finished:
            self._finished = True
            self.logger.debug("数据生成器停止运行")

    def finish(self):
        if self.__finish is not None:
            self.__finish()

    def product(self):
        """
        从数据库中取出数据
        """
        try:
            conn = MySql().get_connection()  # 得到连接
            # 构造查询条件
            query_params = " where ctime >= '%s'" % (self.__start_time,)
            query_params += " and ctime < '%s'" % (self.__end_time,)

            coll = "%s_%s" % (self.__symbol, self.config.time_frame)

            cur = conn.cursor(pymysql.cursors.DictCursor)

            cur.execute("select * from %s " % coll + query_params + " limit %d " % self.__maxsize)
            # print(cur.fetchall())
            for row in cur.fetchall():
                bar = Bar(self.__symbol)
                bar.close = row["close"]
                bar.timestamp = int(row["ctime"])
                bar.high = row["high"]
                bar.low = row["low"]
                bar.open = row["open"]
                bar.volume = row["volume"]
                # volume maybe None in mysql
                if bar.volume is None:
                    bar.volume = 0
                bar.time_frame = self.config.time_frame
                self.__dq.put(bar)
                self.__start_time = bar.timestamp + tf2s(self.config.time_frame)
            cur.close()
            # 如果开始时间距结束时间的距离不超过当前时间尺度,证明数据查询完成
            if (cur.rownumber == 0) or self.__end_time - self.__start_time <= tf2s(self.config.time_frame):
                self.stop()
        except:
            self.logger.error('\n' + traceback.format_exc())
            self.stop()

    @classmethod
    def __check_tf(cls, time_frame):
        check_time_frame(time_frame)


class TickDataGenerator(LoggerInterface, ConfigInterface):
    """
    这个对象包括两个线程,一个生产者,一段一段的不断从数据库中查询记录,并存入缓存队列.
    另一个消费者,不断的从缓存队列中取数据,这样做的好处是避免一次回测的数据太多占用太多的内存
    基本使用:
    dg = DataGenerator(config, self.process, self.finished)  # 数据生成器
    dg.start()
    """

    def __init__(self, process, finish=None, maxsize=500, parent=None):
        """

        Parameters
        ----------
        config: BfConfig对象
        process: 每个数据bar事件来时的回调方法
        finish: 数据结束的回调方法
        maxsize: 缓存大小,默认500
        """
        LoggerInterface.__init__(self, parent=parent)
        ConfigInterface.__init__(self, parent=parent)
        self.__check_tf(self.config.time_frame)
        self.__maxsize = maxsize
        self.__dq = Queue(maxsize=maxsize * 2)  # 数据缓存器,避免数据在内存里过大,造成内存不足的错误
        self.__receiver = TickDataReceiver(parent=self)
        self.__receiver.register_event(self.config.symbols[0], self.product)
        self.__symbol = self.config.symbols[0]
        self.__handle = process  # 行情数据监听函数(可以想象成java的interface)
        self.__finish = finish  # 数据结束函数
        self._finished = False
        self.logger_name = "TickDataGenerator"

    @property
    def finished(self):
        return self._finished

    def empty(self):
        return self.__dq.empty()

    def consume(self):
        """
        从缓存队列中消费数据(生产行情信号)
        :return:
        """
        try:
            data = self.__dq.get(timeout=0.5)
            self.__handle(data)
        except Empty:
            pass
        except:
            self.logger.error("\n" + traceback.format_exc())
            self.stop()

    def start(self):
        self._finished = False
        # 启动生产者
        t1 = threading.Thread(target=self.__receiver.start)
        # t1.setDaemon(True)
        # 启动消费者
        t2 = threading.Thread(target=consume, args=(self,))
        # t2.setDaemon(True)
        t1.start()
        t2.start()

    def stop(self):
        if not self._finished:
            self._finished = True
            self.__receiver.stop()

    def finish(self):
        if self.__finish is not None:
            self.__finish()

    def product(self, tick):
        if not self._finished:
            try:
                self.__dq.put(tick, timeout=0.5)
            except Full:
                pass
            except:
                self.logger.error("\n" + traceback.format_exc())
                self.stop()

    @classmethod
    def __check_tf(cls, time_frame):
        check_time_frame(time_frame)
