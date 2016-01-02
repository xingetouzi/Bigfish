# -*- coding: utf-8 -*-
import time
from pymongo import MongoClient
db = MongoClient("mongodb://root:Xinger520@act.fxdayu.com/forex").forex
tf_peroids = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400, "W1": 604800}


def get_period_bars(symbol, time_frame, start_time, end_time=None):
    """
    获取从start_time至end_time这段时间内的所有 Bar
    :param symbol: 品种名称
    :param time_frame: 时间尺度
    :param start_time: 开始时间
    :param end_time: 结束时间
    :return 包含所有 Bar 的列表
    """
    __check_tf__(time_frame)
    filters = {"ctime": {"$gte": start_time}}
    if end_time:
        filters["ctime"]["$lte"] = end_time
    coll = "%s_%s" % (symbol, time_frame)
    cursor = db[coll].find(filters)
    bar_list = []
    for row in cursor:
        # bar_list.append({"open": row["open"], "high": row["high"], "low": row["low"], \
        # "close": row["close"], "volume": row["volume"], "ctime":row["ctime"]})
        bar_list.append(row)
    return bar_list


def get_number_bars(symbol, time_frame, number=720):
    """
    获取最新的number(默认为720)
    :param symbol: 品种名称
    :param time_frame: 时间尺度
    :param number:
    :return:
    """
    __check_tf__(time_frame)
    end_time = int(time.time())
    start_time = end_time - number * tf_peroids[time_frame]
    bar_list = []
    while len(bar_list) < number:
        bar_list += get_period_bars(symbol, time_frame, start_time, end_time)
        end_time = start_time
        start_time = end_time - (number - len(bar_list)) * tf_peroids[time_frame]
    return bar_list


def __check_tf__(time_frame):
    if not (time_frame in tf_peroids.keys()):
        raise ValueError("Not supported time_frame: %s" % time_frame)


# bar_array = get_number_bars("EURUSD", "M30", 20)
# print(bar_array)
