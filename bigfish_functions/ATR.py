def ATR(length=10):
    atr = 0
    for i in range(length, 0, -1):
        atr += true_range(i)
    atr /= length
    return atr
