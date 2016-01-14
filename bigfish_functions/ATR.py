from .true_range import true_range


def ATR(high, low, length=10):
    barnum = len(high)
    atr = 0
    for i in range(min(length, barnum)-1, 0, -1):
        atr += true_range(high, low, i)
    atr /= length
    return atr