# -*- coding:utf-8 -*-
# 计算一组时间序列数据（如开盘价、收盘价、最高价、最低价、收益率等）的最高值
# 输入参数：
# length 时间长度 int
# price  时间序列数据 序列数组 默认为最高价数据
# offset 位移数(从前多少根bar开始) int 默认为0
# 若当前K线总数不足以支持计算,(BarNum>length+offset时才能支持计算)返回None

def Highest(length, price=None, offset=0):
    if length <= 0:
        return None
    if price is None:
        price = High
    if BarNum <= length + offset:
        return None
    else:
        max_ = price[offset]
        for i in range(length - 1):
            max_ = max(price[i + offset + 1], max_)
        return max_
