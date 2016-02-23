base = 100000

def init():
    pass

def handle():
    print('-------------')
    print('BarNum<%s>:' % BarNum)
    print('Symbols:\n%s' % Symbols)
    print('Symbol:\n%s' % Symbol)
    print('Positions:\n%s' % Positions)
    print('Pos:\n%s' % Pos)
    print('MarketPosition:\n%s' % MarketPosition)
    print('CurrentContracts\n%s' % CurrentContracts)
    print('OHLC:\n%s,%s,%s,%s\n%s,%s,%s,%s' % (Open[0], High[0] , Low[0], Close[0], O[0], H[0], L[0], C[0]))