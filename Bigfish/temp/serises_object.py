# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 13:57:24 2015

@author: morrison
"""

from functools import wraps

def dict_eq(dict1,dict2):
    if (dict1==None):
        return False
    for (k,v1) in dict1:
        v2 = dict2.pop(k,None)
        if (v2==None) or (v1!=v2):
            return False
    return True

class SeriesObject(object):    
    def __init__(self,func)    
        wraps(func)(self)    
        self.__para_dict = {}
        self.__partialfunc_dict = {}
        self.__dict_count = 0
        
    def __call__(self,**kwargs)
        for k,v in self.__paradict
            if dict_eq(kkargs,v):
                
            
    def __getitem__(self,index):
        pass