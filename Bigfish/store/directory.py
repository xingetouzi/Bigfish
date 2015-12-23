# -*- coding: utf-8 -*-
import os


class UserDirectory(object):
    """用户目录管理,维护一个用户主目录,已经主目录下的两个子目录(函数目录,策略目录)"""
    def __init__(self, user):
        """
        :param user: 必须传入用户对象
        """
        super(UserDirectory, self).__init__()
        self.__user__ = user

    @classmethod
    def __get_dir__(cls, root, dir_name):
        """
        获取指定目录(文件夹)下指定名称的目录(文件夹),如果目录不存在则创建
        :param root:主目录
        :param dir_name:主目录下的需要获取的子目录
        :return:
        """
        new_dir = os.path.join(root, dir_name)
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)
        return new_dir

    def __get_root__(self):
        """
        获取策略代码存放路径
        :return: 策略代码存放的根目录
        """
        base_dir_name = "Bigfish"   # TODO 先写死, 以后肯定需要重构
        return self.__get_dir__(os.path.expanduser('~'), base_dir_name)

    def get_home(self, code=None):
        """
        得到用户主目录,如果传入了code对象,则返回该对象存放的主目录 #TODO 以后这里可以扩充支持分布式等等
        :param code: 代码对象
        """
        # 以user_id 作为用户的主目录
        if not code:
            return self.__get_dir__(self.__get_root__(), self.__user__.user_id)
        elif code.code_type == 1:
            return self.get_strategy_dir()
        else:
            return self.get_func_dir()

    def get_temp_dir(self):
        temp_dir_name = "temp"
        return self.__get_dir__(self.get_home(), temp_dir_name)

    def get_strategy_dir(self):
        """
        得到用户创建策略的存放目录
        :return:
        """
        strategy_dir_name = "library"
        return self.__get_dir__(self.get_home(), strategy_dir_name)

    def get_func_dir(self):
        """
        获取用户编写的函数存放目录
        :return:
        """
        func_dir_name = "functions"
        return self.__get_dir__(self.get_home(), func_dir_name)

    def get_func_list(self):
        """
        获取用户编写的函数列表
        """
        return os.listdir(self.get_func_dir())

    def get_strategy_list(self):
        """
        获取用户编写的策略列表
        """
        return os.listdir(self.get_strategy_dir())

    # def strategy_exists(self, strategy_name):
    #     """
    #     判断用户策略是否存在
    #     :param strategy_name:策略文件名称
    #     """
    #     return os.path.exists(os.path.join(self.get_strategy_dir(), strategy_name))
    #
    # def func_exists(self, func_name):
    #     """
    #     判断用户函数文件是否存在
    #     :param func_name:函数文件名称,可以一个函数一个文件,也可以多个函数一个文件
    #     """
    #     return os.path.exists(os.path.join(self.get_func_dir(), func_name))