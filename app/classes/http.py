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

        self.clear_cookie("user")

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

        try:
            user_data = Users.get(Users.username == entered_user)

            if user_data:
                # if the login is good and the pass verified, we go to the dashboard
                login_result = helper.verify_pass(entered_password, user_data.password)
                if login_result:
                    self.set_current_user(entered_user)
                    self.redirect(self.get_argument("next", u"/admin/dashboard"))
        except:
            pass

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
        self.console = console


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
            saved = self.get_argument('saved', None)

            db_data = Schedules.select()

            template = "admin/schedules.html"
            context = {'db_data': db_data, 'saved': saved}

        elif page == "reloadschedules":

            logging.info("Reloading Scheduled Tasks")

            db_data = Schedules.select()

            # clear all user jobs
            schedule.clear('user')

            logging.info("Deleting all old tasks")

            logging.info("There are {} scheduled jobs to parse:".format(len(db_data)))

            # loop through the tasks in the db
            for task in db_data:
                helper.scheduler(task, self.mcserver)

            template = "admin/schedules.html"
            context = {'db_data': db_data, 'saved': None}

        elif page == "schedule_disable":
            schedule_id = self.get_argument('id', None)
            q = Schedules.update(enabled=0).where(Schedules.id == schedule_id)
            q.execute()

            self.redirect("/admin/reloadschedules")

        elif page == "schedule_enable":
            schedule_id = self.get_argument('id', None)
            q = Schedules.update(enabled=1).where(Schedules.id == schedule_id)
            q.execute()

            self.redirect("/admin/reloadschedules")

        elif page == 'config':
            saved = self.get_argument('saved', None)

            template = "admin/config.html"
            mc_data = MC_settings.get()
            crafty_data = Crafty_settings.get()

            page_data = {}
            page_data['saved'] = saved
            page_data['mc_settings'] = model_to_dict(mc_data)
            page_data['crafty_settings'] = model_to_dict(crafty_data)

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
                self.mcserver.restart_threaded_server()
                next_page = "/admin/dashboard"

            elif command == "backup":
                backup_thread = threading.Thread(name='backup', target=self.mcserver.backup_worlds, daemon=False)
                backup_thread.start()
                time.sleep(5)
                next_page = '/admin/backups'

            self.redirect(next_page)

        elif page == 'get_logs':
            server_log = os.path.join(self.mcserver.server_path, 'logs', 'latest.log')
            # data = helper.read_whole_file(server_log)
            data = helper.tail_file(server_log, 500)
            data.insert(0, "Lines trimmed to ~500 lines for speed sake \n ")

            crafty_data = helper.tail_file(helper.crafty_log_file, 100)
            crafty_data.insert(0, "Lines trimmed to ~100 lines for speed sake \n ")

            scheduler_data = helper.tail_file(os.path.join(helper.logs_dir, 'schedule.log'), 100)
            scheduler_data.insert(0, "Lines trimmed to ~100 lines for speed sake \n ")

            access_data = helper.tail_file(os.path.join(helper.logs_dir, 'tornado-access.log'), 100)
            access_data.insert(0, "Lines trimmed to ~100 lines for speed sake \n ")

            errors = self.mcserver.search_for_errors()
            template = "admin/logs.html"
            context = {'log_data': data, 'errors': errors, 'crafty_log': crafty_data,
                       'scheduler': scheduler_data, 'access': access_data}

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

        elif page == 'schedules':
            action = self.get_argument('action', '')
            interval = self.get_argument('interval', '')
            interval_type = self.get_argument('type', '')
            sched_time = self.get_argument('time', '')
            command = self.get_argument('command', '')
            comment = self.get_argument('comment', '')

            result = (
                Schedules.insert(
                    enabled=True,
                    action=action,
                    interval=interval,
                    interval_type=interval_type,
                    start_time=sched_time,
                    command=command,
                    comment=comment
                )
                .on_conflict('replace')
                .execute()
            )
            self.redirect("/admin/schedules?saved=True")


        elif page == 'config':

            config_type = self.get_argument('config_type')

            if config_type == 'mc_settings':

                q = MC_settings.update({
                    MC_settings.server_path: self.get_argument('server_path'),
                    MC_settings.server_jar: self.get_argument('server_jar'),
                    MC_settings.memory_max: self.get_argument('memory_max'),
                    MC_settings.memory_min: self.get_argument('memory_min'),
                    MC_settings.additional_args: self.get_argument('additional_args'),
                    MC_settings.pre_args: self.get_argument('pre_args'),
                    MC_settings.auto_start_server: int(self.get_argument('auto_start_server')),
                    MC_settings.auto_start_delay: self.get_argument('auto_start_delay'),
                }).where(MC_settings.id == 1)

                q.execute()

            elif config_type == 'crafty_settings':
                q = Crafty_settings.update({
                    Crafty_settings.history_interval: self.get_argument('historical_interval'),
                    Crafty_settings.history_max_age: self.get_argument('history_max_age'),
                }).where(Crafty_settings.id == 1)

                q.execute()

                # reload the history settings
                self.mcserver.reload_history_settings()

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

        if page == 'history':
            db_data = History.select()
            return_data = []
            for d in db_data:
                row_data = {
                    'time': d.time.strftime("%m/%d/%Y %H:%M:%S"),
                    'cpu': d.cpu,
                    'mem': d.memory,
                    'players': d.players
                }
                return_data.append(row_data)

            self.write(json.dumps(return_data))


    def post(self, page):

        if page == "send_command":
            # posted_data = tornado.escape.json_decode(self.request.body)
            command = self.get_body_argument('command', default=None, strip=True)
            if command:
                if self.mcserver.check_running:
                    self.mcserver.send_command(command)

        elif page == 'del_file':
            file_to_del = self.get_body_argument('file_name', default=None, strip=True)
            if file_to_del:
                helper.del_file(file_to_del)

        elif page == 'del_schedule':
            id_to_del = self.get_body_argument('id', default=None, strip=True)

            if id_to_del:
                logging.info("Got command to del schedule {}".format(id_to_del))
                q = Schedules.delete().where(Schedules.id == id_to_del)
                q.execute()

        elif page == 'search_logs':
            search_string = self.get_body_argument('search', default=None, strip=True)
            logfile = os.path.join(self.mcserver.server_path, 'logs', 'latest.log')
            data = helper.search_file(logfile, search_string)
            if data:
                temp_data = ""
                for d in data:
                    line = "Line Number: {} {}".format(d[0], d[1])
                    temp_data = "{}\n{}".format(temp_data, line)
                return_data = temp_data

            else:
                return_data = "Unable to find your string: {}".format(search_string)
            self.write(return_data)

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


