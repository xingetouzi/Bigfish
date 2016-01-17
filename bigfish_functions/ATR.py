def ATR(length=10):
    export(atr)
    if barnum == 1:
        atr[0] = true_range(0)
    elif barnum <= length:
        for i in range(barnum - 1, -1, -1):
            atr[0] = atr[1] + true_range(i)
    else:
        atr[0] = atr[1] + true_range(0) - true_range(length - 1)
    return atr[0] / min(length, barnum)
