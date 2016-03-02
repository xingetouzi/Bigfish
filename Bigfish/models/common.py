# -*- coding: utf-8 -*-
import copy
from collections import deque, UserList


class DictLike:
    __slots__ = []

    def to_dict(self):
        cls = self.__class__.__name__
        return ({slot.replace('__', ''): getattr(self, slot.replace('__', '_%s__' % cls))
                 for slot in self.__slots__})

    @classmethod
    def get_fields(cls):
        return list(map(lambda x: x.replace('__', ''), cls.__slots__))

    def __getitem__(self, key):
        return getattr(self, key)


class FactoryWithID:
    _class = None

    def __init__(self):
        self.__id = 0

    def next_id(self):
        self.__id += 1
        return self.__id

    def get_id(self):
        return self.__id

    def set_id(self, num):
        self.__id = num

    def reset_id(self):
        self.__id = 0

    def __call__(self, *args, **kwargs):
        return self._class(*args, **kwargs, id=self.next_id())


class HasID:
    """有自增长ID对象的通用方法"""
    __slots__ = []
    __AUTO_INC_NEXT = 0

    # XXX 是否把自增写入
    @classmethod
    def next_auto_inc(cls):
        cls.__AUTO_INC_NEXT += 1
        return cls.__AUTO_INC_NEXT

    @classmethod
    def get_auto_inc(cls):
        return cls.__AUTO_INC_NEXT

    @classmethod
    def set_auto_inc(cls, num):
        cls.__AUTO_INC_NEXT = num


class Deque(deque, HasID):
    def __init__(self, *args, **kwargs):
        super(Deque, self).__init__(*args, **kwargs)
        self.__id = self.next_auto_inc()

    def __hash__(self):
        return self.__id


class SeriesList(UserList):
    __MAX_LENGTH = 10000

    def __init__(self, initlist=None, maxlen=None):
        self.maxlen = None
        if maxlen:
            if isinstance(maxlen, int):
                if maxlen > 0:
                    self.maxlen = maxlen
        else:
            self.maxlen = self.__class__.__MAX_LENGTH
        if not self.max_length:
            raise (ValueError("参数max_length的值不合法"))
        if len(initlist) > self.max_length:
            super().__init__(list(reversed(initlist[-maxlen:])))
        else:
            super().__init__(list(reversed(initlist)))
        self.last = len(self.data)
        self.full = self.last == self.max_length
        self.last %= self.max_length

    def append(self, item):
        if not self.full:
            self.data.append(item)
            self.last += 1
            if self.last == self.max_length:
                self.full = True
                self.last = 0
        else:
            self.data[self.last] = item
            self.last = (self.last + 1) % self.max_length

    def __getitem__(self, i):
        if not self.full:
            return self.data[self.last - i - 1]
        else:
            return self.data[(self.last - i - 1 + self.max_length) % self.max_length]

    def __setitem__(self, i, item):
        raise TypeError("SeriesList is read-only")

    def __delitem__(self, i):
        raise TypeError("SeriesList is read-only")
