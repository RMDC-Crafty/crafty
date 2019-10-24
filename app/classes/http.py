import os
import json
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


class MessageHandler(tornado.web.RequestHandler):
    web_root = os.path.join(os.path.curdir, 'app', 'web')

    def get(self):

        self.render(
            "public/index.html",
        )

class webserver():

    def log_function(self,handler):

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
        web_root = os.path.join(os.path.curdir, 'app', 'web')

        logging.info("Starting Tornado HTTP Server on port {}".format(port_number))
        Console.info("Starting Tornado HTTP Server on port {}".format(port_number))
        asyncio.set_event_loop(asyncio.new_event_loop())

        tornado.template.Loader('.')


        handlers = [
            (r'/', MessageHandler)
        ]

        app = tornado.web.Application(
            handlers,
            template_path=os.path.join(web_root, 'templates'),
            static_path=os.path.join(web_root, 'static'),
            debug=True,
            cookie_secret='wqkbnksbicg92ujbnf',
            xsrf_cookies=True,
            autoreload=False,
            log_function = self.log_function
        )
        app.listen(port_number)
        tornado.ioloop.IOLoop.instance().start()

    def start_web_server(self):
        thread = threading.Thread(target=self.run_tornado, daemon=True)
        thread.start()


