# -*- coding:utf-8 -*-
import logging

logger = logging.getLogger("Backtesting")


def init():
    pass


def handle():
    logger.info("%s %s %s %s %s" % (BarNum, MarketPosition, Pos.volume, Cap.margin, Cap.available))
    print(BarNum, MarketPosition, Pos.volume, Cap.margin, Cap.available)
    lots = 1
    if Pos.volume >= lots * 10:
        pass
        # BuyToCover(Symbol, Pos.volume)
    if BarNum % 6 != 0:
        SellShort(Symbol, 1)
        SellShort(Symbol, 1)
        SellShort(Symbol, 1)
        # else:
        # BuyToCover(Symbol, Pos.volume)
