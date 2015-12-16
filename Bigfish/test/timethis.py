# -*- coding: utf-8 -*-
import time
from functools import wraps

def timethis(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        start = time.time()
        r = func(*args,**kwargs)
        end = time.time()
        print(end - start)
        return r
    return wrapper


