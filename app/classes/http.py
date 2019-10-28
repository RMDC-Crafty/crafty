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

from app.classes.console import Console
from app.classes.helpers import helpers
from app.classes.db import db_wrapper

console = Console()
helper = helpers()


class PublicHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('This is the public page: {}')


class AdminHandler(tornado.web.RequestHandler):

    def initialize(self, mcserver):
        self.mcserver = mcserver

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



class AjaxHandler(tornado.web.RequestHandler):

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
            (r'/', PublicHandler),
            (r'/admin/(.*)', AdminHandler, dict(mcserver=self.mc_server)),
            (r'/ajax/(.*)', AjaxHandler),
            (r'/static(.*)', tornado.web.StaticFileHandler, {"path": '/'}),
            (r'/images(.*)', tornado.web.StaticFileHandler, {"path": "/images"})
        ]

        app = tornado.web.Application(
            handlers,
            template_path=os.path.join(web_root, 'templates'),
            static_path=os.path.join(web_root, 'static'),
            debug=True,
            cookie_secret='wqkbnksbicg92ujbnf',
            xsrf_cookies=True,
            autoreload=False,
            log_function=self.log_function
        )
        app.listen(port_number)
        tornado.ioloop.IOLoop.instance().start()

    def start_web_server(self):
        thread = threading.Thread(target=self.run_tornado, daemon=True)
        thread.start()


