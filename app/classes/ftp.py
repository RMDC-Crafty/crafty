import os
import threading
import logging

from app.classes.helpers import helper

from app.classes.models import Ftp_Srv, MC_settings


from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import TLS_FTPHandler
from pyftpdlib.servers import ThreadedFTPServer

logger = logging.getLogger(__name__)


class ftp_server():

    def __init__(self):
        self.root_dir = None
        self.user = None
        self.password = None
        self.port = None
        self.server = None
        self.ftp_server_thread = None
        self.running = False
        self.last_error = None

    def get_root_dir(self):
        return self.root_dir

    def set_root_dir(self, full_path):
        self.root_dir = full_path

    def setup_ftp(self, server_id=1):
        ftp_settings = None
        mc_settings = None
        try:
            ftp_settings = Ftp_Srv.get_by_id(1)
            mc_settings = MC_settings.get_by_id(server_id)

        except Exception as e:
            logging.exception("Error Loading FTP. Traceback:")
            self.last_error = e
            return False

        pemfile = os.path.join(helper.crafty_root, "app", 'web', 'certs', 'crafty.pem')

        if not helper.check_file_exists(pemfile):
            helper.create_ftp_pem()

        if ftp_settings is not None and mc_settings is not None:

            self.user = ftp_settings.user
            self.password = ftp_settings.password
            self.port = ftp_settings.port
            self.root_dir = mc_settings.server_path

            logger.info("FTP server is now setup - Port: {}, Dir: {}".format(self.port, self.root_dir))

    def _ftp_serve(self, server_id=1):
        self.setup_ftp(server_id)

        authorizer = DummyAuthorizer()
        authorizer.add_user(self.user, self.password, self.root_dir, perm='elradfmwMT')
        handler = TLS_FTPHandler
        crafty_root = os.path.abspath(helper.crafty_root)
        certfile = os.path.join(crafty_root, 'app', 'web', 'certs', 'crafty.pem')

        handler.certfile = certfile
        handler.authorizer = authorizer
        self.server = ThreadedFTPServer(('0.0.0.0', self.port), handler)
        self.running = True
        self.server.serve_forever()

    def run_threaded_ftp_server(self, server_id=1):
        self.running = True
        logger.info("Ftp Server Started for server ID: {}".format(server_id))
        self.ftp_server_thread = threading.Thread(target=self._ftp_serve, args=[server_id], daemon=True)
        self.ftp_server_thread.start()

    def stop_threaded_ftp_server(self):
        self.running = False
        self.server.close_all()

    def check_running(self):
        return self.running


ftp_svr_object = ftp_server()
