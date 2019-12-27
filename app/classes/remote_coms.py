import time
from app.classes.models import *
from app.classes.ftp import ftp_svr_object

class remote_commands():

    def __init__(self, mc_server_obj, tornado_obj):
        self.mc_server_obj = mc_server_obj
        self.tornado_obj = tornado_obj
        self.clear_all_commands()

    def clear_all_commands(self):
        logger.info("Clearing all Remote Commands")
        Remote.delete().execute()

    def start_watcher(self):
        logger.info("Starting Remote Command Processor Daemon")
        self.keep_processing = True
        self.watch_for_commands()

    def watch_for_commands(self):
        while True:
            command_instance = Remote.select().where(Remote.id == 1).exists()
            if command_instance:
                command = Remote.get().command
                logger.info("Remote Command:{} found - Executing".format(command))
                self.handle_command(command)
                self.clear_all_commands()

            time.sleep(1)

    def handle_command(self, command):
        if command == 'restart_web_server':
            self.tornado_obj.stop_web_server()
            time.sleep(1)
            self.tornado_obj.start_web_server(True)
            self.clear_all_commands()

        elif command == "reload_mc_settings":
            self.mc_server_obj.reload_settings()

        elif command == 'restart_mc_server':
            running = self.mc_server_obj.check_running()

            if running:
                try:
                    logger.info("Stopping MC Server")
                    self.mc_server_obj.stop_threaded_server()
                except Exception as e:
                    logger.error("Error reported: {}".format(e))
                    pass

                while True:
                    server_up = self.mc_server_obj.is_server_pingable()
                    if server_up:
                        logger.info("Server still pingable, waiting")
                        time.sleep(.5)
                    else:
                        logger.info("Servers Stopped")

                        break

                self.mc_server_obj.run_threaded_server()
            else:
                logger.info("Server not running - Starting Server")
                self.mc_server_obj.run_threaded_server()

        elif command == 'start_mc_server':
            running = self.mc_server_obj.check_running()

            if not running:
                logger.info("Starting MC Server")
                self.mc_server_obj.run_threaded_server()
                time.sleep(2)
                self.mc_server_obj.write_html_server_status()
            else:
                logger.info("Server Already Running - Skipping start of MC Server")

        elif command == 'stop_mc_server':
            running = self.mc_server_obj.check_running()

            if running:
                logger.info("Stopping MC Server")
                self.mc_server_obj.stop_threaded_server()
                time.sleep(2)
                self.mc_server_obj.write_html_server_status()
            else:
                logger.info("Server Not Running - Skipping stop of MC Server")

        elif command == 'update_server_jar':
            self.mc_server_obj.update_server_jar(False)

        elif command == 'revert_server_jar':
            self.mc_server_obj.revert_updated_server_jar(False)

        elif command == "exit_crafty":
            logger.info("Sending Stop Command To Crafty")
            running = self.mc_server_obj.check_running()

            if running:
                logger.info("Stopping MC Server")
                self.mc_server_obj.stop_threaded_server()

            if ftp_svr_object.check_running():
                ftp_svr_object.stop_threaded_ftp_server()

            logger.info("***** Crafty Stopped ***** \n")
            # sys.exit(0)

            os._exit(0)

        elif command == 'start_ftp':
            logger.info("Starting FTP Server")
            ftp_svr_object.run_threaded_ftp_server()

        elif command == 'stop_ftp':
            ftp_svr_object.stop_threaded_ftp_server()