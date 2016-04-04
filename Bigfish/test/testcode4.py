base = 100000

def init():
    pass

def handle():
    def jincha():
        if MA(5)<MA(10):
            return True
        else:
            return False
    Sum=Summation(10, Close)
    print(Sum, jincha())