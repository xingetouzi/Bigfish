# -*- coding:utf-8 -*-
base = 100000

def init():
    pass

def handle(slowlength=20, fastlength=10, lots=1):
    def highest(price, len, offset=0):
        max_ = 0
        for index in range(len):
            max_ = max(price[index + offset], max_)
        return max_
    atr = ATR(fastlength)
    export(a)
    a[0] = ATR(1)
    print('atr(1):%s' % a[0])
    print('atr(2):%s' % (ATR(1) if barnum== 1 else (a[0]+a[1])/2))
    print('atr(2):%s' % ATR(2))
    if barnum > slowlength:
        symbol = symbols[0]
        position = marketpositions.get(symbol, None)
        if position == 0:
            if close[0] >= highest(high, slowlength, 1) + atr:
                buy(symbol, lots)
            if close[0] <= lowest(slowlength, 1) - atr:
                short(symbol, lots)
        elif position > 0:
            if close[0] <= lowest(fastlength, offset=1) - atr:
                sell(symbol, lots)
        elif position < 0:
            if close[0] >= highest(high, fastlength, 1) + atr:
                cover(symbol, lots)