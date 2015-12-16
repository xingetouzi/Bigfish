# -*- coding: utf-8 -*-
"""
Created on Tue Dec 15 11:37:18 2015

@author: BurdenBear
"""

class SlaverThreadError(RuntimeError):
    """子线程中出现的错误，保留子线程的堆栈信息"""
    def __init__(self, exc_type, exc_value, exc_traceback):
        super().__init__(exc_type, exc_value, exc_traceback)
        self.exc_type = exc_type
        self.exc_value = exc_value
        self.exc_traceback = exc_traceback
        
    def get_exc(self):
        return(self.exc_type, self.exc_value, self.exc_traceback)