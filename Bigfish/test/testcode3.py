# -*- coding:utf-8 -*-


def init():
    pass


def handle(slowlength=20, fastlength=10, lots=1):
    def highest(price, len, offset=0):
        max_ = 0
        for index in range(len):
            max_ = max(price[index + offset], max_)
        return max_

    atr = ATR(fastlength)
    # print('%s:%s' % (barnum, atr))
    if BarNum > slowlength:
        if MarketPosition == 0:
            if Close[0] >= highest(High, slowlength, 1) + atr:
                Buy(Symbol, lots)
            if Close[0] <= lowest(slowlength, 1) - atr:
                SellShort(Symbol, lots)
        elif MarketPosition > 0:
            if Close[0] <= lowest(fastlength, offset=1) - atr:
                Sell(Symbol, lots)
        elif MarketPosition < 0:
            if Close[0] >= highest(High, fastlength, 1) + atr:
                BuyToCover(Symbol, lots)
