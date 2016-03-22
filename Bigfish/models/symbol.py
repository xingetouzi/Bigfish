# -*- coding:utf-8 -*-
import os

import pandas

__all__ = ['Symbol', 'Forex']


class Symbol:
    """
    交易种类对象
    """
    __all = {}

    # XXX 已经移动到symbol_manage中
    """
    @classmethod
    def get_all_symbols(cls):
        # TODO 真正的获取symbol，拟定从数据库中获取
        # TODO 资产的其他信息，如滑点、手续费等信息
        # 将以json的形式存于文件或数据库中
        if len(cls.__all) == 0:
            with sqlite3.connect(_DBPATH) as conn:
                cur = conn.cursor()
                cur.execute("select code,name from symbol;")
                for item in cur.fetchall():
                    cls.__all[item[0]] = Symbol(*item)
        return cls.__all
    """

    def __init__(self, code):
        super(Symbol, self).__init__()
        self.code = code
        self.en_name = None  # 交易品种英文名称
        self.zh_name = None  # 交易品种中午名称
        self.tw_name = None  # 交易品种繁体中文名称
        self.margin_rate = 0  # 交易品种保证金比例
        self.commission = 0  # 交易品种每手手续费
        self.lot_size = 1  # 交易品种一手的合约数
        self.lever = 1  # 交易杠杆
        self.point = None
        self._big_point_value = 0

    def __str__(self):
        return "en_name=%s, zh_name=%s, 'tw_name=%s" % (self.en_name, self.zh_name, self.tw_name)

    def big_point_value(self, **kwargs):  # 整点价值
        return self._big_point_value

    def lot_value(self, point, lot=1, commission=None, slippage=0, **kwargs):
        """
        根据点值计算lot手合约的价值, 传入价差可以计算盈亏
        :param point: 点值
        :param lot: 手数
        :param commission: 是否计算手续费
        :param slippage: 滑点
        :param kwargs: 其他参数
        :return: lot手合约的价值
        """
        if not lot:
            return 0
        return (
                   self.lot_size * self.big_point_value(**kwargs) * (
                       point - slippage) - (commission if commission else self.commission)) * lot

    def caution_money(self, point, lot=1, **kwargs):
        # TODO 不知道手续费是最后在收益中结算还是占用了可用保证金
        return self.lot_value(point, lot, **kwargs) / self.lever


class Forex(Symbol):
    """
    外汇
    """
    PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'symbols.csv')
    ALL = pandas.read_csv(PATH, index_col=0)

    def __init__(self, code):
        super(Forex, self).__init__(code)
        self.lot_size = 100000
        self.en_name = self.code
        self.zh_name = self.ALL['zh_name'][self.code]
        self.point = self.ALL['point'][self.code]

    def big_point_value(self, base_price=1, **kwargs):
        return base_price
