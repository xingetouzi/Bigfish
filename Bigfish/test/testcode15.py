# -*- coding:utf-8 -*-


def init():
    pass

def handle():
    ma5 = MA(5)
    ma2 = MA(2)
    print(ma5, MA(5), ma2, MA(2))
    atr2 = ATR(2)
    atr30 = ATR(30)
    # 若当前没有持多头仓位，且收盘价大于前一日MA5与前一日ATR之和，且大于前一日MA20与前一日ATR之和
    if MarketPosition<=0 and Close[0]>ma5 + atr2 and Close[0]>ma2 + atr30:
        Buy(Symbol,1) # 开一手多仓
    # 若当前没有持空头仓位，且收盘价小于前一日MA5与前一日ATR之差，且小于前一日MA20与前一日ATR之差
    elif MarketPosition>=0 and Close[0]<ma5 - atr2 and Close[0]>ma2 - atr30:
        SellShort(Symbol,1) # 开一手空仓