# -*- coding:utf-8 -*-
# 计算一组时间序列数据（如开盘价、收盘价、最高价、最低价、收益率等）的Bolling Bonds.
# 输入参数：
# length 时间长度 int
# price  时间序列数据 序列数组 默认为收盘价数据
# offset 位移数(从前多少根bar开始) int 默认为0
# 返回值:
# 如果有足够的bar用于计算，返回Boll对象,有以下属性;否则返回None
# Boll.ma: 移动平均，即bolling中轨线;
# Boll.std: 1/4 Boll带宽;
# Boll.up: Boll带上轨线;
# Boll.down: Boll带下轨线;

def Bolling(length, price=None, offset=0):
    class Boll:
        __slot__ = ['ma', 'up', 'down', 'std']

    if price == None:
        price = Close
    ma = MA(length, price, offset)
    std = StdDev(length, price, offset)
    if ma is None or std is None:
        return None
    else:
        result = Boll()
        result.ma = ma
        result.std = std
        result.up = ma + 2 * std
        result.down = ma - 2 * std
        return result
