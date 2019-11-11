import os
import json
import time
import asyncio
import logging
import schedule
import threading
import tornado.web
import tornado.ioloop
import tornado.log
import tornado.template
import tornado.escape
from playhouse.shortcuts import model_to_dict, dict_to_model

from app.classes.console import Console
from app.classes.helpers import helpers
from app.classes.models import *

console = Console()
helper = helpers()


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user", max_age_days=1)


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
            self.set_secure_cookie("user", tornado.escape.json_encode(user), expires_days=1)
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
        entered_user = self.get_argument('username')
        entered_password = self.get_argument('password')

        user_data = Users.get(Users.username == entered_user)
        if user_data:
            # if the login is good and the pass verified, we go to the dashboard
            login_result = helper.verify_pass(entered_password, user_data.password)
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
        context = {}

        if page == 'dashboard':
            template = "admin/dashboard.html"
            context = server_data

        elif page == 'change_password':
            template = "admin/change_pass.html"

        elif page == 'virtual_console':
            template = "admin/virt_console.html"

        elif page == "backups":
            template = "admin/backups.html"
            backup_path = os.path.join(self.mcserver.settings.server_path, 'crafty_backups')
            context = {'backup_path': backup_path, 'current_backups': self.mcserver.list_backups()}

        elif page == "schedules":
            template = "admin/schedules.html"



        elif page == 'config':
            saved = self.get_argument('saved', None)

            template = "admin/config.html"
            db_data = MC_settings.get()
            page_data = model_to_dict(db_data)
            page_data['saved'] = saved

            context = page_data

        elif page == 'downloadbackup':
            path = self.get_argument("file", None, True)

            if path is not None:
                file_name = os.path.basename(path)
                self.set_header('Content-Type', 'application/octet-stream')
                self.set_header('Content-Disposition', 'attachment; filename=' + file_name)

                with open(path, 'rb') as f:
                    while 1:
                        data = f.read(16384)  # or some other nice-sized chunk
                        if not data:
                            break
                        self.write(data)
                self.finish()
            self.redirect("/admin/backups")

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
                next_page = "/admin/dashboard"

            elif command == "server_start":
                self.mcserver.run_threaded_server()
                time.sleep(3)
                self.mcserver.write_html_server_status()
                next_page = "/admin/dashboard"

            elif command == "server_restart":
                self.mcserver.stop_threaded_server()
                time.sleep(3)
                self.mcserver.run_threaded_server()
                self.mcserver.write_html_server_status()
                next_page = "/admin/dashboard"

            elif command == "backup":
                backup_thread = threading.Thread(name='backup', target=self.mcserver.backup_worlds, daemon=False)
                backup_thread.start()
                next_page = '/admin/backups'

            self.redirect(next_page)

        elif page == 'get_logs':
            server_log = os.path.join(self.mcserver.server_path, 'logs', 'latest.log')
            data = helper.read_whole_file(server_log)

            errors = self.mcserver.search_for_errors()
            template = "admin/logs.html"
            context = {'log_data': data, 'errors': errors}

        else:
            # 404
            template = "public/404.html"
            context = {}

        self.render(
            template,
            data=context
        )

    @tornado.web.authenticated
    def post(self, page):

        if page == 'change_password':
            entered_password = self.get_argument('password')
            encoded_pass = helper.encode_pass(entered_password)

            q = Users.update({Users.password: encoded_pass}).where(Users.username == "Admin")
            q.execute()

            self.clear_cookie("user")
            self.redirect("/")

        elif page == 'config':

            q = MC_settings.update({
                MC_settings.server_path: self.get_argument('server_path'),
                MC_settings.server_jar: self.get_argument('server_jar'),
                MC_settings.memory_max: self.get_argument('memory_max'),
                MC_settings.memory_min: self.get_argument('memory_min'),
                MC_settings.additional_args: self.get_argument('additional_args'),
                MC_settings.auto_start_server: int(self.get_argument('auto_start_server')),
                MC_settings.auto_start_delay: self.get_argument('auto_start_delay'),
            }).where(MC_settings.id == 1)

            q.execute()
            self.redirect("/admin/config?saved=True")


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

    def initialize(self, mcserver):
        self.mcserver = mcserver

    @tornado.web.authenticated
    def get(self, page):

        if page == 'server_log':

            server_log = os.path.join(self.mcserver.server_path, 'logs', 'latest.log')
            data = helper.tail_file(server_log, 40)

            for d in data:
                self.write(d.encode("utf-8"))

    def post(self, page):

        if page == "send_command":
            # posted_data = tornado.escape.json_decode(self.request.body)
            command = self.get_body_argument('command', default=None, strip=True)
            if command:
                if self.mcserver.check_running:
                    self.mcserver.send_command(command)


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

        websettings = Webserver.get()

        port_number = websettings.port_number
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
            debug=True,
            cookie_secret=helper.random_string_generator(20),
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


