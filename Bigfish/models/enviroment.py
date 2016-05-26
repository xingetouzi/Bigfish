import ast
from Bigfish.utils.ast import LocalsInjector, wrap_with_module, InjectingInfo
from Bigfish.utils.log import LoggerInterface
from Bigfish.utils.export import SeriesFunction


class Globals:
    def __init__(self, const: dict, var: dict):
        self.const = const
        self.var = var

    def update(self, globals_):
        assert isinstance(globals_, Globals)
        self.const.update(globals_.const)
        self.var.update(globals_.var)


class Environment:
    def __init__(self):
        self.__globals = Globals({}, {})
        self.__system_functions = {}

    @property
    def globals_const(self):
        return self.__globals.const.copy()

    @property
    def globals_var(self):
        return self.__globals.var.copy()

    @property
    def system_functions(self):
        return self.__system_functions.copy()

    def update_const(self, dict_):
        self.__globals.const.update(dict_)

    def update_var(self, dict_):
        self.__globals.var.update(dict_)

    def update(self, globals_: Globals):
        self.__globals.update(globals_)

    def add_system_function(self, name, value: SeriesFunction):
        self.__system_functions[name] = value

    def get_system_function(self, name) -> SeriesFunction:
        return self.__system_functions.get(name, None)


class APIInterface:
    def __init__(self):
        pass

    def get_APIs(self, **kwargs) -> Globals:
        raise NotImplementedError


class EnvironmentSetter(LoggerInterface):
    EXCLUDE = ["Buy, Sell, BuyToCover, SellShort"]

    def __init__(self, environment: Environment):
        assert isinstance(environment, Environment)
        self.__environment = environment
        LoggerInterface.__init__(self)
        self._logger_name = "EnvironmentSetter"

    def get_func_within_environment(self, ast_: ast.AST, allow_trading=True, filename=None):
        assert isinstance(ast_, ast.FunctionDef)
        self.set_environment(ast_, allow_trading=allow_trading)
        glb = self.get_globals(allow_trading=allow_trading)
        loc = {}
        if filename is None:
            filename = ast_.name
        exec(compile(wrap_with_module(ast_), filename=filename, mode="exec"), glb, loc)
        return loc[ast_.name]

    def set_environment(self, ast_, allow_trading=True):
        injector = self.get_injector(allow_trading)
        injector.visit(ast_)

    def get_injector(self, allow_trading=True):
        exclude = [] if allow_trading else self.EXCLUDE
        to_inject_init = ["__globals = globals()"]
        to_inject_init.extend(
            ["{0} = __globals[\"{0}\"]".format(key) for key in self.__environment.globals_const.keys()
             if key not in exclude])
        to_inject_init.extend(
            ["{0} = __globals[\"{0}\"]".format(key) for key in self.__environment.system_functions.keys()])
        globals_var = self.__environment.globals_var
        to_inject_init.extend(
            ["{0} = __globals[\"{0}\"]".format("get" + key) for key in globals_var.keys()])
        to_inject_var = ["{0} = get{0}()".format(key) for key, value in globals_var.items()]
        return LocalsInjector(InjectingInfo(to_inject_init, to_inject_var))

    def get_globals(self, allow_trading=True):
        exclude = [] if allow_trading else self.EXCLUDE
        result = {}
        result.update({key: value for key, value in self.__environment.globals_const.items()
                       if key not in exclude})
        result.update({"get" + key: value for key, value in self.__environment.globals_var.items()})
        result.update(self.__environment.system_functions)
        return result
