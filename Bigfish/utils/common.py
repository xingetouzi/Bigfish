# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 10:46:33 2015

@author: BurdenBear
"""
from collections import UserList
from collections import deque
from datetime import datetime
import traceback
import re

###################################################################
def string_to_html(string):
    return(string.replace(' ', '&nbsp;').replace('\r\n', '<br>').replace('\r', '<br>').replace('\n', '<br>'))
###################################################################
def is_user_file(string, limit=r'\A\[.+\]\Z'):
    """判断是否是用户生成的文件，用于输出友好的错误日志"""
    pattern = re.compile(limit)
    match_ = pattern.match(string)
    print(match_)
    return(pattern.match(string)!=None)
###################################################################
def get_user_friendly_traceback(exc_type, exc_value, exc_traceback):
    tb_message = traceback.format_list(filter(lambda x:is_user_file(str(x[0])),traceback.extract_tb(exc_traceback)))
    print(tb_message)
    format_e = traceback.format_exception_only(exc_type, exc_value)
    tb_message.append(''.join(format_e))
    return(tb_message)
###################################################################
#通用的属性（property）封装方法，通过反射比直接在类中写特殊的方法慢4~5倍，适用于非内部循环变量
def get_attr(self, attr=''):
    return(getattr(self,'_%s__%s'%(self.__class__.__name__,attr)))
    
def set_attr(self, value, attr='', check=lambda x:None, handle=None):
    after_check = check(value)
    if not after_check:
        setattr(self,'_%s__%s'%(self.__class__.__name__,attr),value)
    elif handle:
        setattr(self,'_%s__%s'%(self.__class__.__name__,attr),handle(check))
    else:
        setattr(self,'_%s__%s'%(self.__class__.__name__,attr),after_check)
###################################################################
_TIME_FRAME = {item:n for n, item in
               enumerate(['W1','D1','H1','M30','M15','M10','M5','M1'])}
_TIME_FRAME_PERIOD ={'W1':604800,'D1':86400,'H1':3600,'M30':1800,'M15':900,'M10':600,'M5':300,'M1':60}

def check_time_frame(time_frame):
    if not time_frame in _TIME_FRAME.keys():
        raise(ValueError("不合法的time_frame值:%s"%time_frame))
    return True
    
def get_time_frame_bit(time_frame):
    check_time_frame(time_frame)
    return(1 << _TIME_FRAME[time_frame])    
###################################################################
def __replace_all(string, olds, new):
    for old in olds:
        string=string.replace(old,new)
    return(string)

__PATTERNS = {re.compile(r'\A'+__replace_all(format_,['%m','%d','%H','%M','%S'],r'\d{2}')
            .replace('%Y',r'\d{4}')+r'\Z'):format_ for format_ 
            in ['%Y-%m-%d','%Y-%m-%d %H:%M%:%S']}

def get_datetime(string):
    for pattern, format_ in __PATTERNS.items():
        if pattern.match(string):
            return(datetime.strptime(string, format_))
    raise(ValueError("不合法的时间格式"))
###################################################################
def quick_sort(l, r, arr, key):
    if l > r: return    
    i = l
    j = r
    mid = key(arr, (l+r)>>1)
    while i <= j:
        while key(arr, i) < mid and i <= r: i += 1
        while key(arr, j) > mid and j >= l: j -= 1
        if i <= j:
            temp = arr[i]
            arr[i] = arr[j]
            arr[j] = temp
            i += 1
            j -= 1
    if j > l: quick_sort(l,j,arr,key)
    if i < r: quick_sort(i,r,arr,key)
###################################################################
class DictLike():
    __slots__=[]
    def to_dict(self):
        cls = self.__class__.__name__
        return ({slot.replace('__',''):getattr(self,slot.replace('__','_%s__'%cls))
                for slot in self.__slots__})
    def __getitem__(self,key):
        return (getattr(self,key))
###################################################################
class HasID:
    """有自增长ID对象的通用方法"""
    __slots__=[]
    __AUTO_INC_NEXT = 0
    #XXX 是否把自增写入
    @classmethod 
    def next_auto_inc(cls):
        cls.__AUTO_INC_NEXT += 1
        return cls.__AUTO_INC_NEXT
    @classmethod
    def get_auto_inc(cls):
        return(cls.__AUTO_INC_NEXT)
    @classmethod
    def set_auto_inc(cls, num):
        cls.__AUTO_INC_NEXT = num
###################################################################
class Deque(deque):
    pass
    #让deque支持切片操作
        
###################################################################        
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
    def append(self,item):
        if not self.full:
            self.data.append(item)
            self.last += 1
            if self.last == self.max_length:
                self.full = True
                self.last = 0
        else:
            self.data[self.last] = item
            self.last = (self.last+1)%self.max_length
    def __getitem__(self, i): 
        if not self.full:
            return self.data[self.last-i-1]
        else:
            return self.data[(self.last-i-1+self.max_length)%self.max_length]
    def __setitem__(self, i, item): raise(TypeError("SeriesList is read-only"))
    def __delitem__(self, i): raise(TypeError("SeriesList is read-only"))