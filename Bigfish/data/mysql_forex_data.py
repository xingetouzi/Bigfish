# -*- coding: utf-8 -*-
import time

import pymysql

tf_peroids = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400, "W1": 604800}

conn=pymysql.connect(host='115.29.54.208', user='xinger', passwd='ShZh_forex_4', db='forex', charset='utf8')

def get_period_bars(symbol, time_frame, start_time, end_time=None, pattern=None):
    """
    获取从start_time至end_time这段时间内的所有 Bar
    :param symbol: 品种名称
    :param time_frame: 时间尺度
    :param start_time: 开始时间
    :param end_time: 结束时间
    :param pattern: 时间日期格式(%Y-%m-%d %H:%M:%S ...)
    :return 包含所有 Bar 的列表
    """
    __check_tf__(time_frame)
    if pattern:
        start_time = time.mktime(time.strptime(start_time, pattern))
        end_time = time.mktime(time.strptime(end_time, pattern))

    cur = conn.cursor(pymysql.cursors.DictCursor)
    query_params = " where ctime > '%s'" % (start_time, )
    if end_time:
        query_params += " and ctime < '%s'" % (end_time,)
    coll = "%s_%s" % (symbol, time_frame)
    cur.execute("select * from %s" % coll + query_params)
    bar_list = []
    for row in cur.fetchall():
        # bar_list.append(row)
        bar_list.append({"open": row["open"], "close": row["close"], "low": row["low"], "high": row["high"],
                         "ctime": row["ctime"], "volume": row["volume"]})
    return bar_list


def __check_tf__(time_frame):
    if not (time_frame in tf_peroids.keys()):
        raise ValueError("Not supported time_frame: %s" % time_frame)


if __name__ == '__main__':
    bar_array = get_period_bars("EURUSD", "M30", "2015-12-01", "2016-01-08", "%Y-%m-%d")
    # bar_array = get_period_bars("EURUSD", )
    print(bar_array)
