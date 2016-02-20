# -*- coding:utf-8 -*-
from collections import deque


class Deque(deque):
    def __hash__(self):
        return 0


class g:
    pass


if __name__ == '__main__':
    x = g()
    y = Deque([1.21036])
    d = {((1, 2), (3, x)): 0}
    d[(3, (4, y))] = 1
    print(d)
    print(d[(3, (4, y))])