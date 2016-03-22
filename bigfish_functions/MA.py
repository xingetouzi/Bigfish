# -*- coding:utf-8 -*-
#计算一组时间序列数据（如开盘价、收盘价、最高价、最低价、收益率等）的简单移动平均
#输入参数：
#length 时间长度 int
#price  时间序列数据 序列数组 默认为收盘价数据
#offset 位移数(从前多少根bar开始) int 默认为0

def MA(length,price=None,offset=0):
    Sum=Summation（length,offset,price）
    if BarNum<=offset:
        return 0
    else:
        return Sum/min(BarNum-offset,length)