# -*- coding:utf-8 -*-

def lowest(length, offset, price=None):
    min_ = 9999999
    if price is None:
        price = low
    for i in range(length):
        min_ = min(price[i+offset], min_)
    return min_
