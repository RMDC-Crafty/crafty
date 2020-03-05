import os
import cmd
import sys
import time
import json
import logging

from app.classes.console import console
from app.classes.helpers import helpers
from app.classes.models import Remote, MC_settings, Webserver, model_to_dict, Users
from app.classes.multiserv import multi

helper = helpers()

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
        console.info("Stopping any server daemons")
        multi.stop_all_servers()
        self.print_crafty_end()

    def do_stop(self, line):
        if line == '':
            self.help_stop()
            return 0

        try:
            int(line)
        except ValueError:
            console.error("Server ID must be a number")
            self.help_stop()
            return 0

        try:
            server = MC_settings.get_by_id(line)

        except Exception as e:
            console.help("Unable to find a server with that ID: {}".format(e))
            return 0

        server = int(line)

        if helper.is_setup_complete():

            srv_obj = multi.get_server_obj(server)

            if not srv_obj.check_running():
                console.warning("Server already stopped")
            else:
                console.info("Stopping Minecraft Server")
                multi.stop_server(server)
                '''
                Remote.insert({
                    Remote.command: 'stop_mc_server'
                }).execute()
                '''
        else:
            console.warning("Unable to stop server, please complete setup in the web GUI first")

    def help_stop(self):
        console.help("Stops a Server")
        console.help("Specify the server to stop by ID number")
        console.help("Example: stop 1 - this will stop server ID 1")
        console.help("You can get a server id by issuing list_servers")

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
        if line == '':
            self.help_start()
            return 0

        try:
            int(line)
        except ValueError:
            console.error("Server ID must be a number")
            self.help_start()
            return 0

        try:
            server = MC_settings.get_by_id(line)

        except Exception as e:
            console.help("Unable to find a server with that ID: {}".format(e))
            return 0

        server = int(line)

        if helper.is_setup_complete():

            srv_obj = multi.get_server_obj(server)

            if srv_obj.check_running():
                console.warning("Server already running")
            else:
                console.info("Starting Minecraft Server in background")

                Remote.insert({
                    Remote.command: 'start_mc_server',
                    Remote.server_id: server,
                    Remote.command_source: "localhost"
                }).execute()

        else:
            console.warning("Unable to start server, please complete setup in the web GUI first")

    def help_start(self):
        console.help("Starts a Server")
        console.help("Specify the server to start by ID number")
        console.help("Example: start 1 - this will start server ID 1")
        console.help("You can get a server id by issuing list_servers")

    def do_restart(self, line):
        if line == '':
            self.help_start()
            return 0

        try:
            int(line)
        except ValueError:
            console.error("Server ID must be a number")
            self.help_start()
            return 0

        try:
            server = MC_settings.get_by_id(line)

        except Exception as e:
            console.help("Unable to find a server with that ID: {}".format(e))
            return 0

        server = int(line)

        Remote.insert({
            Remote.command: 'restart_mc_server',
            Remote.server_id: server,
            Remote.command_source: "localhost"
        }).execute()

        console.info("Restarting Minecraft Server in background")

    def help_restart(self):
        console.help("Stops then Starts the server if not running. Will also start the server if not already running")

    def help_show_stats(self):
        console.help("Shows system information such as CPU/Mem/Disk Usage and Server stats: Online / Max players etc")

    def do_show_stats(self, line):
        multi.do_host_status()
        host_stats = multi.get_host_status()
        server_stats = multi.get_stats_for_servers()

        websettings = Webserver.get()

        port_number = websettings.port_number

        console.info("/" * 75)
        console.info("#\t\t Crafty Controller Server Stats \t\t\t#")
        console.info("/" * 75)

        console.info("Boot Time:\t {}".format(host_stats['boot_time']))
        console.info("Webconsole at:\t https://{}:{}".format(helper.get_local_ip(), port_number))
        console.info("-" * 75)

        console.info("CPU Usage:\t {}".format(host_stats['cpu_usage']))
        console.info("CPU Cores:\t {}".format(host_stats['cpu_cores']))
        console.info("Mem Percent:\t {}".format(host_stats['mem_percent']))
        console.info("Mem Usage: \t {} / {}".format(host_stats['mem_usage'], host_stats['mem_total']))
        console.info("Disk Percent:\t {}".format(host_stats['disk_percent']))
        console.info("Disk Usage: \t {} / {}".format(host_stats['disk_usage'], host_stats['disk_total']))

        console.info("-" * 75)
        console.info(" --- Minecraft Servers --- ")
        console.info("-" * 75)

        s = 1
        while s <= len(server_stats):
            data = server_stats[s]
            console.info("Server ID {}".format(data['server_id']))
            console.info("Running {}".format(data['server_running']))
            console.info("Players: {}/{}".format(data['online_players'], data['max_players']))
            s += 1
        console.help("Use the list_servers command to get more detailed data")

    def do_set_passwd(self, line):

        try:
            user = Users.get(Users.username == line).username
        except:
            console.error("User: {} Not Found".format(line))
            return False
        new_pass = input("NEW password for: {} > ".format(user))

        if len(new_pass) > 512:
            console.warning("Password Too Long")
            return False

        if len(new_pass) < 6:
            console.warning("Password Too Short")
            return False

        Users.update({
            Users.password: helper.encode_pass(new_pass)
        }).where(Users.username == user).execute()

        console.info("Password for {} is now set to {}".format(user, new_pass))

    def help_set_passwd(self):
        console.help("Sets a users password. Example set_password Admin. Use list_users to see defined users")

    def help_disable_autostart(self):
        console.help("Disables Server Autostarting on Crafty Launch")
        console.help("Specify the server to modify by ID number")
        console.help("Example: disable_autostart 1 - this will disable auto-start for server 1")
        console.help("You can get a server id by issuing list_servers")

    def do_disable_autostart(self, line):
        if line == '':
            self.help_disable_autostart()
            return 0

        try:
            int(line)
        except ValueError:
            console.error("Server ID must be a number")
            self.help_disable_autostart()
            return 0

        try:
            server = MC_settings.get_by_id(line)

        except Exception as e:
            console.help("Unable to find a server with that ID: {}".format(e))
            return 0

        server = int(line)

        MC_settings.update({
            MC_settings.auto_start_server: False
        }).where(MC_settings.id == server).execute()

        logger.info("Disabled Autostart for Server {} via the console".format(server))
        console.info("Disabled Autostart for Server {} ".format(server))

    def help_enable_autostart(self):
        console.help("Enables Server Autostarting on Crafty Launch")
        console.help("Specify the server to modify by ID number")
        console.help("Example: enable_autostart 1 - this will enable auto-start for server 1")
        console.help("You can get a server id by issuing list_servers")

    def do_enable_autostart(self, line):
        if line == '':
            self.help_enable_autostart()
            return 0

        try:
            int(line)
        except ValueError:
            console.error("Server ID must be a string")
            self.help_enable_autostart()
            return 0

        try:
            server = MC_settings.get_by_id(line)

        except Exception as e:
            console.help("Unable to find a server with that ID: {}".format(e))
            return 0

        server = int(line)

        MC_settings.update({
            MC_settings.auto_start_server: True
        }).where(MC_settings.id == server).execute()

        logger.info("Enabled Autostart for Server {} via the console".format(server))
        console.info("Enabled Autostart for Server {} ".format(server))

    def do_reload_webserver(self, line):
        Remote.insert({
            Remote.command: 'restart_web_server',
            Remote.server_id: 1,
            Remote.command_source: 'localhost'
        }).execute()
        console.info("Reloading Tornado Webserver, Please wait 5 seconds to reconnect")

    def help_reload_webserver(self):
        console.help("Reloads the Tornado Webserver, takes 5 seconds to reload")

    def do_change_web_port(self, line):
        if int(line) > 65535:
            console.error("Invalid Port")
            return False

        if int(line) < 1:
            console.error("Invalid Port")
            return False

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

    def help_list_servers(self):
        console.help("Lists Servers Defined in the System")

    def do_list_servers(self, line):
        servers = MC_settings.select()
        console.info("Servers Defined:")
        console.info('-'*30)
        for s in servers:
            srv_obj = multi.get_server_obj(s.id)
            running = srv_obj.check_running()
            stats = multi.get_stats_for_server(s.id)
            # print(stats)

            console.info("Server ID: {}".format(s.id))
            console.info("Name:{}".format(s.server_name))
            console.info("Path: {}".format(s.server_path))
            console.info("Memory: {}/{}:".format(s.memory_min, s.memory_max))
            console.info("IP {} / Port: {}".format(s.server_ip, s.server_port))
            console.info("AutoStart: {}".format(s.auto_start_server))
            console.info("Currently Running: {}".format(running))
            console.info("Started: {}".format(stats['server_start_time']))
            console.info("CPU: {}".format(stats['cpu_usage']))
            console.info("Memory: {}".format(stats['memory_usage']))
            console.info("Players: {}/{}".format(stats['online_players'], stats['max_players']))
            console.info("Server: {}".format(stats['server_version']))
            console.info("MOTD: {}".format(stats['motd']))

            console.info('-' * 30)

    def help_update_server_jar(self):
        console.help("Updates a Server Jar")
        console.help("Specify the server to update by ID number")
        console.help("Example: update_server_jar 1 - this will update server ID 1")
        console.help("You can get a server id by issuing list_servers")

    def do_update_server_jar(self, line):
        if line == '':
            self.help_update_server_jar()
            return 0

        try:
            int(line)
        except ValueError:
            console.error("Server ID must be a number")
            self.help_update_server_jar()
            return 0

        try:
            server = MC_settings.get_by_id(line)

        except Exception as e:
            console.help("Unable to find a server with that ID: {}".format(e))
            return 0

        server = int(line)

        if helper.is_setup_complete():

            srv_obj = multi.get_server_obj(server)

            console.info("Updating Server Jar in background")

            Remote.insert({
                Remote.command: 'update_server_jar_console',
                Remote.server_id: server,
                Remote.command_source: "localhost"
            }).execute()
        else:
            console.warning("Unable to update server jar, please complete setup in the web GUI first")

    def help_revert_server_jar(self):
        console.help("Reverts a Server Jar Update")
        console.help("Specify the server to revert by ID number")
        console.help("Example: revert_server_jar 1 - this will revert the update for server ID 1")
        console.help("You can get a server id by issuing list_servers")

    def do_revert_server_jar(self, line):
        if line == '':
            self.help_update_server_jar()
            return 0

        try:
            int(line)
        except ValueError:
            console.error("Server ID must be a number")
            self.help_update_server_jar()
            return 0

        try:
            server = MC_settings.get_by_id(line)

        except Exception as e:
            console.help("Unable to find a server with that ID: {}".format(e))
            return 0

        server = int(line)

        if helper.is_setup_complete():

            srv_obj = multi.get_server_obj(server)

            console.info("Reverting updated Server Jar in background")

            Remote.insert({
                Remote.command: 'revert_server_jar_console',
                Remote.server_id: server,
                Remote.command_source: "localhost"
            }).execute()
        else:
            console.warning("Unable to update server jar, please complete setup in the web GUI first")

