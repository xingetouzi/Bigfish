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


class Symbol(object):
    """
    交易种类对象
    """
    def __init__(self, en_name, zh_name):
        super(Symbol, self).__init__()
        self.en_name = en_name  # 交易品种英文名称
        self.zh_name = zh_name  # 交易品种中午名称

    def __str__(self):
        return "en_name=%s, zh_name=%s" % (self.en_name, self.zh_name)


