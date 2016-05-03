# -*- coding: utf-8 -*-
import copy
from collections import deque, UserList
from datetime import datetime


class DictLike:
    __slots__ = []

    def to_dict(self):
        cls = self.__class__.__name__
        return ({slot.replace('__', ''): getattr(self, slot.replace('__', '_%s__' % cls))
                 for slot in self.get_keys()})

    @classmethod
    def from_dict(cls, dict_):
        obj = cls()
        for slot in cls.get_keys():
            setattr(obj, slot, dict_[slot])
        return obj

    @classmethod
    def get_keys(cls):
        return list(map(lambda x: x.replace('__', ''), cls.__slots__))

    def __getitem__(self, key):
        return getattr(self, key)


class FactoryWithID:
    _class = None

    def __init__(self):
        self._id = 0

    def get_id(self):
        return self._id

    def next(self):
        self._id += 1
        return self._id

    def reset(self):
        self._id = 0

    def new(self, *args, **kwargs):
        return self._class(*args, id=str(self.next()), **kwargs)

    def __call__(self, *args, **kwargs):
        return self.new(*args, **kwargs)


class FactoryWithPrefixID(FactoryWithID):
    _class = None

    def _get_prefix(self):
        raise not NotImplementedError

    def get_prefix(self):
        return self._get_prefix()

    prefix = property(get_prefix)

    def new(self, *args, **kwargs):
        id_ = self.prefix + '-' + str(self.next()) if self.prefix else str(self.next())
        return self._class(*args, id=id_, **kwargs)


class FactoryWithTimestampPrefixID(FactoryWithPrefixID):
    _class = None

    def __init__(self, prefix='', timestamp=False):
        super().__init__()
        self._prefix = prefix
        self._timestamp = timestamp

    def _get_prefix(self):
        if self._timestamp:
            return self._prefix + '-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        else:
            return self._prefix


class FactoryWithList(FactoryWithID):
    _class = None

    def __init__(self):
        super(FactoryWithList, self).__init__()
        self.all = []

    def new(self, *args, **kwargs):
        result = super(FactoryWithList, self).new(*args, **kwargs)
        self.all.append(result)
        return result

    def clear(self):
        """
        重置ID计数器,清空存储。
        """
        self.all.clear()
        self.reset()


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
