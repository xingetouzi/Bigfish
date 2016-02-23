# -*- coding:utf-8 -*-

def ATR(length=10):
    Export(atr)
    if BarNum == 1:
        atr[0] = true_range(0)
    elif BarNum <= length:
        atr[0] = atr[1] + true_range(0)
    else:
        atr[0] = atr[1] + true_range(0) - true_range(length)
    return atr[0] / min(length, BarNum)
