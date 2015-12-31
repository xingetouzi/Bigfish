# -*- coding: utf-8 -*-

import sqlite3
from Bigfish.models import Symbol
import os


DATABASE_NAME = "Bigfish/strategy.db"
SYMBOL_LIST = {"EUR/USD": "欧元/美元",
               "XAU/USD": "黄金/美元",
               "GBP/USD": "英镑/美元",
               "EUR/JPY": "欧元/日元",
               "USD/JPY": "美元/日元",
               "GBP/JPY": "英镑/日元",
               "AUD/JPY": "澳元/日元",
               "EUR/CAD": "欧元/加元",
               "EUR/GBP": "欧元/英镑",
               "AUD/USD": "澳元/美元",
               "EUR/AUD": "欧元/澳元",
               "USD/CAD": "美元/加元",
               "USD/CHF": "美元/瑞郎",
               "EUR/CHF": "欧元/瑞郎",
               "GBP/CHF": "英镑/瑞郎",
               "AUD/NZD": "澳元/纽元",
               "EUR/NZD": "欧元/纽元",
               }


def connect():
    conn = sqlite3.connect(os.path.join(os.path.expanduser("~"), DATABASE_NAME))
    return conn


def create_symbol():
    """
    创建交易品种数据库表
    """
    # TODO (添加)资产的其他信息，如滑点、手续费等信息
    create_sql = """
        create table if not exists category (
            id integer primary key autoincrement,
            en_name varchar(10),
            zh_name varchar(20))
        """
    with connect() as conn:
        conn.execute(create_sql)
        conn.commit()


def init_symbol():
    # TODO 扩充品种, 修改等,或者新添修改表结构的函数
    with connect() as conn:
        conn.execute("DELETE FROM category")
        sql_list = [(en_name, zh_name) for en_name, zh_name in SYMBOL_LIST.items()]
        conn.executemany("INSERT INTO category(en_name, zh_name) values(?, ?)", sql_list)
        conn.commit()


def exists():
    exist_sql = "SELECT COUNT(*) FROM sqlite_master where type='table' and name='category'"
    with connect() as conn:
        cursor = conn.execute(exist_sql)
        ret = cursor.fetchone() is not None
        return ret


# ================下面是对模块外暴露的方法================ #
def get_all_symbols():
    all_symbol = []
    get_all_sql = "SELECT en_name, zh_name FROM category"
    with connect() as conn:
        cursor = conn.execute(get_all_sql)
        for row in cursor.fetchall():
            category = Symbol(row[0], row[1])
            all_symbol.append(category)
    return all_symbol
