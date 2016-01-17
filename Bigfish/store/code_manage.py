# -*- coding: utf-8 -*-
"""
用户策略管理
"""
from Bigfish.models import Code
from Bigfish.store import UserDirectory
import os
import sqlite3
import shutil


def save_code(user, code):
    """
    保存用户代码
    :param user: 用户对象
    :param code: Code对象
    """
    udir = UserDirectory(user)
    home = udir.get_home(code=code)
    current_path = os.path.join(home, code.name)

    if not os.path.exists(current_path):  # 如果是第一次创建,则记录相关信息
        __execute_sql__(home, "insert into code_info (name) values (?)", code.name)

    file = open(current_path, 'w+')  # 打开一个文件的句柄
    file.write(code.content)  # 写入代码(策略)内容
    file.flush()
    file.close()


def __get_store_db__(home):
    db_path = os.path.join(home, ".store.db")
    if not os.path.exists(db_path):
        open(db_path, "w+")
        with sqlite3.connect(db_path) as conn:
            conn.execute("create table code_info (id integer primary key autoincrement, name varchar(30) unique)")
            conn.commit()
    return db_path


def __execute_sql__(home, sql, *args):
    with sqlite3.connect(__get_store_db__(home)) as conn:
        conn.execute(sql, args)
        conn.commit()


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
    __execute_sql__(home, "update code_info set name=? where name=?", new_name, code.name)
    return True


def rename_strategy(user, old_name, new_name):
    code = Code(old_name)
    return rename_code(user, code, new_name)


def rename_func(user, old_name, new_name):
    code = Code(old_name, code_type=2)
    return rename_code(user, code, new_name)


def delete_strategy(user, name):
    udir = UserDirectory(user)
    home = udir.get_strategy_dir()
    os.remove(os.path.join(home, name))
    __execute_sql__(home, "delete from code_info where name=?", name)


def delete_func(user, name):
    udir = UserDirectory(user)
    home = udir.get_func_dir()
    os.remove(os.path.join(home, name))
    __execute_sql__(home, "delete from code_info where name=?", name)


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


def get_sys_func(code_name):
    """
    根据代码名称,获取该段策略代码
    :param code_name: 代码名称
    :return 返回一个code对象
    """
    sys_func_path = os.path.join(get_sys_func_dir(), code_name + ".py")

    if os.path.exists(sys_func_path):
        file = open(sys_func_path, 'r')
        code = Code(code_name, code_type=2, content=file.read())
        file.close()
        return code
    return None


def get_code_list(home):
    code_list = []

    demo = os.path.join(home, "demo.py")
    if not os.path.exists(demo):
        demo_ = os.path.join(os.path.dirname(__file__), '..', '..', 'demo.py')

        # 复制代码到用户目录
        __execute_sql__(home, "insert into code_info (name) values (?)", 'demo.py')
        shutil.copy(demo_, home)

    with sqlite3.connect(__get_store_db__(home)) as conn:
        cursor = conn.execute("select id, name from code_info")
        for row in cursor.fetchall():
            code_list.append(dict(id=row[0], name=row[1]))
    return code_list


def get_sys_func_dir():
    return os.path.join(os.path.dirname(__file__), '..', '..', 'bigfish_functions')


def get_sys_func_list():
    return list(map(lambda x: x.replace('.py', ''),
                    set(os.listdir(get_sys_func_dir())) - {'__init__.py', '__pycache__'}))


def get_func_list(user):
    """
    获取用户编写的函数列表
    :param user
    """
    u_dir = UserDirectory(user)
    return get_code_list(u_dir.get_func_dir())


def get_strategy_list(user):
    """
    获取用户编写的策略列表
    :param user
    """
    u_dir = UserDirectory(user)
    return get_code_list(u_dir.get_strategy_dir())
