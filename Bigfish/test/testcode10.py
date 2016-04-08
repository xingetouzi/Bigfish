# -*- coding:utf-8 -*-
import traceback

def init():
    pass


def handle(MaxLen=60 * 24 * 4 + 1):
    # print(MA(60 * 24 * 4))
    if BarNum % 6 != 0 :
        SellShort(Symbol, 1)
    else:
        BuyToCover(Symbol, Pos.volume)
    print(MarketPosition, Pos.volume)