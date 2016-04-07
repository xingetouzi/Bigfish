import tornado
from Bigfish.web.views import *
from tornado.web import HTTPError
from Bigfish.web.session import SessionManager


class Application(tornado.web.Application):
    def __init__(self):
        settings = dict(
            session_timeout=60,
            # store_options={
            #     'redis_host': 'localhost',
            #     'redis_port': 6379,
            #     'redis_pass': 'Xinger520',
            # },
        )
        handlers = [
            (r"/", MainHandler),
            (r"", MainHandler),
            (r"/login", LoginHandler)
        ]
        tornado.web.Application.__init__(self, handlers, **settings)
        self.session_manager = SessionManager(settings["session_secret"], settings["session_timeout"])


if __name__ == "__main__":
    app = Application()
    app.listen(8000)
    print("starting...")
    tornado.ioloop.IOLoop.current().start()
    print("start success...")