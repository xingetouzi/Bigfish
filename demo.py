# -*- coding:utf-8 -*-

def init():
    pass


def handle():
    # 若当前没有持仓，且收盘价小于开盘价
    if MarketPosition == 0 and Close[0] < Open[0]:
        # 开一手多仓
        Buy(Symbol, 1)
        # 若当前持有多仓，且收盘价大于开盘价
    if MarketPosition > 0 and Close[0] > Open[0]:
        # 平多仓
        Sell(Symbol, 1)