# -*- coding: utf-8 -*-
"""
用户策略管理
"""
from Bigfish.models import Code
from Bigfish.store import UserDirectory
import os


def save_code(user, code):
    """
    保存用户代码
    :param user: 用户对象
    :param code: Code对象
    """
    udir = UserDirectory(user)
    current_path = os.path.join(udir.get_home(code=code), code.name)
    file = open(current_path, 'w+')  # 打开一个文件的句柄
    file.write(code.content)  # 写入代码(策略)内容
    file.flush()
    file.close()


def rename_code(user, code, new_name):
    """
    给用户代码重命名
    :param user: 用户对象
    :param code: Code对象
    :param new_name: 新名称
    :return true:重命名成功, false:存在同名文件
    """
    udir = UserDirectory(user)
    home = udir.get_home(code=code)
    old_path = os.path.join(home, code.name)
    new_path = os.path.join(home, new_name)
    if os.path.exists(new_path):
        return False
    os.rename(old_path, new_path)
    return True


def rename_strategy(user, old_name, new_name):
    code = Code(old_name)
    return rename_code(user, code, new_name)


def rename_func(user, old_name, new_name):
    code = Code(old_name, code_type=2)
    return rename_code(user, code, new_name)


def delete_strategy(user, name):
    udir = UserDirectory(user)
    os.remove(os.path.join(udir.get_strategy_dir(), name))


def delete_func(user, name):
    udir = UserDirectory(user)
    os.remove(os.path.join(udir.get_func_dir(), name))


def get_func(user, code_name):
    """
    根据代码名称,获取该段函数代码
    :param user: 用户对象
    :param code_name: 代码名称
    :return 返回一个code对象
    """
    udir = UserDirectory(user)
    func_path = os.path.join(udir.get_func_dir(), code_name)

    if os.path.exists(func_path):
        file = open(func_path, 'r')
        code = Code(code_name, code_type=2, content=file.read())
        file.close()
        return code
    return None


def get_strategy(user, code_name):
    """
    根据代码名称,获取该段策略代码
    :param user: 用户对象
    :param code_name: 代码名称
    :return 返回一个code对象
    """
    udir = UserDirectory(user)
    strategy_path = os.path.join(udir.get_strategy_dir(), code_name)

    if os.path.exists(strategy_path):
        file = open(strategy_path, 'r')
        code = Code(code_name, code_type=1, content=file.read())
        file.close()
        return code
    return None
