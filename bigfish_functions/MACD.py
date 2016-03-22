# -*- coding:utf-8 -*-
#计算一组时间序列数据（如开盘价、收盘价、最高价、最低价、收益率等）的MACD指标
#输入参数：
#fastLen 快均线时间长度 int 
#slowLen 慢均线时间长度 int
#price  时间序列数据 序列数组 默认为收盘价数据
#offset 位移数(从前多少根bar开始) int 默认为0

def MACD(fastLen,slowLen,price=None,offset=0):
    return EMA(fastLen,offset,price)-EMA(slowLen,offset,price)