# -*- coding: utf-8 -*-

from Bigfish.models import Symbol
from Bigfish.config import SYMBOL_LIST
__all__ = ['get_all_symbols']

_all_symbols = [Symbol(s['en_name'].replace('/', ''), s['zh_name']) for s in SYMBOL_LIST.values()]


# ================下面是对模块外暴露的方法================ #
def get_all_symbols():
    global _all_symbols
    return _all_symbols.copy()
