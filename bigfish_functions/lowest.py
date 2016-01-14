def lowest(length, price=None):
    min_ = 9999999
    if price is None:
        price = low
    for i in range(length):
        min_ = min(price[i], min_)
    return min_
