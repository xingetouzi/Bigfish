# -*- coding: utf-8 -*-

import pymysql


def get_connection():
    return pymysql.connect(host="115.29.54.208", user='xinger', passwd='ShZh_forex_4', db='runtime', charset='utf8',
                           use_unicode=True)


conn = get_connection()