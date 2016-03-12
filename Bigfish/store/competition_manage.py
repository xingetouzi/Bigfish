# -*- coding: utf-8 -*-
"""
参赛组合管理
"""
import pymysql
from Bigfish.models import Code, User
from Bigfish.store.connection import conn


MAX_COMPETITION_COUNT = 3


def add_competition(user, code):
    if not code.name:
        raise ValueError("code.name is empty.")

    if not check_competition_limit(user):
        raise KeyError("beyond competition limit.")

    __check_user(user)

    conn.ping(True)
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("insert into strategy_competition (name, user_id, content) value (%s, %s, %s)",
                (code.name, user.user_id, code.content))

    conn.commit()


def __check_user(user):
    if not user.user_id:
        raise ValueError("User not found.")


def update_competition_config(user, old_name, new_name):
    """
    修改参赛组合的设置
    Parameters
    ----------
    user: 修改的用户
    old_name: 要修改参赛策略名称
    new_name: 参赛策略新名称
    -------

    """
    __check_user(user)

    if not new_name:
        return

    conn.ping(True)
    cur = conn.cursor(pymysql.cursors.DictCursor)

    sql = "update strategy_competition set name=%s where name=%s and user_id=%s"
    cur.execute(sql, (new_name, old_name, user.user_id))

    conn.commit()


def update_competition_content(user, name, content):
    __check_user(user)

    conn.ping(True)
    cur = conn.cursor(pymysql.cursors.DictCursor)

    sql = "update strategy_competition set content=%s where name=%s and user_id=%s"
    cur.execute(sql, (content, name, user.user_id))

    conn.commit()


def remove_competition(user, name):
    __check_user(user)

    conn.ping(True)
    cur = conn.cursor(pymysql.cursors.DictCursor)

    sql = "delete from strategy_competition where name=%s and user_id=%s"
    cur.execute(sql, (name, user.user_id))

    conn.commit()


def get_competition_list(user):
    __check_user(user)

    conn.ping(True)
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("select id, name from strategy_competition where user_id=%s", (user.user_id,))
    code_list = cur.fetchall()
    conn.commit()
    return code_list


def get_competition(user, code_name):
    """
    根据代码名称,获取该段策略代码
    :param user: 用户对象
    :param code_name: 代码名称
    :return 返回一个code对象
    """
    conn.ping(True)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("select name, content from strategy_competition where user_id=%s and name=%s",
                (user.user_id, code_name))
    row = cur.fetchone()
    if row:
        return Code(code_name, content=row["content"])
    return None


def get_competition_count(user):
    conn.ping(True)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute("select count(name) as num from strategy_competition where user_id=%s", (user.user_id,))
    row = cur.fetchone()
    return row["num"]


def check_competition_limit(user):
    """
    检查用户是否还可以添加参赛策略
    Parameters
    ----------
    user: 用户

    Returns 如果还可以添加参赛组合则返回True
    -------

    """
    return get_competition_count(user) <= MAX_COMPETITION_COUNT


if __name__ == '__main__':
    user = User("10046")
    add_competition(user, Code("Hello", content="Hello,World!"))
    print(get_competition_list(user))
    print(get_competition(user, "Hello"))

    update_competition_content(user, "Hello", "Hi Hello,World")
    print(get_competition_list(user))
    print(get_competition(user, "Hello"))
    print("count=%s" % get_competition_count(user))

    update_competition_config(user, "Hello", "World")
    print(get_competition_list(user))

    remove_competition(user, "World")
    print(get_competition_list(user))
