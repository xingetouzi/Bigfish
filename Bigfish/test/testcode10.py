# -*- coding:utf-8 -*-

def init():
    pass


def handle():
    print(MarketPosition, Pos.volume, Cap.margin, Cap.available)
    if Pos.volume >= 0.1:
        BuyToCover(Symbol, Pos.volume)
    if BarNum % 6 != 0:
        SellShort(Symbol, 0.01)
        SellShort(Symbol, 0.01)
        SellShort(Symbol, 0.01)
    # else:
        # BuyToCover(Symbol, Pos.volume)
