# -*- coding:utf-8 -*-
#计算length日相对强弱指标(RSI)
#输入参数：
#length 时间长度 int
#offset 位移数(从前多少根bar开始) int 默认为0
#BAR数不足以支持计算时返回NONE

def RSI(length=14, offset=0):
    Export(rs_up, rs_down, rsi)
    if BarNum < length:
        rsi[0] = None
        rs_up[0] = None
        rs_down[0] = None
    else:
        if BarNum == length:
            rs_up[0] = 0
            rs_down[0] = 0
            for index in range(length):
                change = C[index] - O[index]
                if change > 0:
                    rs_up[0] += change
                else:
                    rs_down[0] -= change
        else:
            rs_up[0] = rs_up[1]
            rs_down[0] = rs_down[1]
            change = C[0] - O[0]
            if change > 0:
                rs_up[0] += change
            else:
                rs_down[0] -= change
            change = C[length] - O[length]
            if change > 0:
                rs_up[0] -= change
            else:
                rs_down[0] += change
        if rs_down[0] > 0.0000001:
            rs = rs_up[0] / rs_down[0]
            rsi[0] = 100 * rs / (1 + rs)
        else:
            rsi[0] = 100
    if BarNum > offset:
        return rsi[offset]
    else:
        return None