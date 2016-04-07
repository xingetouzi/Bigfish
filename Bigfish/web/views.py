import tornado.web
from Bigfish.web.session import Session


def login_required(f):
    def _wrapper(self, *args, **kwargs):
        print(self.get_current_user())
        logged = self.get_current_user()
        if logged is None:
            self.write('no login')
            self.finish()
        else:
            ret = f(self,*args, **kwargs)
    return _wrapper


class BaseHandler(tornado.web.RequestHandler):

    def __init__(self, *argc, **argkw):
        super(BaseHandler, self).__init__(*argc, **argkw)
        self.session = Session(self.application.session_manager, self)

    def get_current_user(self):
        return self.session.get("user_name")


class MainHandler(BaseHandler):

    @login_required
    def get(self):
        username = self.get_current_user()
        # print('start..')
        # print(username)
        # print(self.session['nima'])
        if username is None:
            self.write('nima')
        else:
            self.write("What's up, " + username + "?")


class LoginHandler(BaseHandler):
    def get(self):
        # print(self.get_argument("name"))
        self.session["user_name"] = self.get_argument("name")
        self.session["nima"] = 'xiaorui.cc'
        self.session.save()
        self.write('你的session已经欧了')
