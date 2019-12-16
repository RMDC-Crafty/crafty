import os
import threading

from app.classes.helpers import helpers

from pyftpdlib.servers import FTPServer
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import TLS_FTPHandler


helper = helpers()

class ftp_server():

    def __init__(self, user, password, root_dir, port=2121):
        self.root_dir = root_dir
        self.user = user
        self.password = password
        self.port = port
        self.server = None
        self.server_thread = None


    def ftp_serve(self):
        authorizer = DummyAuthorizer()
        authorizer.add_user(self.user, self.password, self.root_dir, perm='elradfmwMT')
        handler = TLS_FTPHandler

        crafty_root = os.path.abspath(helper.crafty_root)
        certfile = os.path.join(crafty_root, 'app', 'web', 'certs', 'ftpcert.pem')

        handler.certfile = certfile
        handler.authorizer = authorizer
        self.server = FTPServer(('', self.port), handler)
        self.server.serve_forever()

    def run_threaded_ftp_server(self):
        self.server_thread = threading.Thread(target=self.ftp_serve, daemon=True)
        self.server_thread.start()

    def stop_threaded_ftp_server(self):
        self.server.close()
        self.server_thread.join()

