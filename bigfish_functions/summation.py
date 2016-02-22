# -*- coding:utf-8 -*-

def summation(length, price=None):
    Export(sum_)
    if not price:
        price = Close
    if BarNum == 1:
        sum_[0] = price[0]
    elif BarNum <= length:
        sum_[0] = sum_[1] + price[0]
    else:
        sum_[0] = sum_[1] + price[0] - price[length]
    return sum_[0]
