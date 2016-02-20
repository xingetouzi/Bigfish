# -*- coding:utf-8 -*-

def summation(length,price=None):
    export(sum_)
    if not price:
        price=close
    if barnum == 1:
        sum_[0] = price[0]
    elif barnum <= length:
            sum_[0]=sum_[1]+price[0]
    else:
        sum_[0]=sum_[1]+price[0]-price[length]
    return sum_[0]