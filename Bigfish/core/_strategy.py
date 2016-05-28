# -*- coding: utf-8 -*-

# 系统模块
import ast
import codecs
import inspect
import os
from functools import partial
from weakref import proxy

from Bigfish.event.handle import SignalFactory
from Bigfish.models.base import Runnable
from Bigfish.models.common import HasID
from Bigfish.models.enviroment import APIInterface, Globals, Environment, EnvironmentSetter
from Bigfish.models.model import User
from Bigfish.models.config import ConfigInterface
from Bigfish.store.code_manage import get_sys_func_list
from Bigfish.store.directory import UserDirectory
from Bigfish.utils.ast import SeriesExporter, SystemFunctionsDetector, ImportInspector, \
    InitTransformer, wrap_with_module, TradingCommandsTransformer, find_func_in_module
from Bigfish.utils.common import check_time_frame
from Bigfish.utils.export import export, SeriesFunction
from Bigfish.utils.log import FilePrinter, LoggerInterface


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


class Strategy(HasID, LoggerInterface, APIInterface, Runnable, ConfigInterface):
    API_FUNCTION = ["Buy", "Sell", "SellShort", "BuyToCover", "Export"] + get_sys_func_list()
    API_VARIABLES = ["O", "Open", "Opens", "H", "High", "Highs", "L", "Low", "Lows", "C", "Close", "Closes",
                     "Datetime", "Datetimes", "D", "Timestamp", "Timestamps", "T", "Volume", "Volumes", "V",
                     "Symbols", "Symbol", "BarNum", "MarketPosition", "Positions", "Pos", "Cap",
                     "CurrentContracts", "Point", "TimeFrame", "Symbols", "StartTime", "MaxLen", "EndTime"]

    def __init__(self, engine, code, parent=None):
        """Constructor"""
        super().__init__()
        LoggerInterface.__init__(self)
        APIInterface.__init__(self)
        Runnable.__init__(self)
        ConfigInterface.__init__(self, parent=parent)
        self.__id = self.next_auto_inc()
        self.user = self.config.user
        self.user_dir = UserDirectory(User(self.config.user))
        self.__strategy_code = StrategyCode(self.config.name, code)
        self.__code_parser = None
        self.engine = proxy(engine)
        self.time_frame = self.config.time_frame
        self.symbols = self.config.symbols
        self.start_time = self.config.start_time
        self.end_time = self.config.end_time
        self.capital_base = self.config.capital_base
        self.handlers = {}
        self.signal_factory = SignalFactory()
        self.signals = {}
        self.system_functions = {}
        self.series_storage = {}
        self.printer = FilePrinter(self.config.user, self.config.name, self.engine)
        self.__context = {}
        self._setting()
        # 将策略容器与对应代码文件关联

    @staticmethod
    def open(*args, **kwargs):
        raise RuntimeError("open函数已被禁用")

    def get_output(self):
        with open(self.printer.get_path()) as f:
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

    def _get_system_func_ast(self, func):
        path = os.path.join(self.user_dir.get_sys_func_dir(), func + ".py")
        with codecs.open(path, "r", "utf-8") as f:
            func_ast = find_func_in_module(func, ast.parse(f.read()))
            f.close()
        return func_ast

    def _setting(self):
        # parse the strategy
        self.__code_parser = CodeParser(self.__strategy_code, self)
        for signal in self.__code_parser.signals:
            setting = self.__code_parser.get_signal_setting(signal)
            self.engine.add_cache_info(setting.symbols, setting.time_frame, setting.max_len)
            self.signals[signal] = self.signal_factory.new(self.engine, self.user, self.__strategy_code.name, signal,
                                                           setting.symbols, setting.time_frame)

    def _init(self):
        # check the import
        import_inspector = ImportInspector()
        import_inspector.visit(self.__code_parser.ast_root)  # 模块导入检查
        # get the system functions in use
        for signal in self.__code_parser.signals:
            sys_func_detector = SystemFunctionsDetector()
            sys_func_detector.visit(self.__code_parser.get_signal_ast(signal))
            environment = Environment()
            for func in sys_func_detector.get_funcs_in_use():
                environment.add_system_function(func, SeriesFunction(signal=signal))
            setting = self.__code_parser.get_signal_setting(signal)
            environment.update(self.__code_parser.globals)
            environment.update(self.get_APIs(setting.symbols, setting.time_frame))
            environment.update(self.engine.get_APIs(self.get_id(), signal, setting.symbols, setting.time_frame))
            environment.update(self.signals[signal].get_APIs())
            self.signals[signal].environment = environment
            setter = EnvironmentSetter(environment)
            series_exporter = SeriesExporter()
            for func in sys_func_detector.get_funcs_in_use():
                func_ast = self._get_system_func_ast(func)
                func_ast = series_exporter.visit(func_ast)
                function = environment.get_system_function(func)
                function.set_generator(setter.get_func_within_environment(func_ast, allow_trading=False))
            signal_ast = self.__code_parser.get_signal_ast(signal)
            signal_ast = series_exporter.visit(signal_ast)
            signal_ast = TradingCommandsTransformer().visit(signal_ast)  # 给买卖语句表上行列号
            signal_func = setter.get_func_within_environment(signal_ast, allow_trading=False)
            self.signals[signal].set_generator(signal_func)
        self.logger.info("<%s>策略添加成功" % self.__strategy_code.name)

    def _recycle(self):
        self.__context.clear()
        self.series_storage.clear()

    def _start(self):
        """
        启动交易
        """
        self._init()
        for signal in self.signals.values():
            signal.start()
        for function in self.system_functions.values():
            function.start()
        self.printer.start()
        self.logger.info("<%s>策略开始运行" % self.__strategy_code.name)

    def _stop(self):
        """
        停止交易
        同上
        """
        for signal in self.signals.values():
            signal.stop()
        for function in self.system_functions.values():
            function.stop()
        self.printer.stop()
        self._recycle()
        self.logger.info("<%s>策略停止运行" % self.__strategy_code.name)

    def get_APIs(self, symbols=None, time_frame=None) -> Globals:
        temp = {
            "Symbols": symbols, "TimeFrame": time_frame, "Symbol": symbols[0], "StartTime": self.start_time,
            "EndTime": self.end_time,
            "Context": self.__context, "Export": partial(export, strategy=self), "Put": self.put_context,
            "Get": self.get_context, "print": self.printer.print, "open": self.open,
            "signals": self.signals, "system_functions": self.system_functions}
        return Globals(temp, {})


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
        return self.__globals

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

    # TODO 这里最好也使用Environment对象来设置
    def _init(self, loc):
        init_transformer = InitTransformer()
        init_transformer.visit(self.ast_root)
        # XXX 必须要一个module node作为根节点。
        exec(compile(wrap_with_module(init_transformer.init_node), "[Strategy:%s]" % self.__code.name, mode="exec")
             , dict(open=self.__strategy.open, print=self.__strategy.printer.print, **loc), loc)
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
            max_length = self._get_parameter_default(paras, "MaxLen", lambda x: isinstance(x, int) and (x > 0), None)
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
        self.__signals_ast = find_func_in_module(self.signals, self.__ast_root)
        self.__globals.update(Globals({key: value for key, value in loc.items() if key not in self.signals}, {}))
