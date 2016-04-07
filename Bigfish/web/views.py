import tornado.web


class BaseHandler(tornado.web.RequestHandler):

    def __init__(self, *argc, **argkw):
        super(BaseHandler, self).__init__(*argc, **argkw)

    def post(self):
        self.write("result")
