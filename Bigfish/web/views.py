import tornado.web


class BaseHandler(tornado.web.RequestHandler):

    def __init__(self, *argc, **argkw):
        super(BaseHandler, self).__init__(*argc, **argkw)

    def post(self):
        print(self.get_arguments("name"))
        print(self.get_body_arguments("name"))
        # self.write("json")
        self.finish()
