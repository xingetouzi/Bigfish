# -*- coding: utf-8 -*-

# 系统模块
from queue import Queue, Empty
from functools import wraps, partial
from threading import Thread
import sys

# 自定义模块
from Bigfish.event.event import EVENT_TIMER, EVENT_ASYNC, Event
from Bigfish.utils.error import SlaverThreadError


########################################################################
class EventEngine:
    """
    事件驱动引擎

    事件驱动引擎中所有的变量都设置为了私有，这是为了防止不小心
    从外部修改了这些变量的值或状态，导致bug。
    
    变量说明
    __queue：私有变量，事件队列
    __active：私有变量，事件引擎开关
    __thread：私有变量，事件处理线程
    __timer：私有变量，计时器
    __handlers：私有变量，事件处理函数字典

    
    方法说明
    __run: 私有方法，事件处理线程连续运行用
    __process: 私有方法，处理事件，调用注册在引擎中的监听函数
    __onTimer：私有方法，计时器固定事件间隔触发后，向事件队列中存入计时器事件
    start: 公共方法，启动引擎
    stop：公共方法，停止引擎
    register：公共方法，向引擎中注册监听函数
    unregister：公共方法，向引擎中注销监听函数
    put：公共方法，向事件队列中存入新的事件
    
    事件监听函数必须定义为输入参数仅为一个event对象，即：
    
    函数
    def func(event)
        ...
    
    对象方法
    def method(self, event)
        ...
        
    """

    # ----------------------------------------------------------------------
    def __init__(self):
        """初始化事件引擎"""
        # 事件队列
        self.__queue = Queue()
        self.__file_opened = []
        # 事件引擎开关
        self.__active = False
        self.__finished = False
        self.__thread = None
        self.__exc_type = None
        self.__exc_value = None
        self.__exc_traceback = None
        # 计时器，用于触发计时器事件
        # self.__timer = QTimer()
        # self.__timer.timeout.connect(self.__onTimer)

        # 这里的__handlers是一个字典，用来保存对应的事件调用关系
        # 其中每个键对应的值是一个列表，列表中保存了对该事件进行监听的函数功能
        self.__handlers = {}
        # 注册异步事件
        self.register(EVENT_ASYNC, lambda event: event.content['func']())

    # ----------------------------------------------------------------------
    def __run(self):
        """引擎运行"""
        while self.__active == True:
            try:
                event = self.__queue.get(block=True, timeout=0.5)  # 获取事件的阻塞时间设为0.5秒
                self.__process(event)
            except Empty:
                if self.__finished:
                    self.__active = False
            except Exception:
                self.__exc_type, self.__exc_value, self.__exc_traceback = sys.exc_info()
                self.__active = False
        for file in self.__file_opened:
            if not file.closed:
                file.close()

    # ----------------------------------------------------------------------
    def __process(self, event):
        """处理事件"""
        # 检查是否存在对该事件进行监听的处理函数
        if event.type_ in self.__handlers:
            # 若存在，则按顺序将事件传递给处理函数执行
            for handler in self.__handlers[event.type_]:
                handler(event)

    # ----------------------------------------------------------------------
    def __onTimer(self):
        """向事件队列中存入计时器事件"""
        # 创建计时器事件
        event = Event(type_=EVENT_TIMER)

        # 向队列中存入计时器事件
        self.put(event)

        # ----------------------------------------------------------------------

    def start(self):
        """引擎启动"""
        # 将引擎设为启动
        self.__active = True
        self.__finished = False
        # 启动事件处理线程
        self.__thread = Thread(target=self.__run)
        self.__thread.start()
        # 启动计时器，计时器事件间隔默认设定为1秒
        # self.__timer.start(1000)

    # ----------------------------------------------------------------------
    def stop(self):
        """停止引擎"""
        # 将引擎设为停止
        if self.__active == True:
            self.__active = False
            self.__thread.join()  # 等待事件处理线程退出
        if self.__thread:
            self.__thread = None

    # -----------------------------------------------------------------------
    def wait(self):
        """等待队列中所有事件被处理完成"""
        if self.__active == True:
            self.__finished = True
            self.__thread.join()
            self.throw_error()
            self.stop()
        else:
            self.throw_error()

    # ----------------------------------------------------------------------
    def register(self, type_, handler):
        """注册事件处理函数监听"""
        # 尝试获取该事件类型对应的处理函数列表，若无则创建
        try:
            handlerList = self.__handlers[type_]
        except KeyError:
            handlerList = []
            self.__handlers[type_] = handlerList
        # 监听函数的优先级通过注册先后来实现
        # 若要注册的处理器不在该事件的处理器列表中，则注册该事件
        if handler not in handlerList:
            handlerList.append(handler)

    # ----------------------------------------------------------------------
    def unregister(self, type_, handler):
        """注销事件处理函数监听"""
        # 尝试获取该事件类型对应的处理函数列表，若无则忽略该次注销请求
        try:
            handlerList = self.__handlers[type_]

            # 如果该函数存在于列表中，则移除
            if handler in handlerList:
                handlerList.remove(handler)

            # 如果函数列表为空，则从引擎中移除该事件类型
            if not handlerList:
                del self.__handlers[type_]
        except KeyError:
            pass

    # ----------------------------------------------------------------------
    def add_file(self, file):
        if file not in self.__file_opened:
            self.__file_opened.append(file)

    # ----------------------------------------------------------------------
    def put(self, event):
        """向事件队列中存入事件"""
        self.__queue.put(event)

    # ----------------------------------------------------------------------
    def throw_error(self):
        if self.__exc_type:
            raise (SlaverThreadError(self.__exc_type, self.__exc_value, self.__exc_traceback))


########################################################################
def async_handle(engine, callback):
    def wrap_func(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            def target(*args, **kwargs):
                result = func(*args, **kwargs)
                event = Event(EVENT_ASYNC, {'func': partial(callback, *result[0], **result[1])})
                engine.put(event)

            thread = Thread(target=target, args=args, kwargs=kwargs)
            thread.start()

        return wrapper

    return wrap_func
