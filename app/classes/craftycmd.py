import os
import cmd
import sys
import time
import json

from app.classes.console import Console
from app.classes.helpers import helpers
from app.classes.models import *
from app.classes.multiserv import multi

helper = helpers()
console = Console()
logger = logging.getLogger(__name__)

class MainPrompt(cmd.Cmd):
    """ The main command class - loads the other modules/prompts """

    def __init__(self, mc_server_obj):
        super().__init__()
        self.mc_server_obj = mc_server_obj

    # overrides the default Prompt
    version_data = helper.get_version()
    prompt = "Crafty Controller v{}.{}.{} > ".format(version_data['major'], version_data['minor'], version_data['sub'])

    def emptyline(self):
        pass

    def print_crafty_end(self):
        logger.info("***** Crafty Stopped ***** \n")

    def stop_all_children(self):
        Console.info("Stopping any server daemons")

        if self.mc_server_obj.check_running:
            try:
                self.mc_server_obj.stop_threaded_server()
                self.print_crafty_end()
            except:
                self.print_crafty_end()
        else:
            self.print_crafty_end()

    def do_stop(self, line):
        running = self.mc_server_obj.check_running()

        if running:
            try:
                console.info("Stopping MC Server")
                Remote.insert({
                    Remote.command: 'stop_mc_server'
                }).execute()
            except:
                pass

            console.info("Servers Stopped")
        else:
            console.info("Server not running")

    def help_stop(self):
        console.help("Stops the server if running, Exits the program")

    def do_EOF(self, line):
        """ Exits the main program via Ctrl -D Shortcut """
        self.stop_all_children()
        sys.exit(0)

    def do_exit(self, line):
        """ Exits the main program """
        self.stop_all_children()
        sys.exit(0)

    def help_exit(self):
        console.help("Stops the server if running, Exits the program")

    def do_start(self, line):
        if helper.is_setup_complete():
            running_check = self.mc_server_obj.check_running()
            if running_check:
                console.warning("Server already running")
            else:
                console.info("Starting Minecraft Server in background")
                Remote.insert({
                    Remote.command: 'start_mc_server'
                }).execute()
        else:
            console.warning("Unable to start server, please complete setup in the web GUI first")

    def help_start(self):
        console.help("Starts the Minecraft server if not running")

    def do_restart(self, line):
        Remote.insert({
            Remote.command: 'restart_mc_server'
        }).execute()
        console.info("Restarting Minecraft Server in background")

    def help_restart(self):
        console.help("Stops then Starts the server if not running. Will also start the server if not already running")

    def help_show_stats(self):
        console.help("Shows system information such as CPU/Mem/Disk Usage and Server stats: Online / Max players etc")

    def do_show_stats(self, line):
        multi.do_host_status()
        json_file_path = os.path.join(helper.get_web_temp_path(), 'server_data.json')

        try:
            with open(json_file_path, 'r') as json_file:
                server_stats = json.load(json_file)
            json_file.close()
        except Exception as e:
            "Unable to read json file: {}".format(e)
            return False

        websettings = Webserver.get()

        port_number = websettings.port_number

        console.info("/" * 75)
        console.info("#\t\t Crafty Controller Server Stats \t\t\t#")
        console.info("/" * 75)

        console.info("Boot Time:\t {}".format(server_stats['boot_time']))
        if server_stats['server_running']:
            console.info("MC Start Time:\t {}".format(server_stats['mc_start_time']))
        else:
            console.info("MC Start Time:\t Server NOT running ")
        console.info("Webconsole at:\t https://{}:{}".format(helper.get_local_ip(), port_number))
        console.info("-" * 75)

        console.info("CPU Usage:\t {}".format(server_stats['cpu_usage']))
        console.info("CPU Cores:\t {}".format(server_stats['cpu_cores']))
        console.info("Mem Percent:\t {}".format(server_stats['mem_percent']))
        console.info("Mem Usage: \t {} / {}".format(server_stats['mem_usage'], server_stats['mem_total']))
        console.info("Disk Percent:\t {}".format(server_stats['disk_percent']))
        console.info("Disk Usage: \t {} / {}".format(server_stats['disk_usage'], server_stats['disk_total']))

        console.info("-" * 75)

        if server_stats['server_running']:
            console.info("Online Stats:\t {} of {} players online".format(
                server_stats['online_stats']['online'],
                server_stats['online_stats']['max']))
            console.info("Server Version: \t {}".format(server_stats['server_version']))
            console.info("Server MOTD: \t {}".format(server_stats['server_description']))

        # print(server_stats)

    def do_set_passwd(self, line):

        try:
            user = Users.get(Users.username == line).username
        except Exception as e:
            Console.error("User: {} Not Found".format(line))
            return False
        new_pass = input("NEW password for: {} > ".format(user))

        Users.update({
            Users.password: helper.encode_pass(new_pass)
        }).where(Users.username == user).execute()

        console.info("Password for {} is now set to {}".format(user, new_pass))

    def help_set_passwd(self):
        console.help("Sets a users password. Example set_password Admin. Use list_users to see defined users")

    def help_disable_autostart(self):
        console.help("Disables Minecraft Server Autostarting on Crafty Launch")

    def do_disable_autostart(self, line):
        MC_settings.update({
            MC_settings.auto_start_server: False
        }).execute()
        logger.info("Disabled Minecraft Autostart via the console")
        Console.info("Disabled Minecraft Autostart")

    def help_enable_autostart(self):
        console.help("Enables Minecraft Server Autostarting on Crafty Launch")

    def do_enable_autostart(self,line):
        MC_settings.update({
            MC_settings.auto_start_server: False
        }).execute()
        logger.info("Enabled Minecraft Autostart via the console")
        Console.info("Enabled Minecraft Autostart")

    def do_reload_webserver(self, line):
        Remote.insert({
            Remote.command: 'restart_web_server'
        }).execute()
        console.info("Reloading Tornado Webserver, Please wait 5 seconds to reconnect")

    def help_reload_webserver(self):
        console.help("Reloads the Tornado Webserver, takes 5 seconds to reload")

    def do_change_web_port(self, line):
        Webserver.update({
            Webserver.port_number: int(line)
        }).execute()
        console.info("Tornado Webserver Port set to port: {}".format(line))

    def help_change_web_port(self):
        console.help("Sets the Tornado Webserver Port. Issue 'reload webserver' to apply the change.")

    def do_list_users(self, line):
        console.info("Users defined:")
        all_users = Users.select().execute()

        for user in all_users:
            console.info("User: {} - Role:{}".format(user.username, user.role))

    def help_list_users(self):
        console.help("Lists all users in the Crafty Controller")

    def do_check_update(self, line):
        console.info("Getting Latest Version Info:")
        master = helper.check_version('master')
        beta = helper.check_version('beta')
        snaps = helper.check_version('snapshot')
        current = helper.get_version()
        console.info("Master Branch has: {}.{}.{}".format(master['major'], master['minor'], master['sub']))
        console.info("Beta Branch has: {}.{}.{}".format(beta['major'], beta['minor'], beta['sub']))
        console.info("Snaps Branch has: {}.{}.{}".format(snaps['major'], snaps['minor'], snaps['sub']))
        console.info("You are on Version: {}.{}.{}".format(current['major'], current['minor'], current['sub']))

    def help_check_update(self):
        console.help("Shows version information for you and what is in the repos to help you decide if you should "
                     "update or not")

    def help_update_jar(self):
        console.help("This will automatically update your server jar. If the server is running, it will be restarted "
                     "after the download is complete.")

    def do_update_jar(self, line):
        self.mc_server_obj.update_server_jar()

    def help_revert_jar_upgrade(self):
        console.help("This will automatically revert your server jar from the last backup copy")

    def do_revert_jar_upgrade(self, line):
        self.mc_server_obj.revert_updated_server_jar()