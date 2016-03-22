# -*- coding:utf-8 -*-
#计算一组时间序列数据（如开盘价、收盘价、最高价、最低价、收益率等）的指数移动平均
#输入参数：
#length 时间长度 int
#price  时间序列数据 序列数组 默认为收盘价数据
#offset 位移数(从前多少根bar开始) int 默认为0

def EMA(length,price=None,offset=0):
    export(ema)
    if not price:
        price=Close
    w=2/(length+1) #平滑系数
    if barnum==1:
        ema[0]=price[0]
    else: 
        ema[0]=w*price[0]+(1-w)*ema[1]
    if BarNum<=offset:
        return 0
    else:
        return ema[offset]