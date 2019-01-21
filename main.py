#coding=utf-8
import time
import base64
from uuid import uuid4
from datetime import datetime
from random  import randint
from pycket.session import SessionMixin
import tornado.httpserver
import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.escape
from tornado.options import define, options
from models.connect import session
from models.User import User
from sqlalchemy import and_, or_,text,func ,extract,not_,exists


#定义一个默认的端口
define("port", default=9000, help="run port ", type=int)
define("t",  default=False, help="creat tables", type=bool)
define("a",  default=False, help="creat tables", type=bool)

class AuthError(Exception):
    def __init__(self, msg):
        super(AuthError, self).__init__(msg)


class BaseHandler(tornado.web.RequestHandler, SessionMixin):
    def initialize(self):
        self.db=session

    def get_current_user(self):
        if self.session.get("user_name"):
            return User.by_name(self.session.get("user_name"))
        else:
            return None

    def on_finish(self):
        self.db.close()


class BaseWebSocketHandler(tornado.websocket.WebSocketHandler, SessionMixin):
    def open(self):
        pass

    def on_message(self, message):
        pass

    def on_close(self):
        pass

    def get_current_user(self):
        if self.session.get("user_name"):
            return User.by_name(self.session.get("user_name"))
        else:
            return None


class MessageWSHandler(BaseWebSocketHandler):
    users = set()
    cache = []
    cache_size = 5

    def get_compression_options(self):
        """
        重写以返回连接的压缩选项。
        如果该方法没有返回（默认值），压缩将
        被禁用。如果它返回一个字典（甚至一个空的），它
        将启用。本词典的内容可以用来
        控制压缩的内存和CPU使用率，
        但目前没有这样的选择。
        """
        return {}

    def open(self):
        """有新的websocket链接时调用这个函数"""
        MessageWSHandler.users.add(self)
        print('-------------------open-----------------')

    def on_close(self):
        """当websocket链接关闭时调用这个函数"""
        print('-------------------on_close-----------------')
        if self in MessageWSHandler.users:
            MessageWSHandler.users.remove(self)
        print(MessageWSHandler.users)

    def on_message(self, message):
        """链接建立完成后当有浏览器发送过来请求后调用这个函数"""
        print('-------------------on_message-----------------')
        msg = tornado.escape.json_decode(message)
        msg.update({
            "useravatar":self.current_user.avatar,
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        print(msg)
        MessageWSHandler.update_cache(msg)
        MessageWSHandler.send_updates(msg, self)

    @classmethod
    def update_cache(cls, message):
        """向缓存列表中插入消息"""
        cls.cache.insert(0, message)
        if len(cls.cache) > cls.cache_size:
            cls.cache = cls.cache[:cls.cache_size]

    @classmethod
    def send_updates(cls, message, self):
        """发送消息，在这里调用write_message发送给自己消息"""
        for user in cls.users:
            if user != self:
                try:
                    #向与当前MessageWebSocketHandler对像链接的浏览器发送消息
                    user.write_message(message)
                    #关闭当前的链接，code 和 reason 通知客户端链接关闭的原因
                    #user.close()
                except Exception as e:
                   print(e)




class MessageHandler(BaseHandler):
    def get(self):
        """返回消息页面，这个页面包含发送websocket链接的代码"""
        self.render("websocket.html",
                    messages=MessageWSHandler.cache,
                    username=self.current_user
                    )


class IndexHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        #为用户添加头像
        # user = self.db.query(User).filter(User.id==1).first()
        # user.avatar = open("static/images/avatar11.jpg", "rb").read()
        # self.db.add(user)
        # self.db.commit()
        # user = self.db.query(User1).filter(User1.id == 2).first()
        # user.avatar = open("static/images/headpictrue.jpg", "rb").read()
        # self.db.add(user)
        # self.db.commit()
        user = self.db.query(User).filter(User.id == 1).first()

        user.avatar = open("static/images/headpictrue.jpg", "rb").read()

        self.db.add(user)
        self.db.commit()
        print('-' * 80)
        users = User.all()
        self.render(u"sqlalchemy.html",
                    currentuser=self.current_user,
                    users=users
                    )

class LoginHandler(BaseHandler):
    def get(self):
        self.render("login.html", nextname=self.get_argument("next", "/"))

    def post(self):
        user = User.by_name(self.get_argument('name', ''))
        password = self.get_argument("password", "")
        if not user.locked:
            if user and user.auth_password(password):
                self.success_login(user)
                if user.loginnum == 1:
                    self.write('newuser.html')
                else:
                    self.redirect(self.get_argument("aaa", "/"))
            else:
                self.write("登录失败")
        else:
            self.write("此用户已经被锁定，请联系管理员")

    def success_login(self, user):
        print(user.username)
        user.last_login = datetime.now()
        user.loginnum += 1
        self.db.add(user)
        self.db.commit()
        self.session.set('user_name', user.username)


class RegistHandler(BaseHandler):
    def get(self):
        if self.current_user:
            self.redirect('/')
        else:
            self.render("regist.html", error=None)

    def post(self):
        if self._check_argument():
            try:
                self._create_user()
                self.redirect('/login')
            except AuthError as e:
                self.render("regist.html", error=e)
            except Exception as e:
                self.render("regist.html", error=e)
        else:
            self.render("regist.html", error="input error")


    def _check_argument(self):
        name = self.get_argument("name", "")
        password = self.get_argument("password", "")
        if len(name) < 10 and len(password) < 10:
            return True
        else:
            return False


    def _create_user(self):
        if User.by_name(self.get_argument('name', '')):
            raise AuthError("name is registered")
        if self.get_argument('password1', '') != self.get_argument('password2', ''):
            raise AuthError("Password error")
        user = User()
        user.username = self.get_argument('name', '')
        user.password = self.get_argument('password1', '')
        self.db.add(user)
        self.db.commit()

class ModifyNameHandler(BaseHandler):

    def get(self):
        user = User.by_uuid(self.get_argument('uuid', ''))
        self.db.delete(user)
        self.db.commit()
        self.redirect('/')


    def post(self):
        user = User.by_uuid(self.get_argument('uuid', ''))
        delete = self.get_argument('delete', '')
        if delete == 'delete':
            self.db.delete(user)
            self.db.commit()
            self.redirect('/')
        elif user:
            user.username=self.get_argument('username', '')
            self.db.add(user)
            self.db.commit()
            self.redirect('/')
        else:
            self.write('error no')


if __name__ == "__main__":
    options.parse_command_line()
    if options.t:
        creat_tables.run()
    if options.a:
        print('你好请使用我们的系统...')

    app = tornado.web.Application(
        handlers=[
            (r'/', IndexHandler),
            (r'/login', LoginHandler),
            (r'/regist', RegistHandler),
            (r'/modifyname', ModifyNameHandler),
            (r'/messagewebsocket', MessageWSHandler),
            (r'/message', MessageHandler)
        ],
        template_path='templates',
        static_path='static',
        debug=True,
        cookie_secret='aaaa',
        login_url='/login',
        xsrf_cookies=True,
         # pycket的配置信息
        pycket={
            'engine': 'redis',  # 设置存储器类型
            'storage': {
                'host': '127.0.0.1',
                'port': 6379,
                'db_sessions': 5,
                'db_notifications': 11,
                'max_connections': 2 ** 31,
            },
            'cookies': {
                'expires_days': 30,  # 设置过期时间
                'max_age': 5000,
            },
        },
    )

    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    print('start server...')
    tornado.ioloop.IOLoop.instance().start()