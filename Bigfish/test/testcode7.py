# 可以import我们平台支持的python模块，比如pandas，ta-lib等。
import time


def init():
    # 初始化函数，在该函数中可以进行一些全局变量的设定，该功能将在之后开放。
    start_time = time.time()


def handle():
    # 开始编写你的主要算法逻辑
    # 通过变量Open，Close，High，Low，Time，Volume获取K线数据。
    # 通过Buy，Sell，SellShort，BuyToCover进行下单。
    # 详情请参见文档中关于系统变量和函数的详细说明。
    # 若当前没有持仓，且收盘价小于开盘价
    if MarketPosition == 0 and Close[0] < Open[0]:
        Buy(Symbol, 1)  # 开一手多仓
    # 若当前持多仓，且收盘价大于开盘价
    elif MarketPosition > 0 and Close[0] > Open[0]:
        Sell(Symbol, 1)  # 平一手多仓
