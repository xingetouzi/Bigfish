# -*- coding:utf-8 -*-

def highest(length, offset, price=None):
    max_ = 0
    if price is None:
        price = high
    for i in range(length):
        max_ = max(price[i+offset], max_)
    return max_
