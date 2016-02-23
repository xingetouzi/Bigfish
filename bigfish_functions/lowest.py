# -*- coding:utf-8 -*-

def lowest(length, offset=0, price=None):
    if price is None:
        price = Low
    min_ = price[0]
    for i in range(min(length, BarNum)):
        min_ = min(price[i + offset], min_)
    return min_
