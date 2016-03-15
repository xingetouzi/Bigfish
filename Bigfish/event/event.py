# -*- coding: utf-8 -*-
from Bigfish.models.common import HasID
from Bigfish.store.symbol_manage import get_all_symbols
from Bigfish.utils.common import _TIME_FRAME

'''
本文件仅用于存放对于事件类型常量的定义。

由于python中不存在真正的常量概念，因此选择使用全大写的变量名来代替常量。
这里设计的命名规则以EVENT_前缀开头。

常量的内容通常选择一个能够代表真实意义的字符串（便于理解）。

建议将所有的常量定义放在该文件中，便于检查是否存在重复的现象。
'''


########################################################################
class _EventType(HasID):
    __slots__ = ["__id", "name", "verbose_name", "priority"]  # 事件类型的ID,名称，含义解释

    def __init__(self, name, verbose_name='', priority=0):
        self.__id = self.next_auto_inc()
        self.name = name
        self.verbose_name = verbose_name
        self.priority = priority  # 事件优先级，优先级高的先执行

    def get_id(self):
        return self.__id


########################################################################
class Event:
    """事件对象"""
    __types = {}

    @classmethod
    def create_event_type(cls, name, priority=0):
        # TODO check name
        if name in [type_.name for type_ in cls.__types.values()]:
            # TODO 自定义错误
            raise (ValueError("重复的事件<%s>定义" % name))
        else:
            event_type = _EventType(name, priority=priority)
            cls.__types[event_type.get_id()] = event_type
            return event_type

    # ----------------------------------------------------------------------
    def __init__(self, type=None, **content):
        """Constructor"""
        self.type = type  # 事件类型
        self.priority = self.__types[type].priority  # 事件的优先级
        self.content = content  # 保存具体的事件数据


EVENT_ASYNC = Event.create_event_type('Async').get_id()  # 用于实现异步
EVENT_TIMER = Event.create_event_type('Timer').get_id()  # 计时器事件，每隔1秒发送一次
EVENT_LOG = Event.create_event_type('Log').get_id()  # 日志事件，通常使用某个监听函数直接显示
EVENT_TDLOGIN = Event.create_event_type('TdLogin').get_id()  # 交易服务器登录成功事件
EVENT_TICK = Event.create_event_type('Tick').get_id()  # 行情推送事件
SYMBOLS = list(map(lambda x: x.en_name, get_all_symbols()))
EVENT_BAR = Event.create_event_type('Bar').get_id()  # 特定交易物的数据事件
# 特定品种原始数据更新事件,content:{'data': bar}为行情数据对象。
EVENT_SYMBOL_BAR_RAW = {
    symbol: {time_frame: Event.create_event_type('BarRaw.%s.%s' % (symbol, time_frame)).get_id() for time_frame in
             _TIME_FRAME} for symbol in SYMBOLS}
# 特定品种数据更新事件,这个事件看似与之前的数据重合，但是通过数据中继站，可以对BarUpdate事件产生的频率进行控制,content:{'data':bar,'completed':True or False}
EVENT_SYMBOL_BAR_UPDATE = {
    symbol: {time_frame: Event.create_event_type('BarUpdate.%s.%s' % (symbol, time_frame), priority=1).get_id() for
             time_frame in _TIME_FRAME} for symbol in SYMBOLS}
# 特定品种上一根K线完结事件，这个事件主要用来实现在下一个Bar的open时进行对上一根Bar的所有下单进行处理。
EVENT_SYMBOL_BAR_COMPLETED = {
    symbol: {time_frame: Event.create_event_type('BarCompleted.%s.%s' % (symbol, time_frame), priority=2).get_id() for
             time_frame in _TIME_FRAME} for symbol in SYMBOLS}
EVENT_DEAL = 'Deal'  # 成交推送事件
EVENT_DEAL_SYMBOL = {symbol: Event.create_event_type('Deal.%s' % symbol).get_id()
                     for symbol in SYMBOLS}  # 特定交易物的成交事件
EVENT_ORDER = 'Order'  # 报单推送事件
EVENT_ORDER_SYMBOL = {symbol: Event.create_event_type('Order.%s' % symbol).get_id()
                      for symbol in SYMBOLS}  # 特定报单号的报单事件
EVENT_POSITION = 'Position'  # 持仓查询回报事件
EVENT_POSITION_SYMBOL = {symbol: Event.create_event_type('Position.%s' % symbol).get_id()
                         for symbol in SYMBOLS}  # 特定交易物持仓查询回报事件
