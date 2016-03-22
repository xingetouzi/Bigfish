# -*- coding:utf-8 -*-
#计算一组时间序列数据（如开盘价、收盘价、最高价、最低价、收益率等）的最低值
#输入参数：
#length 时间长度 int 
#price  时间序列数据 序列数组 默认为最低价数据
#offset 位移数(从前多少根bar开始) int 默认为0

def Lowest(length,price=None,offset=0):
    if price is None:
        price = Low
    min_ = price[offset]
    for i in range(min(length, BarNum)):
        min_ = min(price[i + offset], min_)
    return min_
