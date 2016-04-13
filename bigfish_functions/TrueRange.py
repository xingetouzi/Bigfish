# -*- coding:utf-8 -*-
#计算某一时刻的真实波动区间（最高价-最低价）
#输入参数：
#offset 位移数(从前多少根bar开始) int 默认为0（当前的真实波动区间）

def TrueRange(offset=0):
    if BarNum <= offset:
        return 0
    elif BarNum == offset + 1:
        return H[offset] - L[offset]
    else:
        return max(H[offset] - L[offset], C[offset + 1] - L[offset] , H[offset] - C[offset + 1])