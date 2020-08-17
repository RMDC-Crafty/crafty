import os
import sys
import json
import time
import secrets
import asyncio
import logging
import schedule
import threading
import tornado.web
import tornado.ioloop
import tornado.log
import tornado.template
import tornado.escape
import tornado.locale
import tornado.httpserver
from pathlib import Path

from app.classes.console import console
from app.classes.models import Crafty_settings, Webserver
from app.classes.ftp import ftp_svr_object
from app.classes.minecraft_server import mc_server
from app.classes.helpers import helper
from app.classes.web_sessions import web_session
from app.classes.multiserv import multi
from app.classes.handlers.base_handler import BaseHandler
from app.classes.handlers.default404 import My404Handler
from app.classes.handlers.public_handler import PublicHandler
from app.classes.handlers.admin_handler import AdminHandler
from app.classes.handlers.ajax_handler import AjaxHandler
from app.classes.handlers.setup_handler import SetupHandler
from app.classes.handlers.download_handler import DownloadHandler

import app.classes.api as api_routes

logger = logging.getLogger(__name__)


class webserver():

    def __init__(self, mc_server):
        self.mc_server = mc_server
        self.ioloop = None
        self.HTTPServer = None

    def _asyncio_patch(self):
        """
        As of Python 3.8 (on Windows), the asyncio default event handler has changed to "proactor",
        where tornado expects the "selector" handler.

        This function checks if the platform is windows and changes the event handler to suit.

        (Taken from https://github.com/mkdocs/mkdocs/commit/cf2b136d4257787c0de51eba2d9e30ded5245b31)
        """
        logger.debug("Checking if asyncio patch is required")
        if sys.platform.startswith("win") and sys.version_info >= (3, 8):
            import asyncio
            try:
                from asyncio import WindowsSelectorEventLoopPolicy
            except ImportError:
                logger.debug("asyncio patch isn't required")
                pass  # Can't assign a policy which doesn't exist.
            else:
                if not isinstance(asyncio.get_event_loop_policy(), WindowsSelectorEventLoopPolicy):
                    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
                    logger.debug("Applied asyncio patch")

    def log_function(self, handler):

        info = {
            'Status_Code': handler.get_status(),
            'Method': handler.request.method,
            'URL': handler.request.uri,
            'Remote_IP': handler.request.remote_ip,
            'Elapsed_Time': '%.2fms' % (handler.request.request_time() * 1000)
        }
        tornado.log.access_log.info(json.dumps(info, indent=4))

    def run_tornado(self, silent=False):

        # First, patch asyncio if needed
        self._asyncio_patch()

        # let's verify we have an SSL cert
        helper.create_self_signed_cert()

        websettings = Webserver.get()

        crafty_settings = Crafty_settings.get()
        lang = crafty_settings.language

        port_number = websettings.port_number
        web_root = helper.get_web_root_path()

        logger.info("Starting Tornado HTTPS Server on port {}".format(port_number))

        if not silent:
            console.info("Starting Tornado HTTPS Server on port {}".format(port_number))
            console.info("https://{}:{} is up and ready for connection:".format(helper.get_local_ip(), port_number))

        asyncio.set_event_loop(asyncio.new_event_loop())

        tornado.template.Loader('.')

        tornado.locale.set_default_locale(lang)

        ip = helper.get_public_ip()

        if not silent:
            if ip:
                console.info("Your public IP is: {}".format(ip))

            else:
                console.warning("Unable to find your public IP\nThe service might be down, or your internet is down.")

        handlers = [
            (r'/', PublicHandler),
            (r'/([a-zA-Z]+)', PublicHandler),
            (r'/admin/downloadbackup', DownloadHandler),
            (r'/admin/(.*)', AdminHandler, dict(mcserver=self.mc_server)),
            (r'/ajax/(.*)', AjaxHandler, dict(mcserver=self.mc_server)),
            (r'/setup/(.*)', SetupHandler, dict(mcserver=self.mc_server)),
            (r'/static(.*)', tornado.web.StaticFileHandler, {"path": '/'}),
            (r'/images(.*)', tornado.web.StaticFileHandler, {"path": "/images"}),

            # API routes
            (r'/api/v1/host_stats', api_routes.GetHostStats, dict(mcserver=self.mc_server)),
            (r'/api/v1/server_stats', api_routes.GetServerStats, dict(mcserver=self.mc_server)),

            # Server related
            (r'/api/v1/server/send_command', api_routes.SendCommand, dict(mcserver=self.mc_server)),
            (r'/api/v1/server/get_logs', api_routes.GetMCLogs, dict(mcserver=self.mc_server)),
            (r'/api/v1/server/search_logs', api_routes.SearchMCLogs, dict(mcserver=self.mc_server)),
            (r'/api/v1/server/force_backup', api_routes.ForceServerBackup, dict(mcserver=self.mc_server)),
            (r'/api/v1/server/start', api_routes.StartServer, dict(mcserver=self.mc_server)),
            (r'/api/v1/server/stop', api_routes.StopServer, dict(mcserver=self.mc_server)),
            (r'/api/v1/server/restart', api_routes.RestartServer, dict(mcserver=self.mc_server)),
            (r'/api/v1/list_servers', api_routes.ListServers, dict(mcserver=self.mc_server)),

            # Crafty related
            (r'/api/v1/crafty/add_user', api_routes.CreateUser),
            (r'/api/v1/crafty/del_user', api_routes.DeleteUser),
            (r'/api/v1/crafty/get_logs', api_routes.GetCraftyLogs),
            (r'/api/v1/crafty/search_logs', api_routes.SearchCraftyLogs)   
        ]

        cert_objects = {
            'certfile': os.path.join(web_root, 'certs', 'crafty.crt'),
            'keyfile': os.path.join(web_root, 'certs', 'crafty.key')
        }

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

        self.http_server = tornado.httpserver.HTTPServer(app, ssl_options=cert_objects)
        self.http_server.listen(port_number)
        tornado.locale.load_translations(os.path.join(web_root, 'translations'))
        self.ioloop = tornado.ioloop.IOLoop.instance()
        self.ioloop.start()

    def start_web_server(self, silent=False):
        thread = threading.Thread(target=self.run_tornado, args=(silent, ), daemon=True, name='tornado_thread')
        thread.start()

    def stop_web_server(self):
        logger.info("Shutting Down Tornado Web Server")
        ioloop = self.ioloop
        ioloop.stop()
        self.http_server.stop()
        logger.info("Tornado Server Stopped")


tornado_srv = webserver(mc_server)
