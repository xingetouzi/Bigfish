# -*- coding: utf-8 -*-

# 系统模块
import ast
import inspect
from functools import partial

# 自定义模块
from Bigfish.utils.log import FilePrinter
from Bigfish.utils.export import export
from Bigfish.event.handle import SymbolsListener
from Bigfish.utils.ast import LocalsInjector, SeriesExporter
from Bigfish.utils.common import check_time_frame
from Bigfish.models.common import HasID


########################################################################
class Strategy(HasID):
    ATTR_MAP = dict(timeframe="time_frame", base="capital_base", symbols="symbols", start="start_time", end="end_time",
                    maxlen="max_length")

    # ----------------------------------------------------------------------
    def __init__(self, engine, user, name, code, symbols=None, time_frame=None, start_time=None, end_time=None):
        """Constructor"""
        self.__id = self.next_auto_inc()
        self.user = user
        self.name = name
        self.engine = engine
        self.time_frame = time_frame
        self.symbols = symbols
        self.start_time = start_time
        self.end_time = end_time
        self.max_length = 0
        self.capital_base = 100000
        self.handlers = {}
        self.listeners = {}
        self.series_storage = {}
        self.__printer = FilePrinter(user, name)
        self.__context = {}
        # 是否完成了初始化
        self.trading = False
        # 在字典中保存Open,High,Low,Close,Volumn，CurrentBar，MarketPosition，
        # 手动为exec语句提供local命名空间
        self.__locals_ = dict(sell=partial(self.engine.sell, strategy=self.__id),
                              short=partial(self.engine.short, strategy=self.__id),
                              buy=partial(self.engine.buy, strategy=self.__id),
                              cover=partial(self.engine.cover, strategy=self.__id),
                              marketposition=self.engine.get_current_positions(),
                              currentcontracts=self.engine.get_current_contracts(), data=self.engine.get_data(),
                              context=self.__context, export=partial(export, self),
                              put=self.put_context, get=self.get_context,
                              )
        # 将策略容器与对应代码文件关联
        self.bind_code_to_strategy(code)

    # ----------------------------------------------------------------------
    def get_parameters(self):
        return {key: value.get_parameters() for key, value in self.listeners.items()}

    # ----------------------------------------------------------------------
    def get_id(self):
        return self.__id

    # ----------------------------------------------------------------------
    def put_context(self, **kwargs):
        for key, value in kwargs.items():
            self.__context[key] = value

    # ----------------------------------------------------------------------
    def get_context(self, key):
        return self.__context[key]

    # ----------------------------------------------------------------------
    def initialize(self):
        self.__context.clear()

    # ----------------------------------------------------------------------
    # 将策略容器与策略代码关联
    def bind_code_to_strategy(self, code):
        def get_parameter_default(paras, name, check, default, pop=True):
            if pop:
                para = paras.pop(name, None)
            else:
                para = paras.get(name, None)
            if para:
                temp = para.default
                if temp == inspect._empty:
                    # TODO未给定值的处理
                    return default
                elif check(temp):
                    return temp
                else:
                    raise KeyError("变量%s所赋值不合法", name)
            else:
                return default

        def get_global_attrs(locals_):
            for name, attr in self.ATTR_MAP.items():
                if getattr(self, attr) is None:
                    setattr(self, attr, locals_.get(name))

        def set_global_attrs(globals_):
            for name, attr in self.ATTR_MAP.items():
                value = getattr(self, attr)
                if value is not None:
                    globals_[name] = value
                else:
                    raise ValueError('全局变量%s未被赋值' % name)

        locals_ = {}
        globals_ = {}
        exec(compile(code, "[Strategy:%s]" % self.name, mode="exec"), globals_, locals_)
        get_global_attrs(locals_)
        set_global_attrs(globals_)
        self.engine.set_capital_base(self.capital_base)
        globals_.update(self.__locals_)
        self.engine.start_time = self.start_time
        self.engine.end_time = self.end_time
        check_time_frame(self.time_frame)
        to_inject = {}
        code_lines = ["import functools", "__globals = globals()"]
        code_lines.extend(["%s = __globals['%s']" % (key, key) for key in self.__locals_.keys()
                           if key not in ["sell", "buy", "short", "cover"]])
        for key, value in locals_.items():
            if inspect.isfunction(value):
                if key == "init":
                    self.handlers['init'] = value
                    # TODO init中可以设定全局变量，所以要以"global foo"的方式进行注入，监听的事件不同所以要改写SymbolsListener
                    continue
                paras = inspect.signature(value).parameters.copy()
                ishandle = get_parameter_default(paras, "ishandle", lambda x: isinstance(x, bool), True)
                if not ishandle:
                    continue
                custom = get_parameter_default(paras, "custom", lambda x: isinstance(x, bool), False)
                if not custom:
                    # TODO加入真正的验证方法
                    symbols = get_parameter_default(paras, "symbols", lambda x: True, self.symbols)
                    time_frame = get_parameter_default(paras, "timeframe", check_time_frame, self.time_frame)
                    max_length = get_parameter_default(paras, "maxlen", lambda x: isinstance(x, int) and (x > 0),
                                                       self.max_length)
                    self.engine.add_symbols(symbols, time_frame, max_length)
                    self.listeners[key] = SymbolsListener(self.engine, symbols, time_frame)
                    temp = []
                    print(symbols)
                    temp.extend(["%s = __globals['data']['%s']['%s']['%s']" % (field, symbols[0], time_frame, field)
                                 for field in ["open", "high", "low", "close", "time", "volume"]])
                    temp.extend(["%s = functools.partial(__globals['%s'],listener=%d)" % (
                        field, field, self.listeners[key].get_id())
                                 for field in ["buy", "short", "sell", "cover"]])
                    to_inject[key] = code_lines + temp + ["del(functools)", "del(__globals)"]
                else:
                    # TODO自定义事件处理
                    pass
                for para_name in paras.keys():
                    # TODO加入类型检测
                    default = get_parameter_default(paras, para_name, lambda x: isinstance(x, (int, float)), None,
                                                    pop=False)
                    if default is None:
                        raise ValueError('参数%s未指定初始值')
                    self.listeners[key].add_parameters(para_name, default)
        injector = LocalsInjector(to_inject)
        ast_ = ast.parse(code)
        injector.visit(ast_)
        ast_ = SeriesExporter().visit(ast_)
        # TODO 解决行号的问题
        exec(compile(ast_, "[Strategy:%s]" % self.name, mode="exec"), globals_, locals_)
        for key in to_inject.keys():
            self.listeners[key].set_generator(locals_[key])
        print("<%s>信号添加成功" % self.name)
        if 'init' in self.handlers:
            self.handlers['init']()
        return True

    # ----------------------------------------------------------------------
    def start(self):
        """
        启动交易
        这里是最简单的改变self.trading
        有需要可以重新实现更复杂的操作
        """
        self.trading = True
        self.initialize()
        for listener in self.listeners.values():
            listener.start()
        self.__printer.start()
        self.__locals_['print'] = self.__printer.get_print()
        self.engine.writeLog(self.name + u'开始运行')

    # ----------------------------------------------------------------------
    def stop(self):
        """
        停止交易
        同上
        """
        self.trading = False
        for listener in self.listeners.values():
            listener.stop()
        self.__printer.stop()
        self.engine.writeLog(self.name + u'停止运行')
