import os
import time
import logging

from app.classes.models import Remote, model_to_dict, MC_settings
from app.classes.ftp import ftp_svr_object
from app.classes.multiserv import multi
from app.classes.helpers import helper
from app.classes.webhookmgr import webhookmgr

logger = logging.getLogger(__name__)

# Had to define like this otherwise i would cause a circular import
commands = {
    "restart_web_server": "Restart Web Server",
    "restart_mc_server": "Restart Minecraft Server",
    "start_mc_server": "Start Minecraft Server",
    "stop_mc_server": "Stop Minecraft Server",
    "exit_crafty": "Stop Crafty",
    "start_ftp": "Start FTPS Server",
    "stop_ftp": "Stop FTPS Server"
}


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

    def list_commands(self):
        # just a quick helper to list commands. will improve in future
        return commands

    def handle_command(self, command, server_id):

        if command == "exit_crafty":
            logger.info("Sending Stop Command To Crafty")

            # stop the ftp server...
            if ftp_svr_object.check_running():
                ftp_svr_object.stop_threaded_ftp_server()

            # kill all mc servers gracefully
            try:
                multi.stop_all_servers()
            except:
                pass

            logger.info("***** Crafty Stopped ***** \n")
            webhookmgr.run_command_webhooks(command, webhookmgr.payload_formatter(200, {}, {"code": "CWEB_STOP"},
                                                                                  {"info": "Crafty is shutting down"}))
            os._exit(0)

        srv_obj = multi.get_server_obj(server_id)
        running = srv_obj.check_running()
        server_name = srv_obj.get_mc_server_name()

        if command == 'restart_web_server':
            self.tornado_obj.stop_web_server()
            time.sleep(1)
            self.tornado_obj.start_web_server(True)
            webhookmgr.run_command_webhooks(command, webhookmgr.payload_formatter(200, {}, {"code": "WEBSRV_RESTART"}, {"info": "Crafty Web Interface action has completed"}))
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
                    webhookmgr.run_command_webhooks(command, webhookmgr.payload_formatter(500,
                                                                               {"error": "TRACEBACK"},
                                                                               {"server": {"id": server_id, "name": server_name, "running": running}},
                                                                               {"info": "A Traceback occured while restarting the MC server"}))

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
                webhookmgr.run_command_webhooks(command, webhookmgr.payload_formatter(200, {}, {"code": "SER_RESTART_DONE", "server": {"id": server_id, "name": server_name, "running": running}}, {"info": "Server restart action has completed"}))

        elif command == 'start_mc_server':
            srv_obj.run_threaded_server()
            time.sleep(2)
            multi.do_stats_for_servers()
            webhookmgr.run_command_webhooks(command, webhookmgr.payload_formatter(200, {}, {"code": "SER_START_DONE", "server": {"id": server_id, "name": server_name, "running": running}}, {"info": "Server start action has completed"}))

        elif command == 'stop_mc_server':
            if running:
                logger.info("Stopping MC server %s", server_name)
                srv_obj.stop_threaded_server()
                time.sleep(2)
                multi.do_stats_for_servers()
                webhookmgr.run_command_webhooks(command, webhookmgr.payload_formatter(200, {}, {"code": "SER_STOP_DONE", "server": {"id": server_id, "name": server_name, "running": running}}, {"info": "Server stop action has completed"}))
            else:
                logger.info("Stop halted! Server %s is not running!", server_name)
                webhookmgr.run_command_webhooks(command, webhookmgr.payload_formatter(500, {"error": "SER_NOT_RUNNING"}, {"server": {"id": server_id, "name": server_name, "running": running}}, {"info": "Server is not running"}))

        elif command == 'update_server_jar':
            srv_obj.update_server_jar(False)

        elif command == 'revert_server_jar':
            srv_obj.revert_updated_server_jar(False)

        elif command == 'update_server_jar_console':
            srv_obj.update_server_jar(True)

        elif command == 'revert_server_jar_console':
            srv_obj.revert_updated_server_jar(True)

        elif command == "exit_crafty":
            logger.info("Sending Stop Command To Crafty")

            # stop the ftp server...
            if ftp_svr_object.check_running():
                ftp_svr_object.stop_threaded_ftp_server()

            # kill all mc servers gracefully
            multi.stop_all_servers()

            logger.info("***** Crafty Stopped ***** \n")
            webhookmgr.run_command_webhooks(command, webhookmgr.payload_formatter(200, {}, {"code": "CWEB_STOP"}, {"info": "Crafty is shutting down"}))
            os._exit(0)

        elif command == 'start_ftp':
            settings = MC_settings.get_by_id(server_id)

            if ftp_svr_object.check_running():
                logger.warning("The FTP server is already running - please stop it before starting again")
                webhookmgr.run_command_webhooks(command, webhookmgr.payload_formatter(500, {"error": "FTP_RUNNING"}, {}, {"info": "FTP is already running"}))
                return False

            if helper.check_directory_exist(settings.server_path):
                logger.info("Setting FTP root path to {}".format(settings.server_path))
                ftp_svr_object.set_root_dir(settings.server_path)
            else:
                logger.error("Path: {} not found!".format(settings.server_path))
                webhookmgr.run_command_webhooks(command, webhookmgr.payload_formatter(200, {"error": "PATH_NONEXISTANT"}, {"path": settings.server_path}, {"info": "Home path for FTP server not found"}))
                return False

            logger.info("Starting FTP Server")
            ftp_svr_object.run_threaded_ftp_server(server_id)
            webhookmgr.run_command_webhooks(command, webhookmgr.payload_formatter(200, {}, {}, {"info": "FTP server successfully started"}))

        elif command == 'stop_ftp':
            ftp_svr_object.stop_threaded_ftp_server()
            webhookmgr.run_command_webhooks(command, webhookmgr.payload_formatter(200, {}, {}, {"info": "FTP server successfully stopped"}))

        elif command == 'destroy_world':
            logger.info("Destroying World for Server: {} - {}".format(server_id, server_name))
            srv_obj.destroy_world()

