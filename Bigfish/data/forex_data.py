# -*- coding: utf-8 -*-
import time

import redis
from pymongo import MongoClient

db = MongoClient("mongodb://root:Xinger520@act.fxdayu.com/forex").forex
tf_peroids = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400, "W1": 604800}
pool = redis.ConnectionPool(host='139.129.19.54', port=6379, db=0, password="Xinger520")


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
    filters = {"ctime": {"$gte": start_time}}
    if end_time:
        filters["ctime"]["$lte"] = end_time
    coll = "%s_%s" % (symbol, time_frame)
    cursor = db[coll].find(filters)
    bar_list = []
    for row in cursor:
        bar_list.append(row)
    return bar_list


def get_number_bars(symbol, time_frame, number=720):
    """
    获取最新number(默认为720)数量的 Bar 列表
    (不建议使用,推荐使用 get_period_bars(symbol, time_frame, start_time))
    :param symbol: 品种名称
    :param time_frame: 时间尺度
    :param number: bar 数量
    :return:
    """
    __check_tf__(time_frame)
    end_time = int(time.time())
    start_time = end_time - number * tf_peroids[time_frame]
    bar_list = []
    while len(bar_list) < number:  # 递归获取
        bar_list += get_period_bars(symbol, time_frame, start_time, end_time)
        end_time = start_time
        start_time = end_time - (number - len(bar_list)) * tf_peroids[time_frame]
    return bar_list


def get_latest_bar(symbol, time_frame, utf=False):
    """
    根据品种和时间尺度,获取最新的 Bar
    :param symbol: 品种名称
    :param time_frame: 时间尺度
    :param utf: 返回的键是否用unicode编码, 默认从redis返回的是byte(b'high')
    :return:
    """
    __check_tf__(time_frame)
    r = redis.Redis(connection_pool=pool)
    coll = "%s_%s" % (symbol, time_frame)
    bar = r.hgetall(coll)
    if utf:  # 转化为 utf8 编码的字典
        utf_bar = {}
        for key, value in bar.items():
            utf_bar[key.decode("utf8")] = value.decode("utf8")
        return utf_bar
    return bar


def __check_tf__(time_frame):
    if not (time_frame in tf_peroids.keys()):
        raise ValueError("Not supported time_frame: %s" % time_frame)

if __name__ == '__main__':
    bar_array = get_period_bars("EURUSD", "M30", "2015-12-01", "2016-01-08", "%Y-%m-%d")
    # bar_array = get_period_bars("EURUSD", )
    print(bar_array)
    bar_array = get_latest_bar("EURUSD", "M30", utf=True)
    print(bar_array)
