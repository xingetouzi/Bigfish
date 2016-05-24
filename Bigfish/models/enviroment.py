from Bigfish.core._strategy import InjectingInfo
from Bigfish.utils.ast import LocalsInjector
from Bigfish.utils.log import LoggerInterface


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

    def update_const(self, dict_):
        self.__globals.const.update(dict_)

    def update_var(self, dict_):
        self.__globals.var.update(dict_)

    def update(self, globals_: Globals):
        self.__globals.update(globals_)

    def add_system_function(self, name, func):
        self.__system_functions[name] = func


class APIInterface:
    def __init__(self):
        pass

    def get_APIs(self, **kwargs) -> Globals:
        raise NotImplementedError


class EnvironmentSetter(LoggerInterface):
    EXCLUDE = ["Buy, Sell, BuyToCover, SellShort"]

    def __init__(self, environment):
        assert isinstance(environment, Environment)
        self.__environment = environment
        LoggerInterface.__init__(self)
        self._logger_name = "EnvironmentSetter"

    def set_environment(self, ast, func_name, allow_trading=True):
        return self.get_injector(allow_trading).visit(ast)

    def get_injector(self, func_name, allow_trading=True):
        exclude = [] if allow_trading else self.EXCLUDE
        to_injector_init = ["__globals=globals()"]
        to_injector_init.extend(
                ["{0} = __globals[\"{0}\"]".format(key) for key, value in self.__environment.globals_init.items()
                 if key not in exclude])
        globals_var = self.__environment.globals_var
        to_injector_init.extend(
                ["{0} = __globals[\"{0}\"]".format("get" + key) for key, value in globals_var.items()])
        to_injector_var = ["{0} = get{0}()".format(key) for key, value in globals_var.items()]
        return LocalsInjector(InjectingInfo(func_name, to_injector_init, to_injector_var))

    def get_globals(self, allow_trading=True):
        exclude = [] if allow_trading else self.EXCLUDE
        result = {}
        result.update({key: value for key, value in self.__environment.globals_const.items()
                       if key not in exclude})
        result.update({"get" + key: value for key, value in self.__environment.globals_var.items()})
        return result
