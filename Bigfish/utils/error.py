# -*- coding: utf-8 -*-
"""
Created on Tue Dec 15 11:37:18 2015

@author: BurdenBear
"""
import re
import traceback


class SlaverThreadError(RuntimeError):
    """子线程中出现的错误，保留子线程的堆栈信息"""

    def __init__(self, exc_type, exc_value, exc_traceback):
        """
        :param exc_type:
        :param exc_value:
        :param exc_traceback:
        """
        super().__init__(exc_type, exc_value, exc_traceback)
        self.exc_type = exc_type
        self.exc_value = exc_value
        self.exc_traceback = exc_traceback

    def get_exc(self):
        return (self.exc_type, self.exc_value, self.exc_traceback)


def is_user_file(string, limit=r'\A\[.+\]\Z') -> bool:
    """判断是否是用户生成的文件，用于输出友好的错误日志
    :param string:
    :param limit:
    :return:
    :rtype: str
    """
    pattern = re.compile(limit)
    return pattern.match(string) is not None


def get_user_friendly_traceback(exc_type, exc_value, exc_traceback) -> str:
    """
    :param exc_type:
    :param exc_value:
    :param exc_traceback:
    :return:
    :rtype: str
    """
    if exc_type == SlaverThreadError:
        return get_user_friendly_traceback(*exc_value.get_exc())
    tb_message = traceback.format_list(filter(lambda x: is_user_file(str(x[0])), traceback.extract_tb(exc_traceback)))
    if not tb_message:
        tb_message = traceback.format_list(traceback.extract_tb(exc_traceback))
    format_e = traceback.format_exception_only(exc_type, exc_value)
    tb_message.append(''.join(format_e))
    return tb_message
