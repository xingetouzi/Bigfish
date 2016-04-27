# -*- coding:utf-8 -*-
# 计算一组时间序列数据（如开盘价、收盘价、最高价、最低价、收益率等）的(样本)标准差
# 输入参数：
# length 时间长度 int
# price  时间序列数据 序列数组 默认为收盘价数据
# offset 位移数(从前多少根bar开始) int 默认为0

def StdDev(length, price=None, offset=0):
    Export(std_dev)
    Export(sumx2, sumx)  # sumx2: summation of x^2, sumx: summation of x
    if not price:
        price = Close
    if BarNum < length:  # not enough bar
        std_dev[0] = None
        sumx2[0] = None
        sumx[0] = None
    else:
        if BarNum == length:  # on first bar
            sumx2[0] = 0
            sumx[0] = 0
            for i in range(length):
                sumx2[0] += price[i] * price[i]
                sumx[0] += price[i]
        else:
            sumx2[0] = sumx2[1] + price[0] * price[0] - price[length] * price[length]
            sumx[0] = sumx[1] + price[0] - price[length]
        std_dev[0] = ((sumx2[0] - sumx[0] * sumx[0] / length) / (length - 1 if length > 1 else 1)) ** 0.5
    if BarNum <= offset:
        return None
    else:
        return std_dev[offset]
