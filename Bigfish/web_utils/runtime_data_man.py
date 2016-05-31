# -*- coding: utf-8 -*-

import pymysql
from Bigfish.web_utils.connection import conn

class runtime_data():
    def __init__(self,userid):
        self._userid=userid
        self._conn=conn

    def __del__(self):
        self._conn.close()

    def get_code(self):
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("select code from code where user=%s", self._userid)
        row = cur.fetchone()
        if row:
            return row['code']
        return None

    def get_config(self):
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("select * from config where user=%s", self._userid)
        row = cur.fetchone()
        if row:
            row.pop('idconfig')
            return row
        return None

    def save_code(self,code):
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("select * from code where user=%s", self._userid)
        if cur.fetchone() is not None:
            cur.execute("update code set code = %s where user= %s", (code,self._userid))
        else:
            cur.execute("insert into code (user,code) value (%s,%s)", (self._userid,code))
        conn.commit()
        return True

    def save_config(self,config):
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute("select * from config where user=%s", self._userid)
        if cur.fetchone():
            cur.execute("update config set user = %s,name = %s,time_frame = %s, account = %s, password = %s, trading_mode = %s, symbols = %s where user=%s",
                        (self._userid,
                config[ 'name'],
                config[ 'time_frame'],
                config[ 'account'],
                config[ 'password'],
                config[ 'trading_mode'],
                config[ 'symbols'][0],self._userid))

        else:
            cur.execute("insert into config (user,name,time_frame, account, password, trading_mode, symbols) value (%s,%s,%s,%s,%s,%s,%s)", (self._userid,
                config[ 'name'],
                config[ 'time_frame'],
                config[ 'account'],
                config[ 'password'],
                config[ 'trading_mode'],
                config[ 'symbols'][0]))
        conn.commit()
        return True

if __name__=='__main__':

    DATA={
      'user': '123',
      'name': 'lsd',
      'time_frame': 'M1',
      'account': 'sdf',
      'password':'123447',
      'trading_mode': 'On Tick',
      'symbols': ['USDEUR'],
      'code':'SDF2f'
      }

    rd=runtime_data('0921376')
    print(rd.save_code(DATA['code']))
    print(rd.get_code())