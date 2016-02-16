# -*- coding:utf-8 -*-
base = 100000 # 设置起始资金

def init(): # init函数将在策略被加载时执行，进行一些初始化的工作
    pass

# 每一个不以init为名的函数都将别视为一个信号，信号在每根K线的数据到来时都会被执行
def handle(slowlength=20, fastlength=10, lots=100):  # 函数签名的中只支持带默认值的参数(即关键字参数)，可以对此处的参数使用我们平台的参数优化功能
    pass