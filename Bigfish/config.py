# -*- coding: utf-8 -*-

"""
项目配置文件
"""
__all__ = ["MEMORY_DEBUG", "DATABASE", "ASYNC", "MODULES_IMPORT", "SYMBOL_LIST", "CROSS_TRADE", "SYMBOL_LIST"]

MEMORY_DEBUG = False  # 是否开启内存检测模式
THROW_ERROR = False  # 是否正常抛出异常，True为正常抛出，False以日志的方式将异常记录下来
DATABASE = "mysql"  # 数据库
ASYNC = False  # 数据拉取方式
_system_model = {"array", "bisect", "cmath", "collections", "copy", "datetime", "functools", "heapq", "itertools",
                 "json", "math", "operator", "random", "re", "string", "time", "xml", }
_third_party_model = {"cvxopt", "dateutil", "hmmlearn", "numpy", "pandas", "pkkalman", "pytz", "scipy", "sklearn",
                      "statsmodels", }
MODULES_IMPORT = _system_model or _third_party_model  # 允许在策略代码中导入的模块列表
CROSS_TRADE = False  # 是否开启交叉盘
SYMBOL_LIST = {"EUR/USD": {"en_name": "EUR/USD", "zh_name": "欧元/美元"},
               # "XAU/USD": {"en_name": "XAU/USD", "zh_name": "黄金/美元"},
               "GBP/USD": {"en_name": "GBP/USD", "zh_name": "英镑/美元"},
               "USD/JPY": {"en_name": "USD/JPY", "zh_name": "美元/日元"},
               "AUD/USD": {"en_name": "AUD/USD", "zh_name": "澳元/美元"},
               "USD/CAD": {"en_name": "USD/CAD", "zh_name": "美元/加元"},
               "USD/CHF": {"en_name": "USD/CHF", "zh_name": "美元/瑞郎"},
               }
if CROSS_TRADE:
    SYMBOL_LIST.update({
        "EUR/JPY": {"en_name": "EUR/JPY", "zh_name": "欧元/日元"},
        "GBP/JPY": {"en_name": "GBP/JPY", "zh_name": "英镑/日元"},
        "AUD/JPY": {"en_name": "AUD/JPY", "zh_name": "澳元/日元"},
        "EUR/CAD": {"en_name": "EUR/CAD", "zh_name": "欧元/加元"},
        "EUR/GBP": {"en_name": "EUR/GBP", "zh_name": "欧元/英镑"},
        "EUR/AUD": {"en_name": "EUR/AUD", "zh_name": "欧元/澳元"},
        "EUR/CHF": {"en_name": "EUR/CHF", "zh_name": "欧元/瑞郎"},
        "GBP/CHF": {"en_name": "GBP/CHF", "zh_name": "英镑/瑞郎"},
        "AUD/NZD": {"en_name": "AUD/NZD", "zh_name": "澳元/纽元"},
        "EUR/NZD": {"en_name": "EUR/NZD", "zh_name": "欧元/纽元"},
    })
