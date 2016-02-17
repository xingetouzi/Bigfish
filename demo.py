﻿# -*- coding:utf-8 -*-
base = 100000  # 设置起始资金


def init():  # init函数将在策略被加载时执行，进行一些初始化的工作
    pass


# 每一个不以init为名的函数都将被视为一个信号，信号在每次行情数据到来时都会被执行
def handle(slowlength=20, fastlength=10, lots=1):  # 函数签名的中只支持带默认值的参数(即关键字参数)，可以对此处的参数使用我们平台的参数优化功能
    # 如果需要定义普通的函数而非信号，可以在信号中嵌套定义
    def highest(price, len, offset=0):  # 计算从当前K线向前偏移offset根K线开始起，之前n根K线的price序列数组中的最高价
        max_ = None
        for index in range(len):
            if not max_:
                max_ = price[index + offset]
            else:
                max_ = max(price[index + offset], max_)
        return max_

    atr = ATR(fastlength)  # 系统函数ATR(n),表示最近n根K线的Average True Range
    print(atr)  # print为输出函数，输出的内容将显示在下方的输出栏中
    if barnum > slowlength:  # barnum表示当前的K线数，从1开始计数，第一根K线对应barnum=1
        symbol = symbols[0]  # 全局变量symbols是一个列表，表示用户选择的交易品种池
        # 关于行情的全局变量有: open, high, low, close, volume, time, 类型均为序列数组，序列数组的特点是从当前K线向后开始索引，
        # 例如close[0],表示最后一根K线的收盘价(也是最后一个tick的价格)，而close[1]表示上一根K线的收盘价
        position = marketpositions.get(symbol, None)
        # marketpositions为保存各品种仓位信息的字典，key为交易品种的代码，value为表示对应的仓位的Position对象，详见文档
        # position = marketposition # 对于单品种策略而言，此行语句可以代替以上两行语句
        # buy, sell, short, cover,为交易指令函数，分别为对应开多单，平多单，开空单，平空单，函数签名详情请见文档
        if position == 0:  # 若当前无持仓
            if close[0] >= highest(high, slowlength, 1) + atr:
                buy(symbol, lots)  # 开多仓，买入lots手symbol所代表的看涨合约
            if close[0] <= lowest(slowlength, 1) - atr:
                # 系统函数lowest(n, offset=0, price=None),计算从当前K线向前偏移offset根K线开始起，之前n根K线的最低价，
                short(symbol, lots)  # 开空仓，买入lots手symbol所代表的看跌合约
        elif position > 0:  # 若当前持多仓
            if close[0] <= lowest(fastlength, offset=1) - atr:
                sell(symbol, lots)  # 平多仓，卖出lots手symbol所代表的看涨合约
        elif position < 0:  # 若当前持空仓
            if close[0] >= highest(high, fastlength, 1) + atr:
                cover(symbol, lots)  # 平空仓，卖出lots手symbol所代表的看跌合约