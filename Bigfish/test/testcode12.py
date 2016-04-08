# -*- coding:utf-8 -*-


def init():
	pass

def handle():
    # 若当前没有持仓，且收盘价小于开盘价
    if MarketPosition == 0:
        if MA(5,C,1)<MA(10,C,1) and MA(5)>MA(10) and MA(10,C,1)<MA(10):
            Buy(Symbol, 1)
        elif MA(5,C,1)>MA(10,C,1) and MA(5)<MA(10) and MA(10,C,1)>MA(10):
            SellShort(Symbol, 1)
    if MarketPosition > 0:
    	if MA(5,C,1)>MA(10,C,1) and MA(5)<MA(10):
            Sell(Symbol, Pos.volume)
    if MarketPosition < 0:
        if MA(5,C,1)<MA(10,C,1) and MA(5)>MA(10):
            Buy(Symbol, Pos.volume)