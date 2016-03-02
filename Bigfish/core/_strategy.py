# -*- coding: utf-8 -*-

# 系统模块
import os
import ast
import inspect
from functools import partial
import codecs

# 自定义模块
from Bigfish.utils.log import FilePrinter
from Bigfish.store.directory import UserDirectory
from Bigfish.utils.export import export, SeriesFunction
from Bigfish.event.handle import SymbolsListener
from Bigfish.utils.ast import LocalsInjector, SeriesExporter, SystemFunctionsDetector, ImportInspector, InitTransformer
from Bigfish.utils.common import check_time_frame
from Bigfish.models.common import HasID


########################################################################
def set_parameters(paras):
    pass


class Strategy(HasID):
    ATTR_MAP = dict(TimeFrame="time_frame", Base="capital_base", Symbols="symbols", StartTime="start_time",
                    EndTime="end_time", MaxLen="max_length")
    API_FUNCTION = ['Buy', 'Sell', 'SellShort', 'BuyToCover', 'Export']
    API_VARIABLES = ['O', 'Open', 'Opens', 'H', 'High', 'Highs', 'L', 'Low', 'Lows', 'C', 'Close', 'Closes',
                     'Time', 'Times', 'T', 'Volume', 'Volumes', 'V', 'Symbols', 'Symbol', 'BarNum', 'MarketPosition',
                     'Positions', 'Pos', 'CurrentContracts']

    # ----------------------------------------------------------------------
    def __init__(self, engine, user, name, code, symbols=None, time_frame=None, start_time=None, end_time=None):
        """Constructor"""
        self.__id = self.next_auto_inc()
        self.user = user
        self.user_dir = UserDirectory(user)
        self.name = name
        self.code = code
        self.engine = engine
        self.time_frame = time_frame
        self.symbols = symbols
        self.start_time = start_time
        self.end_time = end_time
        self.max_length = 0
        self.capital_base = 100000
        self.handlers = {}
        self.listeners = {}
        self.system_functions = {}
        self.series_storage = {}
        self.__printer = FilePrinter(user, name, self.engine)
        self.__context = {}
        # 是否完成了初始化
        self.trading = False
        # 在字典中保存Open,High,Low,Close,Volumn，CurrentBar，MarketPosition，
        # 手动为exec语句提供local命名空间
        self.__locals_ = dict(Buy=partial(self.engine.open_position, strategy=self.__id, direction=1),
                              Sell=partial(self.engine.close_position, strategy=self.__id, direction=1),
                              SellShort=partial(self.engine.open_position, strategy=self.__id, direction=-1),
                              BuyToCover=partial(self.engine.close_position, strategy=self.__id, direction=-1),
                              Positions=self.engine.get_current_positions(),
                              CurrentContracts=self.engine.get_current_contracts(), Data=self.engine.get_data(),
                              Context=self.__context, Export=partial(export, strategy=self),
                              Put=self.put_context, Get=self.get_context, print=self.__printer.print,
                              listeners=self.listeners, system_functions=self.system_functions,
                              )
        # 将策略容器与对应代码文件关联
        self.bind_code_to_strategy(self.code)

    # -----------------------------------------------------------------------
    def get_output(self):
        with open(self.__printer.get_path()) as f:
            content = f.read()
            f.close()
        return content

    # ----------------------------------------------------------------------
    def get_parameters(self):
        return {key: value.get_parameters() for key, value in self.listeners.items()}

    # ----------------------------------------------------------------------
    def set_parameters(self, parameters):
        for handle, paras in parameters.items():
            self.listeners[handle].set_parameters(**paras)

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
                    raise ValueError('全局变量%s未被赋值' % name)

        def upper_first_letter(string):
            return string[0].upper() + string[1:]

        # get the system functions in use
        ast_ = ast.parse(code)
        import_inspector = ImportInspector()
        import_inspector.visit(ast_)  # 模块导入检查
        signal_locals_ = {}
        function_locals = {}
        signal_globals_ = {}  # 可动态管理的全策略命名空间
        function_globals_ = {}  # 可动态管理的系统函数命名空间
        # 获取并检查一些全局变量的设定
        exec(compile(code, "[Strategy:%s]" % self.name, mode="exec"), signal_globals_, signal_locals_)
        get_global_attrs(signal_locals_)
        set_global_attrs(signal_globals_)
        set_global_attrs(function_globals_)
        signal_globals_.update(signal_locals_)
        signal_globals_.update(self.__locals_)
        function_globals_.update(self.__locals_)
        self.engine.set_capital_base(self.capital_base)
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
        code_lines.extend(["{0} = __globals['{0}']".format(key) for key in self.__locals_.keys()
                           if key not in ["Sell", "Buy", "SellShort", "BuyToCover"]])
        for key, value in signal_locals_.items():
            if inspect.isfunction(value):
                if key == "init":
                    self.handlers['init'] = value
                    # TODO init中可以设定全局变量，所以要以"global foo"的方式进行注入，监听的事件不同所以要改写SymbolsListener
                    continue
                paras = inspect.signature(value).parameters.copy()  # 获取handler函数的参数列表
                is_handle = get_parameter_default(paras, "IsHandle", lambda x: isinstance(x, bool), True)
                if not is_handle:
                    continue
                custom = get_parameter_default(paras, "Custom", lambda x: isinstance(x, bool), False)
                if not custom:
                    # TODO加入真正的验证方法
                    symbols = get_parameter_default(paras, "Symbols", lambda x: True, self.symbols)
                    time_frame = get_parameter_default(paras, "TimeFrame", check_time_frame, self.time_frame)
                    max_length = get_parameter_default(paras, "MaxLen", lambda x: isinstance(x, int) and (x > 0),
                                                       self.max_length)
                    self.engine.add_symbols(symbols, time_frame, max_length)
                    self.listeners[key] = SymbolsListener(self.engine, symbols, time_frame)

                    additional_instructions = ["{0} = system_functions['%s.%s'%('{1}','{0}')]".format(f, key)
                                               for f, s in funcs_in_use.items() if key in s] + ['del(system_functions)']
                    temp = []
                    # TODO 加入opens等，这里字典的嵌套结构
                    temp.extend(["{0} = __globals['Data']['{1}']['{3}']['{2}']"
                                .format(upper_first_letter(field), time_frame, symbols[0], field)
                                 for field in ["open", "high", "low", "close", "time", "volume"]])
                    temp.extend(["{0} = __globals['Data']['{1}']['{3}']['{2}']"
                                .format(field[0].upper(), time_frame, symbols[0], field)
                                 for field in ["open", "high", "low", "close", "time", "volume"]])
                    temp.extend(["{0}s = __globals['Data']['{1}']['{2}']"
                                .format(upper_first_letter(field), time_frame, field)
                                 for field in ["open", "high", "low", "close", "time", "volume"]])
                    temp.append("{0} = __globals['listeners']['{1}'].{0}".format('get_current_bar', key))
                    temp.append("Symbol = Symbols[0]")
                    function_to_inject_init[key] = code_lines + temp + ["del(functools)", "del(__globals)"] + \
                                                   additional_instructions
                    temp.extend(["{0} = functools.partial(__globals['{0}'],listener={1})".format(
                            field, self.listeners[key].get_id())
                                 for field in ["Sell", "Buy", "SellShort", "BuyToCover"]])
                    signal_to_inject_init[key] = code_lines + temp + ["del(functools)", "del(__globals)"] + \
                                                 additional_instructions
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
                    self.listeners[key].add_parameters(para_name, default)
        series_exporter = SeriesExporter()  # deal with the export syntax
        # export the system functions in use
        for func, signals in funcs_in_use.items():
            for signal in signals:
                fullname = os.path.join(sys_func_dir, func + ".py")
                with codecs.open(fullname, "r", "utf-8") as f:
                    func_ast = ast.parse(f.read())
                    f.close()
                function_injector = LocalsInjector({func: function_to_inject_init[signal]},
                                                   {func: function_to_inject_loop[signal]})
                function_injector.visit(func_ast)
                func_ast = series_exporter.visit(func_ast)
                import_inspector.visit(func_ast)  # 检查模块导入
                # TODO 多个handle时需要对每个handle调用的系统函数建立独立的系统函数
                exec(compile(func_ast, "[SysFunctions:%s]" % func, mode="exec"), function_globals_, function_locals)
                self.system_functions['%s.%s' % (signal, func)] = SeriesFunction(function_locals[func], signal)
                # new方法是对__init__的封装，创建SeriesFunction对象所需信息有其所在的函数体本身，signal和其运行时传入的参数，
                # 编译时所能确定的只有前者，采用偏函数的方式将两者结合到一起
        # inject global vars into locals of handler
        signal_injector = LocalsInjector(signal_to_inject_init, signal_to_inject_loop)
        signal_injector.visit(ast_)
        ast_ = series_exporter.visit(ast_)
        InitTransformer().visit(ast_)
        exec(compile(ast_, "[Strategy:%s]" % self.name, mode="exec"), signal_globals_, signal_locals_)
        for key in signal_to_inject_init.keys():
            self.listeners[key].set_generator(signal_locals_[key])
        print("<%s>信号添加成功" % self.name)
        if 'init' in self.handlers:
            self.handlers['init'] = signal_locals_['init']
            print(self.handlers['init']())
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
        for function in self.system_functions.values():
            function.start()
        self.__printer.start()
        print(self.name + u'开始运行')

    # ----------------------------------------------------------------------
    def stop(self):
        """
        停止交易
        同上
        """
        self.trading = False
        for listener in self.listeners.values():
            listener.stop()
        for function in self.system_functions.values():
            function.stop()
        self.__printer.stop()
        print(self.name + u'停止运行')
