# -*- coding: utf-8 -*-
"""
系统函数库管理
"""

from Bigfish.models import Code
import os
import codecs


def get_sys_func(code_name):
    """
    根据代码名称,获取该段策略代码
    :param code_name: 代码名称
    :return 返回一个code对象
    """
    sys_func_path = os.path.join(get_sys_func_dir(), code_name + ".py")

    if os.path.exists(sys_func_path):
        # file = open(sys_func_path, 'r')
        file = codecs.open(sys_func_path, mode='r', encoding="utf8")
        code = Code(code_name, code_type=2, content=file.read())
        file.close()
        return code
    return None


def get_sys_func_dir():
    return os.path.join(os.path.dirname(__file__), '..', '..', 'bigfish_functions')


def get_sys_func_list():
    return sorted(list(map(lambda x: x.replace('.py', ''),
                           set(os.listdir(get_sys_func_dir())) - {'__init__.py', '__pycache__'})))
