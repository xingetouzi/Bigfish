# -*- coding:utf-8 -*-

def highest(length, offset=0, price=None):
    if price == None:
        price = High
    max_ = price[0]
    for i in range(min(length, BarNum)):
        max_ = max(price[i + offset], max_)
    return max_
