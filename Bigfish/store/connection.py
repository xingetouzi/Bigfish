# -*- coding: utf-8 -*-
"""
获取mysql的连接
"""
import pymysql


def get_connection():
    return pymysql.connect(host='115.29.54.208', user='xinger', passwd='ShZh_forex_4', db='strategy', charset='utf8',
                           use_unicode=True)


conn = get_connection()
