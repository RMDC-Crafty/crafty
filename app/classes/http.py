import os
import json
import asyncio
import logging
import threading
import tornado.web
import tornado.ioloop

from app.classes.console import Console
from app.classes.helpers import helpers
from app.classes.db import db_wrapper

console = Console()
helper = helpers()


class MessageHandler(tornado.web.RequestHandler):
    web_root = os.path.join(os.path.curdir, 'app', 'web')

    def get(self):

        self.render(
            "index.html",
        )

class webserver():
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

        app = tornado.web.Application([(r'/', MessageHandler)], template_path=web_root)
        app.listen(port_number)
        tornado.ioloop.IOLoop.instance().start()

    def start_web_server(self):
        thread = threading.Thread(target=self.run_tornado, daemon=True)
        thread.start()


