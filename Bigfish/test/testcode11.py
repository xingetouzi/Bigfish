# -*- coding:utf-8 -*-


def init():
    n=1
    TP=0.0
    SL=0.0

def handle():
    # 判断开仓
    if MarketPosition==0:
        if Close[0] >= Highest(20,Close,0):
            Buy(Symbol,1)
            SL=Close[0]-2*ATR(20)
            TP=Close[0]+0.5*ATR(20)
            n=1
        elif Close[0] <= Lowest(20,Close,0):
            SellShort(Symbol,1)
            SL=Close[0]+2*ATR(20)
            TP=Close[0]-0.5*ATR(20)
            n=1
    if MarketPosition>0:
        if Close[0]<SL:
            Sell(Symbol,Pos.volume)
        elif Close[0] > TP and n<6:
            Buy(Symbol,1)
            SL=SL+0.5*ATR(20)
            TP=TP+0.5*ATR(20)
            n=n+1
        elif Close[0]>SL and n==6:
            SL=max(SL,Close[0]-ATR(20))
    if MarketPosition<0:
        if Close[0]>SL:
            BuyToCover(Symbol,Pos.volume)
        elif Close[0]<TP and n<6:
            SellShort(Symbol,1)
            SL=SL-0.5*ATR(20)
            TP=TP-0.5*ATR(20)
            n=n+1
        elif Close[0]<SL and n==6:
            SL=min(SL,Close[0]+ATR(20))
