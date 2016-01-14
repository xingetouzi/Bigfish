def highest(length, price=None):
    max_ = 0
    if price is None:
        price = high
    for i in range(length):
        max_ = max(price[i], max_)
    return max_
