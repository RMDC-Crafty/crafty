import os
import sys
import time
import logging
import schedule
import threading

from app.classes.logger import custom_loggers
from app.classes.helpers import helpers
from app.classes.console import Console

from app.classes.craftycmd import MainPrompt
from app.classes.models import *
from app.classes.install import installer
from app.classes.remote_coms import remote_commands

from app.classes.minecraft_server import Minecraft_Server
from app.classes.http import webserver

helper = helpers()
console = Console()


def do_intro():
    version_data = helper.get_version()

    intro = "/" * 75 + "\n"
    intro += '#\t\tWelcome to Crafty Controller - v.{}.{}.{}\t\t #'.format(
        version_data['major'], version_data['minor'], version_data['sub']) + "\n"

    intro += "/" * 75 + "\n"
    intro += '#   \tServer Manager / Web Portal for your Minecraft server\t\t #' + "\n"
    intro += '#   \t\tHomepage: www.craftycontrol.com\t\t\t\t #' + "\n"
    intro += '/' * 75 + "\n"
    print(intro)


def show_help():
    console.help("-h: shows this message")
    console.help("-k: stops all crafty processes")
    sys.exit(0)


def start_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(.5)


def send_kill_command():
    logging.info("Sending Stop Command To Crafty")
    Remote.insert({
        Remote.command: 'exit_crafty'
    }).execute()
    time.sleep(2)
    sys.exit(0)


if __name__ == '__main__':
    """ Our Main Starter """
    log_file = os.path.join(os.path.curdir, 'logs', 'crafty.log')
    if not helper.check_file_exists(log_file):
        helper.ensure_dir_exists(os.path.join(os.path.curdir, 'logs'))
        open(log_file, 'a').close()

    # make sure our web temp directory is there
    helper.ensure_dir_exists(os.path.join(os.path.curdir, "app", 'web', 'temp'))

    custom_loggers.setup_logging()

    arg_length = len(sys.argv) - 1

    if arg_length == 1:
        argument = sys.argv[1]

        if argument == '-k':
            console.info("Sending Shutdown Command")
            send_kill_command()
        else:
            show_help()

    elif arg_length > 1:
        show_help()

    logging.info("***** Crafty Launched *****")

    # is this a fresh install? (is the database there?)
    fresh_install = helper.is_fresh_install()

    # announce the program
    do_intro()

    # create the database
    create_tables()

    admin_pass = None

    if fresh_install:
        # save a file in app/config/new_install so we know this is a new install
        helper.make_new_install_file()

        admin_pass = helper.random_string_generator()
        default_settings(admin_pass)

    else:
        do_database_migrations()

    logging.info("Starting Scheduler Daemon")
    Console.info("Starting Scheduler Daemon")

    scheduler = threading.Thread(name='Scheduler', target=start_scheduler, daemon=True)
    scheduler.start()

    mc_server = Minecraft_Server()
    mc_server.do_init_setup()

    tornado = webserver(mc_server)

    # startup Tornado
    tornado.start_web_server(True)
    websettings = Webserver.get()
    port_number = websettings.port_number

    Console.info("Starting Tornado HTTPS Server https://{}:{}".format(helper.get_local_ip(), port_number))
    if fresh_install:
        Console.info("Please connect to https://{}:{} to continue the install:".format(
            helper.get_local_ip(), port_number))
        Console.info("Your Username is: Admin")
        Console.info("Your Password is: {}".format(admin_pass))

    # start the remote commands watcher thread
    remote_coms = remote_commands(mc_server, tornado)
    remote_coms_thread = threading.Thread(target=remote_coms.start_watcher, daemon=True, name="Remote_Coms")
    remote_coms_thread.start()

    Console.info("Crafty Startup Procedure Complete")
    Console.help("Type 'stop' or 'exit' to shutdown the system")

    Crafty = MainPrompt(mc_server)
    Crafty.cmdloop()

    # main()

