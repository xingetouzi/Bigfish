# -*- coding: utf-8 -*-


class User(object):
    def __init__(self, user_id, username=None):
        super(User, self).__init__()
        self.user_id = user_id
        self.username = username


class Code(object):
    def __init__(self, name, code_type=1, content=None):
        """
        初始化代码对象
        :param name:名称
        :param code_type:代码类型,1表示为策略,2表示为函数
        :param content:代码内容
        :return:
        """
        super(Code, self).__init__()
        self.name = name
        self.content = content
        self.code_type = code_type


