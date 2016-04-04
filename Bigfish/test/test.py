# -*- coding:utf-8 -*-
from collections import deque
from Bigfish.models.common import Deque as Dq
import codecs
from weakref import ref, WeakKeyDictionary
import sys


class g:
    pass

def weakref_test():
    print('weakref test begin')
    cache = WeakKeyDictionary()
    a = g()
    print(sys.getrefcount(a))
    print(sys.getrefcount(a))
    b = ref(a)
    cache[a] = 1
    print(cache.keyrefs())
    print(sys.getrefcount(a))
    del a
    print(cache.keyrefs())
    print(sys.getrefcount(b()))
    print(cache[b()])


def gc_test():
    print('gc_test begin')

    def f():
        return [g()]

    l = f()
    r = ref(l[0])
    print(sys.getrefcount(r()))
    l.clear()
    print(r())
    print(sys.getrefcount(r()))


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
    gc_test()
    weakref_test()
