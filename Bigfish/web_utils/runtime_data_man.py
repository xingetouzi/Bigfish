# -*- coding: utf-8 -*-

import pymysql
from .connection import conn


class RuntimeData:
    def __init__(self, user_id):
        self._user_id = user_id
        self._conn = conn

    def get_code(self):
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("select code from code where user_id=%s", self._user_id)
        row = cur.fetchone()
        if row:
            return row
        return None

    def get_config(self):
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("select * from config where user_id=%s", self._user_id)
        row = cur.fetchone()
        if row:
            return row
        return None

    def save_code(self, code):
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("insert into code (user_id,code) value (%s,%s)", (self._user_id, code))
        conn.commit()
        return True

    def save_config(self, config):
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute(
            "insert into config (user_id,name,time_frame, account, password, trading_mode, symbols) value (%s,%s,%s,%s,%s,%s,%s)",
            (self._user_id,
             config['name'],
             config['time_frame'],
             config['account'],
             config['password'],
             config['trading_mode'],
             config['symbols'][0]))
        conn.commit()
        return True


if __name__ == '__main__':
    DATA = {'user': '123',
            'name': 'lsd',
            'time_frame': 'M1',
            'account': 'sdf',
            'password': '1234567',
            'trading_mode': 'On Tick',
            'symbols': ['USDEUR'],
            'code': 'siduutjdf,fkefjjsdf=sdfefsdf dfwsfdssdfsfsff-df--s-f--sdfwe=fsd-f-0s0=ef0-'
            }
    rd = RuntimeData('0921376')
    print(rd.get_code())
    print(rd.get_config())
