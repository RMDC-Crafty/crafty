import os
import sys
import time
import logging
import schedule
import threading

from app.classes.logger import custom_loggers
from app.classes.helpers import helpers
from app.classes.console import Console
from app.config.version import __version__
from app.classes.craftycmd import MainPrompt
from app.classes.models import *
from app.classes.install import installer
from app.classes.remote_coms import remote_commands

from app.classes.minecraft_server import Minecraft_Server
from app.classes.http import webserver

helper = helpers()
console = Console()

def do_intro():
    intro = "/" * 75 + "\n"
    intro += '#\t\tWelcome to Crafty Controller - v.{}\t\t #'.format(__version__) + "\n"
    intro += "/" * 75 + "\n"
    intro += '#   \tServer Manager / Web Portal for your Minecraft server\t\t #' + "\n"
    intro += '#   \t\tHomepage: www.craftycontrol.com\t\t\t\t #' + "\n"
    intro += '/' * 75 + "\n"
    print(intro)


def is_fresh_install():
    logging.info("Checking for existing DB")

    dbpath = helper.get_db_path()

    fresh_install = False

    if not helper.check_file_exists(dbpath):
        fresh_install = True
        logging.info("Unable to find: {} - This is a fresh install".format(dbpath))

    return fresh_install


def run_installer():
    setup = installer()
    setup.do_install()


def setup_admin():
    setup = installer()
    admin_password = setup.create_admin()
    if admin_password is not None:
        console.info("Your Admin Username is: Admin")
        console.info("Your Admin password is: {}".format(admin_password))
        console.info("Please login to the web portal and change this ASAP")


def start_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(.5)

def main():

    # is this a fresh install? (is the database there?)
    fresh_install = is_fresh_install()

    if fresh_install:
        run_installer()
        default_settings()


    do_intro()

    # make sure the database tables that are needed are there, and have correct default values
    do_database_migrations()

    mc_server = Minecraft_Server()
    tornado = webserver(mc_server)

    # startup Tornado -
    tornado.start_web_server()
    time.sleep(.5)

    # setup the new admin password (random)
    if fresh_install:
        setup_admin()

    mc_server.do_init_setup()

    # fire off a write_html_status now, and schedule one for every 10 seconds
    mc_server.write_html_server_status()
    schedule.every(10).seconds.do(mc_server.write_html_server_status)

    # fire off a history write now, and schedule one for later.
    mc_server.write_usage_history()
    mc_server.reload_history_settings()

    logging.info("Starting Scheduler Daemon")
    Console.info("Starting Scheduler Daemon")

    scheduler = threading.Thread(name='Scheduler', target=start_scheduler, daemon=True)
    scheduler.start()

    # start the remote commands watcher thread
    remote_coms = remote_commands(mc_server, tornado)
    remote_coms_thread = threading.Thread(target=remote_coms.start_watcher, daemon=True, name="Remote_Coms")
    remote_coms_thread.start()

    time.sleep(3)
    Console.info("Crafty Startup Procedure Complete")
    Console.help("Type 'stop' or 'exit' to shutdown the system")

    Crafty = MainPrompt(mc_server)
    Crafty.cmdloop()


if __name__ == '__main__':
    """ Our Main Starter """
    log_file = os.path.join(os.path.curdir, 'logs', 'crafty.log')
    if not helper.check_file_exists(log_file):
        helper.ensure_dir_exists(os.path.join(os.path.curdir, 'logs'))
        open(log_file, 'a').close()

    # make sure our web temp directory is there
    helper.ensure_dir_exists(os.path.join(os.path.curdir, "app", 'web', 'temp'))

    custom_loggers.setup_logging()
    logging.info("***** Crafty Launched *****")

    main()

