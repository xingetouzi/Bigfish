# -*- coding:utf-8 -*-
#计算一组时间序列数据（如开盘价、收盘价、最高价、最低价、收益率等）的最高值
#输入参数：
#length 时间长度 int 
#price  时间序列数据 序列数组 默认为最高价数据
#offset 位移数(从前多少根bar开始) int 默认为0

def Highest(length, price=None,offset=0):
    if price == None:
        price = High
    max_ = price[offset]
    for i in range(min(length, BarNum)):
        max_ = max(price[i + offset], max_)
    return max_
