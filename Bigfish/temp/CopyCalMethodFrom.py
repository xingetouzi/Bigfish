# -*- coding: utf-8 -*-
from functools import wraps
import time

def timethis(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        start = time.time()
        func(*args,**kwargs)
        end = time.time()
        return end - start
    return wrapper

    
#语法糖，参数为某个可以运算的对象的列表，将其最后一个元素的运算函数全部装饰于所作用的
#对象上,使得直接通过碧对象名得到相当于是时间序列中最后一个元素（MC的语法）
def SeriesFromList(list_):        
    def wrapper(cls):
        class wrapperClass():
            _list = list_            
            def __init__(self,cls):
                wraps(cls)(self)            
            def __iter__(cls):
                return (cls._list.__revered__)
            def __getitem__(cls,index):
                return cls._list[-(index+1)]
            def __call__(cls):
                return cls._list[-1]
        return wrapperClass(cls)
    return(wrapper)

def SeriesFuncFromList(list_):
    def namewrapper(f):
        _list = list_        
        @wraps(f)    
        def wrapper(index):
            return(_list[-(index+1)])
        return(wrapper)
    return(namewrapper)
        

#语法糖，将传入对象的运算函数全部装饰于所作用的对象上        
def CopyCalMethodFrom(obj):

#-----------------------------------------------------------------------
#将对象的运算函数进行封装    
    def add_(self, other):
        return(obj.__add__(other))
    
    def sub_(self, other):
        return(obj.__sub__(other))
    
    def mul_(self, other):
        return(obj.__mul__(other))
    
    def floordiv_(self, other):
        return(obj.__floordiv__(other))
        
    def mod_(self, other):
        return(obj.__mod__(other))
    
    def divmod_(self, other):
        return(obj.__divmod__(other))
        
    def pow_(self, other):
        return(obj.__pow__(other))
    
    def lshift_(self,other):
        return(obj.__lshift__(other))
        
    def rshift_(self, other):
        return(obj.__rshift__(other))
    
    def and_(self, other):
        return(obj.__and__(other))
        
    def xor_(self, other):
        return(obj.__xor__(other))
    
    def or_(self, other):
        return(obj.__or__(other))
        
#-----------------------------------------------------------------------        
    def wrapperObject(cls):
        #wraps(obj)(cls)        
        cls.__add__ = add_
        cls.__sub__ = sub_
        cls.__mul__ = mul_
        cls.__floordiv__ = floordiv_
        cls.__mod__ = mod_
        cls.__divmod__ = divmod_
        cls.__pow__ = pow_
        cls.__lshift__ = lshift_
        cls.__rshift__ = rshift_
        cls.__and__ = and_
        cls.__xor__ = xor_
        cls.__or__ = or_
        return cls()                 
    return wrapperObject

if __name__ == '__main__':
    a = [1,2,3,4,5]
    n = 10000000
    @SeriesFromList(a)
    class x():
        pass
    @SeriesFuncFromList(a)
    def y():
        pass
    @timethis
    def f1(n):
        print(x[0])        
        while n > 0:
            x[0]
            n -= 1
    @timethis
    def f2(n):
        print(y(0))
        while n > 0:
            y(0)
            n -= 1
    @timethis
    def f3(n):
        print(a[-1])
        while n > 0:
            a[-1]
            n -= 1
    @timethis
    def f4(n):
        while n > 0:
            n -= 1
    t1 = f1(n)
    t2 = f2(n)
    t3 = f3(n)
    t4 = f4(n)
    print(t1-t4)
    print(t2-t4)
    print(t3-t4)