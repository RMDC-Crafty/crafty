import time
from app.classes.models import *
from app.classes.ftp import ftp_svr_object
from app.classes.multiserv import multi

logger = logging.getLogger(__name__)

class remote_commands():

    def __init__(self, tornado_obj):
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
                entry = Remote.get_by_id(1)
                command_data = model_to_dict(entry)
                command = command_data['command']
                server_id = command_data['server_id']
                source = command_data['command_source']

                server_data = MC_settings.get_by_id(server_id)
                server_name = server_data.server_name

                logger.info("Remote Command \"%s\" found for server \"%s\" from source %s. Executing!", command, server_name, source)

                self.handle_command(command, server_id)
                self.clear_all_commands()

            time.sleep(1)

    def handle_command(self, command, server_id):
        srv_obj = multi.get_server_obj(server_id)
        running = srv_obj.check_running()
        server_name = srv_obj.get_mc_server_name()

        if command == 'restart_web_server':
            self.tornado_obj.stop_web_server()
            time.sleep(1)
            self.tornado_obj.start_web_server(True)
            self.clear_all_commands()

        elif command == "reload_mc_settings":
            any_srv_obj = multi.get_first_server_object()
            any_srv_obj.reload_settings()

        elif command == 'restart_mc_server':
            if running:
                try:
                    logger.info("Stopping MC Server")
                    srv_obj.stop_threaded_server()

                except:
                    logger.exception("Unable to stop server %s. Traceback: ", server_name)

                while True:
                    server_up = srv_obj.is_server_pingable()
                    if server_up:
                        logger.info("%s still pingable, waiting...", server_name)
                        time.sleep(.5)
                    else:
                        logger.info("Server %s has stopped", server_name)
                        break

                srv_obj.run_threaded_server()
            else:
                logger.info("%s not running, starting it now", server_name)
                srv_obj.run_threaded_server()

        elif command == 'start_mc_server':
            srv_obj.run_threaded_server()
            time.sleep(2)
            multi.do_stats_for_servers()

        elif command == 'stop_mc_server':

            if running:
                logger.info("Stopping MC server %s", server_name)
                srv_obj.stop_threaded_server()
                time.sleep(2)
                multi.do_stats_for_servers()
            else:
                logger.info("Stop halted! Server %s is not running!", server_name)

        #elif command == 'update_server_jar':
            # srv_obj.update_server_jar(False)

        #elif command == 'revert_server_jar':
            # srv_obj.revert_updated_server_jar(False)

        elif command == "exit_crafty":
            logger.info("Sending Stop Command To Crafty")

            # stop the ftp server...
            if ftp_svr_object.check_running():
                ftp_svr_object.stop_threaded_ftp_server()

            # kill all mc servers gracefully
            multi.stop_all_servers()

            logger.info("***** Crafty Stopped ***** \n")

            os._exit(0)

        elif command == 'start_ftp':
            logger.info("Starting FTP Server")
            ftp_svr_object.run_threaded_ftp_server()

        elif command == 'stop_ftp':
            ftp_svr_object.stop_threaded_ftp_server()