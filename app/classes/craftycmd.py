import os
import cmd
import sys
import time
import json
import logging

from app.config.version import __version__
from app.classes.console import Console
from app.classes.helpers import helpers
from app.classes.models import *

helper = helpers()
console = Console()

class MainPrompt(cmd.Cmd):
    """ The main command class - loads the other modules/prompts """

    def __init__(self, mc_server_obj):
        super().__init__()
        self.mc_server_obj = mc_server_obj

    # overrides the default Prompt
    prompt = "Crafty Controller > "

    def print_crafty_end(self):
        logging.info("***** Crafty Stopped ***** \n")

    def do_version(self, line):
        Console.info(__version__)

    def help_version(self):
        Console.help("Shows the Crafty version")

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
        self.stop_all_children()
        sys.exit(0)

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
        running_check = self.mc_server_obj.check_running()
        if running_check:
            console.warning("Server already running")
        else:
            self.mc_server_obj.run_threaded_server()


    def help_start(self):
        console.help("Starts the Minecraft server if not running")

    def do_restart(self, line):

        if self.mc_server_obj.check_running:
            try:
                self.mc_server_obj.stop_threaded_server()
                time.sleep(5)
                self.mc_server_obj.run_threaded_server()
            except:
                pass
        else:
            self.mc_server_obj.run_threaded_server()

    def help_restart(self):
        console.help("Stops then Starts the server if not running. Will also start the server if not already running")

    def help_show_stats(self):
        console.help("Shows system information such as CPU/Mem/Disk Usage and Server stats: Online / Max players etc")

    def do_show_stats(self, line):
        self.mc_server_obj.write_html_server_status()
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
        console.info("Mem Usage \t {} / {}".format(server_stats['mem_usage'], server_stats['mem_total']))
        console.info("Disk Percent:\t {}".format(server_stats['disk_percent']))
        console.info("Disk Usage \t {} / {}".format(server_stats['disk_usage'], server_stats['disk_total']))

        console.info("-" * 75)

        if server_stats['server_running']:
            console.info("Online Stats:\t {} of {} players online".format(
                server_stats['online_stats']['online'],
                server_stats['online_stats']['max']))
            console.info("Server Version \t {}".format(server_stats['server_version']))
            console.info("Server MOTD \t {}".format(server_stats['server_description']))

        # print(server_stats)



