# -*- coding:utf-8 -*-
from collections import deque
from Bigfish.models.common import Deque as Dq
import codecs

class g:
    pass



if __name__ == '__main__':
    x = g()
    y = Dq([1.21036])
    z = Dq([1.23123])
    d = {((1, 2), (3, x)): 0}
    d[(3, (4, y))] = 1
    print(d)
    print(hash(y))
    print(hash(z))
    print(d[(3, (4, y))])
    try:
        f = codecs.open("testcode1.py", "r", "utf-8")
        print(1/0)
    except:
        f.close()
    finally:
        f.close()
