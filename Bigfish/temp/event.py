# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 20:12:03 2015

@author: morrison
"""

from Queue import Queue , Empty
from threading import Thread

class EventEngine:
    def __init__(self)
        self.__queue = Queue()
        self.__active = False
        self.__thread = Threading(target = self.__run)
        #self.__timer = QTimer()
        #self.__timer.timeout.connect(self.__onTimer)
        self.__handlers = {}
    
    def __run(self):
        while self.__active == True:
            try:
                event = self.__queue.get(block = True,timeout = 1)
                self.__process(event)
            except Empty:
                pass
    
    def __process(self, event):
        if event.type_ in self.___handlers:
            [handler(event) for handler in self.__handlers[event.type_]]
    
    def __onTimer(self,event):
        event = Event(type_=EVENT_TIMER)
        self.put(event)
        
    def start(self):
        self.__active = True
        self.__thread.start()
        self.__timer.start(1000)
        
    def stop(self):
        self.__active = False
        self.__timer.stop()
        self.__thread.join()
        
    def stop(self)
        try:
            handlerList = self.__handlers[type_]
        except KeyError:
            handlerList = []
            self.__handlers[type_] = handlerList
        if handler not in handlerList:
            handlerList.append(handler)
    
    def unregister(self,type_,handler):
        # try:
            handlerList = self.handlers[type_]
            if handler in handerList:
                handlerList.remove(handler)
            if not handlerList:
                del self.handlers[type_]
        except KeyError:
            pass
    
    def put(self,event):
        self.__queue.put(event)
    