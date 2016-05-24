# -*- coding: utf-8 -*-

# 系统模块
import ast
import codecs
import inspect
import os
from functools import partial
from weakref import proxy
from Bigfish.event.handle import SignalFactory
from Bigfish.models.common import HasID
from Bigfish.models.base import Runnable
from Bigfish.models.enviroment import APIInterface, Globals
from Bigfish.models.model import User
from Bigfish.store.code_manage import get_sys_func_list
from Bigfish.store.directory import UserDirectory
from Bigfish.utils.ast import LocalsInjector, SeriesExporter, SystemFunctionsDetector, ImportInspector, \
    InitTransformer, wrap_with_module, TradingCommandsTransformer
from Bigfish.utils.common import check_time_frame
from Bigfish.utils.export import export, SeriesFunction
from Bigfish.utils.log import FilePrinter, LoggerInterface


class InjectingInfo:
    """
    注入信息，用于创建API注入器
    """

    def __init__(self, function_name, to_inject_init, to_inject_var):
        self.function_name = function_name
        self.to_inject_init = to_inject_init
        self.to_inject_var = to_inject_var


class StrategyCode:
    """
    策略代码,单独拿出来方便实现加密机制
    """

    def __init__(self, name, code):
        self.name = name
        self.code = code


class SignalLocalSetting:
    """
    Singal的局部设定
    """

    def __init__(self, symbols, time_frame, max_len):
        self.symbols = symbols
        self.time_frame = time_frame
        self.max_len = max_len
        self.paras = {}


class CodeParser:
    """
    代码解析器，负责将策略代码拆分成Init，Signal，全局变量定义等部分
    抽取出Signal的局部设置以及语法树
    """

    def __init__(self, code: StrategyCode, strategy: Strategy):
        self.__strategy = strategy
        self.__code = code
        self.__signals_setting = {}
        self.__signals_ast = {}
        self.__ast_root = ast.parse(self.__code.code, filename="[Strategy:%s]" % self.__code.name, mode="exec")
        self.__globals = Globals({}, {})
        self._parse()

    @property
    def ast_root(self) -> ast.AST:
        return self.__ast_root

    @property
    def signals(self) -> list:
        return list(self.__signals_setting.keys())

    @property
    def globals(self) -> Globals:
        return self.__globals.copy()

    def get_signal_setting(self, signal) -> SignalLocalSetting:
        return self.__signals_setting[signal]

    def get_signal_ast(self, signal) -> ast.AST:
        return self.__signals_ast[signal]

    @staticmethod
    def _get_parameter_default(paras, name, check, default, pop=True):
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

    def _init(self, loc):
        init_transformer = InitTransformer()
        init_transformer.visit(self.ast_root)
        # XXX 必须要一个module node作为根节点。
        exec(compile(wrap_with_module(init_transformer.init_node), "[Strategy:%s]" % self.__code.name, mode="exec")
             , dict(open=self.__strategy.open, **loc), loc)
        self.__globals.update(Globals(loc["init"](), {}))

    def _extract_signal_setting(self, name, func):
        paras = inspect.signature(func).parameters.copy()  # 获取handler函数的参数列表
        is_handle = self._get_parameter_default(paras, "IsHandle", lambda x: isinstance(x, bool), True)
        custom = self._get_parameter_default(paras, "Custom", lambda x: isinstance(x, bool), False)
        if not is_handle:
            return
        if not custom:
            # TODO加入真正的验证方法
            # 转化为tuple是因为symbols要那来当做字典的键
            symbols = tuple(
                    self._get_parameter_default(paras, "Symbols", lambda x: True, self.__strategy.symbols))
            time_frame = self._get_parameter_default(paras, "TimeFrame", check_time_frame,
                                                     self.__strategy.time_frame)
            max_length = self._get_parameter_default(paras, "MaxLen", lambda x: isinstance(x, int) and (x > 0),
                                                     self.__strategy.max_length)
            setting = SignalLocalSetting(symbols, time_frame, max_length)
            for para_name in paras.keys():
                # TODO加入类型检测
                default = self._get_parameter_default(paras, para_name, lambda x: True, None, pop=False)
                if default is None:
                    raise ValueError("参数%s未指定初始值" % para_name)
                elif not isinstance(default, (int, float)):
                    raise ValueError("参数%s的值必须为整数或浮点数" % para_name)
                setting.paras[para_name] = default
            self.__signals_setting[name] = setting

    def _parse(self):
        glb = {}
        loc = {}
        exec(compile(self.__code.code, "[Strategy:%s]" % self.__code.name, mode="exec"), glb, loc)
        for key, value in loc.items():
            if inspect.isfunction(value):
                if key == "init":
                    self._init(loc)
                else:
                    self._extract_signal_setting(key, value)
        for node in self.__ast_root.stmt:
            if isinstance(node, ast.FunctionDef) and (node.name in self.signals):
                self.__signals_ast[node.name] = node
        self.__globals.update(Globals({key: value for key, value in loc.items() if key not in self.signals}, {}))


class Strategy(HasID, LoggerInterface, APIInterface, Runnable):
    API_FUNCTION = ["Buy", "Sell", "SellShort", "BuyToCover", "Export"] + get_sys_func_list()
    API_VARIABLES = ["O", "Open", "Opens", "H", "High", "Highs", "L", "Low", "Lows", "C", "Close", "Closes",
                     "Datetime", "Datetimes", "D", "Timestamp", "Timestamps", "T", "Volume", "Volumes", "V",
                     "Symbols", "Symbol", "BarNum", "MarketPosition", "Positions", "Pos", "Cap",
                     "CurrentContracts", "Point", "TimeFrame", "Symbols", "StartTime", "MaxLen", "EndTime"]

    def __init__(self, engine, code, config):
        """Constructor"""
        super().__init__()
        LoggerInterface.__init__(self)
        APIInterface.__init__(self)
        Runnable.__init__(self)
        self.__id = self.next_auto_inc()
        self.user = config.user
        self.user_dir = UserDirectory(User(config.user))
        self.__strategy_code = StrategyCode(config.name, code)
        self.__code_parser = None
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
        # 将策略容器与对应代码文件关联
        self.bind_code_to_strategy()

    @staticmethod
    def open(*args, **kwargs):
        raise RuntimeError("open函数已被禁用")

    def get_output(self):
        with open(self.__printer.get_path()) as f:
            content = f.read()
            f.close()
        return content

    def get_parameters(self):
        return {key: value.get_parameters() for key, value in self.signals.items()}

    def set_parameters(self, parameters):
        for handle, paras in parameters.items():
            self.signals[handle].set_parameters(**paras)

    def get_id(self):
        return self.__id

    def put_context(self, **kwargs):
        for key, value in kwargs.items():
            self.__context[key] = value

    def get_context(self, key):
        return self.__context[key]

    def initialize(self):
        self.__context.clear()
        self.series_storage.clear()

    def bind_code_to_strategy(self):
        """
        将策略容器与策略代码关联
        :param code:
        :return:
        """
        # parse the strategy
        self.__code_parser = CodeParser(self.__strategy_code, self)
        # check the import
        import_inspector = ImportInspector()
        import_inspector.visit(self.__code_parser.ast_root)  # 模块导入检查
        # get the system functions in use
        for singal in self.__code_parser.signals:
            sys_func_detector = SystemFunctionsDetector()
            sys_func_detector.visit(self.__code_parser.ast_root)
            sys_func_dir = self.user_dir.get_sys_func_dir()
            funcs_in_use = sys_func_detector.get_funcs_in_use()

        # init中可以设定全局变量，所以要以"global foo"的方式进行注入。




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
                self.system_functions["%s.%s" % (signal, func)] = SeriesFunction(function_locals[func], signal)
                # new方法是对__init__的封装，创建SeriesFunction对象所需信息有其所在的函数体本身，signal和其运行时传入的参数，
                # 编译时所能确定的只有前者，采用偏函数的方式将两者结合到一起
        # inject global vars into locals of handler
        signal_injector = LocalsInjector(signal_to_inject_init, signal_to_inject_loop)
        signal_injector.visit(ast_)
        ast_ = series_exporter.visit(ast_)
        ast_ = TradingCommandsTransformer().visit(ast_)  # 给买卖语句表上行列号
        exec(compile(ast_, "[Strategy:%s]" % self.name, mode="exec"), signal_globals_, loc)
        for key in signal_to_inject_init.keys():
            self.signals[key].set_generator(loc[key])
        self.logger.info("<%s>策略添加成功" % self.name)
        return True

    def _start(self):
        """
        启动交易
        """
        self.initialize()
        for listener in self.signals.values():
            listener.start()
        for function in self.system_functions.values():
            function.start()
        self.__printer.start()
        self.logger.info("<%s>策略开始运行" % self.name)

    def _stop(self):
        """
        停止交易
        同上
        """
        for listener in self.signals.values():
            listener.stop()
        for function in self.system_functions.values():
            function.stop()
        self.__printer.stop()
        self.logger.info("<%s>策略停止运行" % self.name)

    def get_APIs(self, symbols=None, time_frame=None) -> Globals:
        temp = {
            "Symbols": symbols, "TimeFrame": time_frame, "Symbol": symbols[0], "StartTime": self.start_time,
            "EndTime": self.end_time,
            "Context": self.__context, "Export": partial(export, strategy=self), "Put": self.put_context,
            "Get": self.get_context, "print": self.__printer.print, "open": self.open,
            "signals": self.signals, "system_functions": self.system_functions}
        return Globals(temp, {})
