import os
import json
import time
import asyncio
import logging
import threading
import tornado.web
import tornado.ioloop
import tornado.log
import tornado.template
import tornado.escape

from app.classes.console import Console
from app.classes.helpers import helpers
from app.classes.db import db_wrapper

console = Console()
helper = helpers()




class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")


class My404Handler(BaseHandler):
    # Override prepare() instead of get() to cover all possible HTTP methods.
    def prepare(self):
        self.set_status(404)
        self.render("public/404.html")


class PublicHandler(BaseHandler):

    def initialize(self, mcserver):
        self.mcserver = mcserver

    def set_current_user(self, user):
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user))
        else:
            self.clear_cookie("user")

    def get(self, page=None):

        server_data = self.get_server_data()

        template = "public/login.html"
        context = server_data
        context['login'] = None

        self.render(
            template,
            data=context
        )


    def post(self):
        db = db_wrapper(helper.get_db_path())

        entered_user = self.get_argument('username')
        entered_password = self.get_argument('password')

        user_data = db.get_user_data(entered_user)
        if user_data:
            # if the login is good and the pass verified, we go to the dashboard
            login_result = helper.verify_pass(entered_password, user_data['pass'])
            if login_result:
                self.set_current_user(entered_user)
                self.redirect(self.get_argument("next", u"/admin/dashboard"))

            else:
                server_data = self.get_server_data()
                template = "public/login.html"
                context = server_data
                context['login'] = False

        else:
            server_data = self.get_server_data()

            template = "public/login.html"
            context = server_data
            context['login'] = False

        self.render(
            template,
            data=context
        )


    def get_server_data(self):
        server_file = os.path.join( helper.get_web_temp_path(), "server_data.json")

        if helper.check_file_exists(server_file):
            with open(server_file, 'r') as f:
                server_data = json.load(f)
            return server_data
        else:
            logging.warning("Unable to find server_data file for dashboard: {}".format(server_file))
            return False


class AdminHandler(BaseHandler):

    def initialize(self, mcserver):
        self.mcserver = mcserver

    @tornado.web.authenticated
    def get(self, page):

        server_data = self.get_server_data()

        if page == 'dashboard':
            template = "admin/dashboard.html"
            context = server_data


        elif page == "server_control":

            template = "admin/server_control.html"
            logfile = helper.get_crafty_log_file()
            context = server_data

        elif page == 'commands':
            command = self.get_argument("command", None, True)
            if command == "server_stop":
                self.mcserver.stop_threaded_server()
                time.sleep(3)
                self.mcserver.write_html_server_status()

            elif command == "server_start":
                self.mcserver.run_threaded_server()
                time.sleep(3)
                self.mcserver.write_html_server_status()

            self.redirect('/admin/dashboard')

        else:
            # 404
            template = "public/404.html"
            context = {}


        self.render(
            template,
            data=context
        )

    def get_server_data(self):
        server_file = os.path.join( helper.get_web_temp_path(), "server_data.json")

        if helper.check_file_exists(server_file):
            with open(server_file, 'r') as f:
                server_data = json.load(f)
            return server_data
        else:
            logging.warning("Unable to find server_data file for dashboard: {}".format(server_file))
            return False


class AjaxHandler(BaseHandler):

    def get(self, page):
        self.render(
            "admin/dashboard.html",
        )


class webserver():

    def __init__(self, mc_server):
        self.mc_server = mc_server

    def log_function(self, handler):

        info = {
            'Status_Code': handler.get_status(),
            'Method': handler.request.method,
            'URL': handler.request.uri,
            'Remote_IP': handler.request.remote_ip,
            'Elapsed_Time': '%.2fms' % (handler.request.request_time() * 1000)
        }
        tornado.log.access_log.info(json.dumps(info, indent=4))


    def run_tornado(self):

        # our database wrapper
        db = db_wrapper(helper.get_db_path())

        sql = "SELECT port_number FROM webserver"
        port = db.run_sql_first_row(sql)
        port_number = port['port_number']
        web_root = helper.get_web_root_path()

        logging.info("Starting Tornado HTTP Server on port {}".format(port_number))
        Console.info("Starting Tornado HTTP Server on port {}".format(port_number))
        asyncio.set_event_loop(asyncio.new_event_loop())

        tornado.template.Loader('.')

        ip = helper.get_public_ip()

        if ip:
            Console.info("Your public IP is: {}".format(ip))
        else:
            Console.warning("Unable to find your public IP\nThe service might be down, or your internet is down.")

        handlers = [
            (r'/', PublicHandler, dict(mcserver=self.mc_server)),
            (r'/([a-zA-Z]+)', PublicHandler, dict(mcserver=self.mc_server)),
            (r'/admin/(.*)', AdminHandler, dict(mcserver=self.mc_server)),
            (r'/ajax/(.*)', AjaxHandler, dict(mcserver=self.mc_server)),
            (r'/static(.*)', tornado.web.StaticFileHandler, {"path": '/'}),
            (r'/images(.*)', tornado.web.StaticFileHandler, {"path": "/images"})
        ]

        app = tornado.web.Application(
            handlers,
            template_path=os.path.join(web_root, 'templates'),
            static_path=os.path.join(web_root, 'static'),
            debug=False,
            cookie_secret='wqkbnksbicg92ujbnf',
            xsrf_cookies=True,
            autoreload=False,
            log_function=self.log_function,
            login_url="/",
            default_handler_class=My404Handler

        )
        app.listen(port_number)
        tornado.ioloop.IOLoop.instance().start()

    def start_web_server(self):
        thread = threading.Thread(target=self.run_tornado, daemon=True)
        thread.start()


