"""
数据连接类
"""
import pymysql
import traceback


def singleton(cls, *args, **kw):
    instances = {}

    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]

    return _singleton


@singleton
class MySql:
    """
    从mysql数据中获取数据的连接,可扩展实现更多功能
    可采用连接池,提高性能
    """

    def __init__(self):
        self.__host = "115.29.54.208"
        self.__user = "xinger"
        self.__passwd = "ShZh_forex_4"
        self.__db = "forex"
        self.__charset = "utf8"
        self.__conn = None

    def get_connection(self):
        # assert isinstance(self.__conn, pymysql.Connection)
        if not self.__conn:
            self.__conn = pymysql.connect(host=self.__host, user=self.__user, passwd=self.__passwd, db=self.__db,
                                          charset=self.__charset)
        self.__conn.ping(True)
        return self.__conn
