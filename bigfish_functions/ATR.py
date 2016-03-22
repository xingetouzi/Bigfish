# -*- coding:utf-8 -*-
#计算一段时间内的平均真实波动区间
#输入参数：
#length 时间长度 int
#offset 位移数(从前多少根bar开始) int 默认为0（当前的真实波动区间）

def ATR(length,offset=0):
    Export(atr)
    if BarNum == 1:
        atr[0] = TrueRange(0)
    elif BarNum <= length:
        atr[0] = atr[1] + TrueRange(0)
    else:
        atr[0] = atr[1] + TrueRange(0) - TrueRange(length)
    if BarNum<=offset:
        return 0
    else:
        return atr[offset]/min(BarNum-offset,length)
