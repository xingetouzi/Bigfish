# /usr/bin/python
# coding: utf-8
import uuid
import hmac
import ujson
import hashlib
import redis
from Bigfish.data.cache import RedisPool


# 继承 SessionData 类
class Session(dict):
    # 初始化，绑定 session_manager 和 tornado 的对应 handler
    def __init__(self, session_manager, request_handler):
        self.session_manager = session_manager
        self.request_handler = request_handler

    # 定义 save 方法，用于 session 修改后的保存，实际调用 session_manager 的 set 方法
    def save(self):
        self.session_manager.set(self.request_handler, self)


class SessionManager(object):
    def __init__(self, secret, session_timeout):
        self.secret = secret
        self.session_timeout = session_timeout
        try:
            self.pool = RedisPool()
            self.redis = redis.Redis(connection_pool=self.pool.pool)
        except Exception as e:
            print(e)

    def set(self, request_handler, session):
        request_handler.set_secure_cookie("session_id", session.session_id)
        session_data = ujson.dumps(dict(session.items()))
        self.redis.setex(session.session_id, session_data, self.session_timeout)

    def _generate_id(self):
        pass



class InvalidSessionException(Exception):
    pass
