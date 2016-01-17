def ATR(length=10):
    if barnum == 1:
        atr = 0
    if barnum <= length:
        for i in range(barnum - 1, -1, -1):
            atr += true_range(i)
    else:
        atr = atr + true_range(0) - true_range(length - 1)
    return atr / length
