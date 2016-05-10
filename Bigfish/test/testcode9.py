# -*- coding:utf-8 -*-

def init():
    EntryPrice=0

def handle(TakeProfit=50, StopLoss=100):
    # 若当前没有持仓，且收盘价小于开盘价
    if MarketPosition==0 and Close[0]<Open[0]:
        Buy(Symbol,1) # 开一手多仓
        EntryPrice=Close[0]
    # 若当前持有多仓，且收盘价大于开盘价
    elif MarketPosition>0 and Close[0]>EntryPrice+TakeProfit*Point:
        print(Close[0],EntryPrice)
        Sell(Symbol,1) # 平多仓
    elif MarketPosition>0 and Close[0]<EntryPrice-StopLoss*Point:
        Sell(Symbol,1) # 平多仓