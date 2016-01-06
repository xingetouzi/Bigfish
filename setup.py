# -*- coding:utf-8 -*-

from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
import numpy as np

ext_modules = [
    Extension('Bigfish.utils.algos',
              sources=['Bigfish/utils/algos.pyx'],
              include_dirs=[np.get_include()]
             )
]

DISTNAME = 'bigfish'

setup(
        name='bigfish',
        cmdclass={'build_ext': build_ext},
        ext_modules=ext_modules,
        requires=['Cython', 'pandas', 'numpy', 'tushare'],
)
