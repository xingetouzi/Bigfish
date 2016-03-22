# -*- coding:utf-8 -*-
#计算某一时刻的真实波动区间（最高价-最低价）
#输入参数：
#offset 位移数(从前多少根bar开始) int 默认为0（当前的真实波动区间）

def TrueRange(offset=0):
    return High[offset] - Low[offset]