# -*- coding: utf-8 -*-

# 系统模块
import os
import ast
import inspect
from functools import partial
import codecs
from weakref import proxy
import logging

# 自定义模块
from Bigfish.utils.log import FilePrinter, LoggerInterface
from Bigfish.models.model import User
from Bigfish.store.directory import UserDirectory
from Bigfish.utils.export import export, SeriesFunction
from Bigfish.event.handle import SignalFactory
from Bigfish.utils.ast import LocalsInjector, SeriesExporter, SystemFunctionsDetector, ImportInspector, \
    InitTransformer, wrap_with_module, TradingCommandsTransformer
from Bigfish.utils.common import check_time_frame
from Bigfish.models.common import HasID
from Bigfish.models.trade import OrderDirection
from Bigfish.store.code_manage import get_sys_func_list


class Strategy(LoggerInterface, HasID):
    ATTR_MAP = dict(TimeFrame="time_frame", Base="capital_base", Symbols="symbols", StartTime="start_time",
                    EndTime="end_time", MaxLen="max_length")
    API_FUNCTION = ['Buy', 'Sell', 'SellShort', 'BuyToCover', 'Export'] + get_sys_func_list()
    API_VARIABLES = ['O', 'Open', 'Opens', 'H', 'High', 'Highs', 'L', 'Low', 'Lows', 'C', 'Close', 'Closes',
                     'Datetime', 'Datetimes', 'D', 'Timestamp', 'Timestamps', 'T', 'Volume', 'Volumes', 'V', 'Symbols',
                     'Symbol', 'BarNum', 'MarketPosition', 'Positions', 'Pos', 'CurrentContracts', 'Point']

    # ----------------------------------------------------------------------
    def __init__(self, engine, code, config):
        """Constructor"""
        super().__init__()
        self.__id = self.next_auto_inc()
        self.user = config.user
        self.user_dir = UserDirectory(User(config.user))
        self.name = config.name
        self.code = code
        self.engine = proxy(engine)
        self.time_frame = config.time_frame
        self.symbols = config.symbols
        self.start_time = config.start_time
        self.end_time = config.end_time
        self.capital_base = config.capital_base
        self.max_length = 0
        self.handlers = {}
        self.signal_factory = SignalFactory()
        self.signals = {}
        self.system_functions = {}
        self.series_storage = {}
        self.__printer = FilePrinter(config.user, config.name, self.engine)
        self.__context = {}
        self.__points = {}
        # 是否完成了初始化
        self.trading = False
        # 在字典中保存Open,High,Low,Close,Volumn，CurrentBar，MarketPosition，
        # 手动为exec语句提供globals命名空间
        self.__glb = {'Buy': partial(self.engine.place_order, strategy=self.__id, direction=OrderDirection.long_entry),
                      'Sell': partial(self.engine.place_order, strategy=self.__id,
                                      direction=OrderDirection.long_exit),
                      'SellShort': partial(self.engine.place_order, strategy=self.__id,
                                           direction=OrderDirection.short_entry),
                      'BuyToCover': partial(self.engine.place_order, strategy=self.__id,
                                            direction=OrderDirection.short_exit),
                      'Positions': self.engine.current_positions, 'Data': self.engine.data,
                      'Context': self.__context, 'Export': partial(export, strategy=self), 'Put': self.put_context,
                      'Get': self.get_context, 'print': self.__printer.print,
                      'Points': self.__points, 'Cap': self.engine.get_capital(),
                      'signals': self.signals, 'system_functions': self.system_functions}
        # 将策略容器与对应代码文件关联
        self.bind_code_to_strategy(self.code)

    # -----------------------------------------------------------------------
    @staticmethod
    def open(*args, **kwargs):
        raise RuntimeError('open函数已被禁用')

    # -----------------------------------------------------------------------
    def get_output(self):
        with open(self.__printer.get_path()) as f:
            content = f.read()
            f.close()
        return content

    # ----------------------------------------------------------------------
    def get_parameters(self):
        return {key: value.get_parameters() for key, value in self.signals.items()}

    # ----------------------------------------------------------------------
    def set_parameters(self, parameters):
        for handle, paras in parameters.items():
            self.signals[handle].set_parameters(**paras)

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
        self.series_storage.clear()

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
                    pass

        def upper_first_letter(string):
            return string[0].upper() + string[1:]

        # get the system functions in use
        ast_ = ast.parse(code)
        import_inspector = ImportInspector()
        import_inspector.visit(ast_)  # 模块导入检查
        signal_locals_ = {}
        function_locals = {}
        signal_globals_ = {'open': self.open}  # 可动态管理的全策略命名空间,禁用open
        function_globals_ = {'open': self.open}  # 可动态管理的系统函数命名空间,禁用open
        # 获取并检查一些全局变量的设定
        exec(compile(code, "[Strategy:%s]" % self.name, mode="exec"), signal_globals_, signal_locals_)
        # get_global_attrs(signal_locals_)  # 弃用，暂时保留以便向下兼容
        set_global_attrs(signal_globals_)
        set_global_attrs(function_globals_)
        signal_globals_.update(signal_locals_)
        signal_globals_.update(self.__glb)
        function_globals_.update(self.__glb)
        self.engine.start_time = self.start_time
        self.engine.end_time = self.end_time
        check_time_frame(self.time_frame)
        sys_func_detector = SystemFunctionsDetector()
        sys_func_detector.visit(ast_)
        sys_func_dir = self.user_dir.get_sys_func_dir()
        funcs_in_use = sys_func_detector.get_funcs_in_use()

        # get the instructions to inject to every handle
        signal_to_inject_init = {}
        function_to_inject_init = {}
        signal_to_inject_loop = {}
        function_to_inject_loop = {}
        code_lines = ["import functools", "__globals = globals()"]
        code_lines.extend(["{0} = __globals['{0}']".format(key) for key in self.__glb.keys()
                           if key not in ["Sell", "Buy", "SellShort", "BuyToCover"]])
        # init中可以设定全局变量，所以要以"global foo"的方式进行注入。
        if inspect.isfunction(signal_locals_.get('init', None)):
            init_transformer = InitTransformer()
            init_transformer.visit(ast_)
            # XXX 必须要一个module node作为根节点。
            exec(compile(wrap_with_module(init_transformer.init_node), "[Strategy:%s]" % self.name, mode="exec"),
                 signal_globals_, signal_locals_)
            self.handlers['init'] = signal_locals_['init']
            # 执行init并记录locals，之后注入信号
            init_globals = self.handlers['init']()
            signal_globals_.update(init_globals)
            init_to_inject_init = ["{0} = __globals['{0}']".format(key) for key in init_globals.keys()]
        else:
            init_to_inject_init = []

        for key, value in signal_locals_.items():
            if inspect.isfunction(value):
                if key == "init":
                    continue
                paras = inspect.signature(value).parameters.copy()  # 获取handler函数的参数列表
                is_handle = get_parameter_default(paras, "IsHandle", lambda x: isinstance(x, bool), True)
                if not is_handle:
                    continue
                custom = get_parameter_default(paras, "Custom", lambda x: isinstance(x, bool), False)
                if not custom:
                    # TODO加入真正的验证方法
                    # 转化为tuple是因为symbols要那来当做字典的键
                    symbols = tuple(get_parameter_default(paras, "Symbols", lambda x: True, self.symbols))
                    time_frame = get_parameter_default(paras, "TimeFrame", check_time_frame, self.time_frame)
                    max_length = get_parameter_default(paras, "MaxLen", lambda x: isinstance(x, int) and (x > 0),
                                                       self.max_length)
                    self.engine.add_cache_info(symbols, time_frame, max_length)
                    self.signals[key] = self.signal_factory.new(self.engine, self.user, self.name, key, symbols,
                                                                time_frame)
                    additional_instructions = ["{0} = system_functions['%s.%s'%('{1}','{0}')]".format(f, key)
                                               for f, s in funcs_in_use.items() if key in s] + ['del(system_functions)']
                    temp = []
                    # Begin open,high,low,close相关变量的注入
                    quotes = ["open", "high", "low", "close", "datetime", "timestamp", "volume"]
                    temp.extend(["{0} = __globals['Data']['{1}']['{3}']['{2}']"
                                .format(upper_first_letter(field), time_frame, symbols[0], field)
                                 for field in quotes])
                    temp.extend(["{0} = __globals['Data']['{1}']['{3}']['{2}']"
                                .format(field[0].upper(), time_frame, symbols[0], field)
                                 for field in quotes])
                    temp.extend(["{0}s = __globals['Data']['{1}']['{2}']"
                                .format(upper_first_letter(field), time_frame, field)
                                 for field in quotes])
                    # end
                    # get_current_bar 函数的注入，BarNum实际通过该函数维护
                    temp.append("{0} = __globals['signals']['{1}'].{0}".format('get_current_bar', key))
                    temp.append("Symbol = Symbols[0]")  # Symbol注入
                    temp.append("Point=Points[Symbol]")  # Points注入
                    function_to_inject_init[key] = code_lines + temp + ["del(functools)", "del(__globals)"] + \
                                                   additional_instructions
                    temp.extend(["{0} = functools.partial(__globals['{0}'],signal='{1}')".format(
                        field, key)
                                 for field in ["Sell", "Buy", "SellShort", "BuyToCover"]])
                    # TODO 现在是将init中的变量当做局部变量注入每个信号的初始化部分，其实这样并不等同于全局变量的概念，
                    # 只不过对于单个信号的策略是一样的。
                    signal_to_inject_init[key] = code_lines + temp + init_to_inject_init + \
                                                 ["del(functools)", "del(__globals)"] + additional_instructions
                    # 信号与函数中相比多出的就是交易指令
                    signal_to_inject_loop[key] = ["BarNum = get_current_bar()",
                                                  "Pos = Positions[Symbol]",
                                                  "MarketPosition = Pos.type",
                                                  "CurrentContracts= Pos.volume"]
                    function_to_inject_loop[key] = signal_to_inject_loop[key]
                else:
                    # TODO自定义事件处理
                    pass
                for para_name in paras.keys():
                    # TODO加入类型检测
                    default = get_parameter_default(paras, para_name, lambda x: True, None,
                                                    pop=False)
                    if default is None:
                        raise ValueError('参数%s未指定初始值' % para_name)
                    elif not isinstance(default, (int, float)):
                        raise ValueError('参数%s的值必须为整数或浮点数' % para_name)
                    self.signals[key].add_parameters(para_name, default)
        self.__points.update({key: value.point for key, value in self.engine.symbol_pool.items()})
        series_exporter = SeriesExporter()  # deal with the export syntax
        # export the system functions in use
        for func, signals in funcs_in_use.items():
            for signal in signals:
                fullname = os.path.join(sys_func_dir, func + ".py")
                with codecs.open(fullname, "r", "utf-8") as f:
                    func_ast = ast.parse(f.read())
                    f.close()
                import_inspector.visit(func_ast)  # 检查模块导入
                function_injector = LocalsInjector({func: function_to_inject_init[signal]},
                                                   {func: function_to_inject_loop[signal]})
                function_injector.visit(func_ast)
                func_ast = series_exporter.visit(func_ast)
                # TODO 多个handle时需要对每个handle调用的系统函数建立独立的系统函数
                exec(compile(func_ast, "[SysFunctions:%s]" % func, mode="exec"), function_globals_, function_locals)
                self.system_functions['%s.%s' % (signal, func)] = SeriesFunction(function_locals[func], signal)
                # new方法是对__init__的封装，创建SeriesFunction对象所需信息有其所在的函数体本身，signal和其运行时传入的参数，
                # 编译时所能确定的只有前者，采用偏函数的方式将两者结合到一起
        # inject global vars into locals of handler
        signal_injector = LocalsInjector(signal_to_inject_init, signal_to_inject_loop)
        signal_injector.visit(ast_)
        ast_ = series_exporter.visit(ast_)
        ast_ = TradingCommandsTransformer().visit(ast_)  # 给买卖语句表上行列号
        exec(compile(ast_, "[Strategy:%s]" % self.name, mode="exec"), signal_globals_, signal_locals_)
        for key in signal_to_inject_init.keys():
            self.signals[key].set_generator(signal_locals_[key])
        self.logger.info("<%s>策略添加成功" % self.name)
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
        for listener in self.signals.values():
            listener.start()
        for function in self.system_functions.values():
            function.start()
        self.__printer.start()
        self.logger.info("<%s>策略开始运行" % self.name)

    # ----------------------------------------------------------------------
    def stop(self):
        """
        停止交易
        同上
        """
        self.trading = False
        for listener in self.signals.values():
            listener.stop()
        for function in self.system_functions.values():
            function.stop()
        self.__printer.stop()
        self.logger.info("<%s>策略停止运行" % self.name)
