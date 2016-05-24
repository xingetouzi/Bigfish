# -*- coding:utf-8 -*-

import logging
logger = logging.getLogger("RuntimeSignal")

def init():
    pass


def handle():
    Export(macd)
    macd[0]=MACD(12,26,Close,0)
    logger.info("macdValue=%s"%(macd[0],))
    if BarNum>1:
        if MarketPosition==0:
            if macd[1]<0 and macd[0]>0:
                Buy(Symbol,1)
            elif macd[1]>0 and macd[0]<0:
                SellShort(Symbol,1)
        if MarketPosition>0:
            if macd[1]>0 and macd[0]<0:
                Sell(Symbol,1)
        if MarketPosition<0:
            if macd[1]<0 and macd[0]>0:
                BuyToCover(Symbol,1)
