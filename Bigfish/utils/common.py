# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 10:46:33 2015

@author: BurdenBear
"""
import re
from datetime import datetime


###################################################################
def string_to_html(string):
    return string.replace(' ', '&nbsp;').replace('\r\n', '<br>').replace('\r', '<br>').replace('\n', '<br>')


###################################################################
# 通用的属性（property）封装方法，通过反射比直接在类中写特殊的方法慢4~5倍，适用于非内部循环变量
def get_attr(self, attr=''):
    return getattr(self, '_%s__%s' % (self.__class__.__name__, attr))


def set_attr(self, value, attr='', check=lambda x: None, handle=None):
    after_check = check(value)
    if not after_check:
        setattr(self, '_%s__%s' % (self.__class__.__name__, attr), value)
    elif handle:
        setattr(self, '_%s__%s' % (self.__class__.__name__, attr), handle(check))
    else:
        setattr(self, '_%s__%s' % (self.__class__.__name__, attr), after_check)


###################################################################
_TIME_FRAME = {item: n for n, item in
               enumerate(['W1', 'D1', 'H1', 'M30', 'M15', 'M10', 'M5', 'M1'])}
_TIME_FRAME_PERIOD = {'W1': 604800, 'D1': 86400, 'H1': 3600, 'M30': 1800, 'M15': 900, 'M10': 600, 'M5': 300, 'M1': 60}


def check_time_frame(time_frame):
    if not time_frame in _TIME_FRAME.keys():
        raise (ValueError("不合法的time_frame值:%s" % time_frame))
    return True


def get_time_frame_bit(time_frame):
    check_time_frame(time_frame)
    return 1 << _TIME_FRAME[time_frame]


###################################################################
def __replace_all(string, olds, new):
    for old in olds:
        string = string.replace(old, new)
    return (string)


__PATTERNS = {re.compile(r'\A' + __replace_all(format_, ['%m', '%d', '%H', '%M', '%S'], r'\d{2}')
                         .replace('%Y', r'\d{4}') + r'\Z'): format_ for format_
              in ['%Y-%m-%d', '%Y-%m-%d %H:%M%:%S']}


def get_datetime(string):
    for pattern, format_ in __PATTERNS.items():
        if pattern.match(string):
            return datetime.strptime(string, format_)
    raise (ValueError("不合法的时间格式"))


###################################################################
def quick_sort(l, r, arr, key):
    if l > r: return
    i = l
    j = r
    mid = key(arr, (l + r) >> 1)
    while i <= j:
        while key(arr, i) < mid and i <= r: i += 1
        while key(arr, j) > mid and j >= l: j -= 1
        if i <= j:
            temp = arr[i]
            arr[i] = arr[j]
            arr[j] = temp
            i += 1
            j -= 1
    if j > l: quick_sort(l, j, arr, key)
    if i < r: quick_sort(i, r, arr, key)