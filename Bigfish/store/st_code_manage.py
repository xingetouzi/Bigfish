# -*- coding: utf-8 -*-
"""
用户策略管理
"""
import pymysql
from Bigfish.models import Code
import os
import codecs
from Bigfish.store.connection import conn


def save_code(user, code):
    """
    保存用户代码
    :param user: 用户对象
    :param code: Code对象
    """
    if not code.name:
        raise ValueError("code.name is empty")

    conn.ping(True)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    if not strategy_exists(user, code.name):  # 如果是第一次创建,则记录相关信息
        cur.execute("insert into code_info (name, user_id, content) value (%s, %s, %s)",
                    (code.name, user.user_id, code.content))
    else:
        cur.execute("update code_info set content=%s where name=%s and user_id=%s",
                    (code.content, code.name, user.user_id))
    conn.commit()


def rename_strategy(user, old_name, new_name):
    if not new_name:
        raise ValueError("code.name is empty")
    if strategy_exists(user, new_name):
        return False
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("update code_info set name=%s where user_id=%s and name=%s", (new_name, user.user_id, old_name))
    conn.commit()
    return True


def delete_strategy(user, name):
    conn.ping(True)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    if name == 'demo':
        cur.execute("update code_info set stat=1 where user_id=%s and name=%s", (user.user_id, name))
    else:
        cur.execute("delete from code_info where user_id=%s and name=%s", (user.user_id, name))
    conn.commit()


def get_strategy(user, code_name):
    """
    根据代码名称,获取该段策略代码
    :param user: 用户对象
    :param code_name: 代码名称
    :return 返回一个code对象
    """
    conn.ping(True)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("select name, content from code_info where user_id=%s and name=%s and stat=0", (user.user_id, code_name))
    row = cur.fetchone();
    if row:
        return Code(code_name, content=row["content"])
    return None


def get_strategy_list(user):
    """
    获取用户编写的策略列表
    :param user
    """
    conn.ping(True)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("select id from code_info where name=%s and user_id=%s", ("demo", user.user_id,))
    row = cur.fetchone()
    if not row:
        demo_ = os.path.join(os.path.dirname(__file__), '..', '..', 'demo.py')
        file = codecs.open(demo_, mode='r', encoding="utf8")
        content = file.read()
        cur.execute("insert into code_info (name, user_id, content) value (%s, %s, %s)", ("demo", user.user_id, content))
        file.close()
    cur.execute("select id, name from code_info where user_id=%s and stat=0", (user.user_id,))
    code_list = cur.fetchall()
    conn.commit()
    return code_list


def strategy_exists(user, name):
    conn.ping(True)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("select id, name from code_info where name=%s and user_id=%s", (name, user.user_id))
    return cursor.fetchone() is not None
