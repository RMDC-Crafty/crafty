
import logging
import threading
import time

from app.classes.models import *
from app.classes.helpers import helpers

helper = helpers()

class remote_commands():

    def __init__(self, mc_server_obj, tornado_obj):
        self.keep_processing = True
        self.mc_server_obj = mc_server_obj
        self.tornado_obj = tornado_obj

    def stop_watching(self):
        self.keep_processing = False

    def start_watcher(self):
        logging.info("Starting Remote Command Processor Daemon")
        self.keep_processing = True
        self.watch_for_commands()

    def watch_for_commands(self):
        while True:
            # if we are to keep processing, we process
            if self.keep_processing:
                command_instance = Remote.select().where(Remote.id == 1).exists()
                if command_instance:
                    command = Remote.get_by_id(1).command
                    logging.info("Remote Command:{} found - Executing".format(command))
                    self.handle_command(command)
                    Remote.delete_by_id(1)
            # if we are to stop processing, we break out of this loop
            else:
                break
            time.sleep(1)

    def handle_command(self, command):
        if command == 'restart_web_server':
            self.tornado_obj.stop_web_server()
            time.sleep(1)
            self.tornado_obj.start_web_server(True)
