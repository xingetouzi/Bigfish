# -*- coding: utf-8 -*-
from operator import itemgetter

from Bigfish.models.common import HasID
from Bigfish.models import Symbol
from Bigfish.utils.common import _TIME_FRAME
from Bigfish.store.symbol_manage import get_all_symbols

'''
本文件仅用于存放对于事件类型常量的定义。

由于python中不存在真正的常量概念，因此选择使用全大写的变量名来代替常量。
这里设计的命名规则以EVENT_前缀开头。

常量的内容通常选择一个能够代表真实意义的字符串（便于理解）。

建议将所有的常量定义放在该文件中，便于检查是否存在重复的现象。
'''


########################################################################
class _EventType(HasID):
    __slots__ = ["__id", "name", "verbose_name"]  # 事件类型的ID,名称，含义解释

    def __init__(self, name, verbose_name=''):
        self.__id = self.next_auto_inc()
        self.name = name
        self.verbose_name = verbose_name

    def get_id(self):
        return self.__id


########################################################################
class Event:
    """事件对象"""
    __types = {}

    @classmethod
    def _create_event_type(cls, name):
        # TODO check name
        if name in [type_.name for type_ in cls.__types.values()]:
            # TODO 自定义错误
            raise (ValueError("重复的事件定义"))
        else:
            event_type = _EventType(name)
            cls.__types[event_type.get_id()] = event_type
            return (event_type)

    # ----------------------------------------------------------------------
    def __init__(self, type_=None, content={}):
        """Constructor"""
        self.type_ = type_  # 事件类型
        self.content = content  # 保存具体的事件数据


EVENT_ASYNC = Event._create_event_type('Async').get_id()  # 用于实现异步
EVENT_TIMER = Event._create_event_type('Timer').get_id()  # 计时器事件，每隔1秒发送一次
EVENT_LOG = Event._create_event_type('Log').get_id()  # 日志事件，通常使用某个监听函数直接显示
EVENT_TDLOGIN = Event._create_event_type('TdLogin').get_id()  # 交易服务器登录成功事件
EVENT_TICK = Event._create_event_type('Tick').get_id()  # 行情推送事件
SYMBOLS = list(map(lambda x: x.en_name, get_all_symbols()))
EVENT_BAR = Event._create_event_type('Bar').get_id()  # 特定交易物的数据事件
EVENT_BAR_SYMBOL = {symbol: {time_frame: Event._create_event_type('Deal.%s.%s' %
                                                                  (symbol, time_frame)).get_id() for time_frame in
                             _TIME_FRAME} for symbol in SYMBOLS}
EVENT_DEAL = 'Deal'  # 成交推送事件
EVENT_DEAL_SYMBOL = {symbol: Event._create_event_type('Deal.%s' % symbol).get_id()
                     for symbol in SYMBOLS}  # 特定交易物的成交事件
EVENT_ORDER = 'Order'  # 报单推送事件
EVENT_ORDER_SYMBOL = {symbol: Event._create_event_type('Order.%s' % symbol).get_id()
                      for symbol in SYMBOLS}  # 特定报单号的报单事件
EVENT_POSITION = 'Position'  # 持仓查询回报事件
EVENT_POSITION_SYMBOL = {symbol: Event._create_event_type('Position.%s' % symbol).get_id()
                         for symbol in SYMBOLS}  # 特定交易物持仓查询回报事件
