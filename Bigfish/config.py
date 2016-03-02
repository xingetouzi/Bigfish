# -*- coding: utf-8 -*-

"""
项目配置文件
"""
__all__ = ['MEMORY_DEBUG', 'DATABASE', 'ASYNC', 'MODULES_IMPORT']

MEMORY_DEBUG = False  # 是否开启内存检测模式
DATABASE = 'mysql'
ASYNC = False  # 数据拉取方式
MODULES_IMPORT = ['time']  # 允许在策略代码中导入的模块列表
