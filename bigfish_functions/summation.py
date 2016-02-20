# -*- coding:utf-8 -*-

def summation(length,price=None):
    export(Sum)
    if not price:
        price=close
    if barnum <= length:
        for i in range(length):
            Sum[0]=Sum[0]+price[i]
    else:
        Sum[0]=Sum[1]+price[0]-price[length]
    return Sum[0]