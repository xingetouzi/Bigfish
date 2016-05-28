# -*- coding:utf-8 -*-
import logging

logger = logging.getLogger("RuntimeSignal")


def init():
    pass


def handle():
    logger.info("%s %s %s %s %s" % (BarNum, MarketPosition, Pos.volume, Cap.margin, Cap.available))
    print(BarNum, MarketPosition, Pos.volume, Cap.margin, Cap.available)
    if Pos.volume >= 0.1:
        BuyToCover(Symbol, Pos.volume)
    if BarNum % 6 != 0:
        SellShort(Symbol, 0.01)
        SellShort(Symbol, 0.01)
        SellShort(Symbol, 0.01)
        # else:
        # BuyToCover(Symbol, Pos.volume)
