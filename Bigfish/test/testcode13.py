# -*- coding:utf-8 -*-


def init():
    pass


def handle(fastlength=5, slowlength=10):
    # 若当前没有持仓，且收盘价小于开盘价
    ma_f_0 = MA(fastlength)
    ma_s_0 = MA(slowlength)
    ma_f_1 = MA(fastlength, offset=1)
    ma_s_1 = MA(slowlength, offset=1)
    if MarketPosition == 0:
        if ma_f_1 < ma_s_1 < ma_s_0 < ma_f_0:
            Buy(Symbol, 1)
        elif ma_f_1 > ma_s_1 > ma_s_0 > ma_f_0:
            SellShort(Symbol, 1)
    if MarketPosition > 0:
        if ma_f_1 > ma_s_1 and ma_f_0 < ma_s_0:
            Sell(Symbol, Pos.volume)
    if MarketPosition < 0:
        if ma_f_1 < ma_s_1 and ma_f_0 > ma_s_0:
            Buy(Symbol, Pos.volume)
