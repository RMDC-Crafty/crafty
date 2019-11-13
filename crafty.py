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


def check_for_sql_db():
    logging.info("Checking for existing DB")

    dbpath = helper.get_db_path()

    if helper.check_file_exists(dbpath):

        # here we update the database with new tables if needed
        try:
            create_tables()
        except:
            logging.critical("Unable to update db - Exiting")
            console.critical("Unable to update db - Exiting")
            sys.exit(1)
        return True
    else:
        logging.info("Unable to find: {} - Launching Creation script".format(dbpath))

        # create the db
        try:
            create_tables()

        except:
            logging.critical("Unable to create db - Exiting")
            console.critical("Unable to create db - Exiting")
            sys.exit(1)

        return False


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


def read_schedules():
    print('Schedules Here')

def start_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(5)

def main():

    # if we don't have a sql_db, we create one, and run the installers
    if not check_for_sql_db():
        run_installer()

        do_intro()

        mc_server = Minecraft_Server()

        tornado = webserver(mc_server)

        # startup Tornado -
        tornado.start_web_server()
        time.sleep(.5)

        # setup the new admin password (random)
        setup_admin()

    else:

        mc_server = Minecraft_Server()

        # startup Tornado -
        do_intro()

        tornado = webserver(mc_server)

        tornado.start_web_server()
        time.sleep(.5)

    time.sleep(.5)

    mc_server.do_init_setup()

    time.sleep(.5)

    schedule.every(10).seconds.do(mc_server.write_html_server_status)

    logging.info("Starting Scheduler Daemon")
    Console.info("Starting Scheduler Daemon")
    scheduler = threading.Thread(name='Scheduler', target=start_scheduler, daemon=True)
    scheduler.start()

    time.sleep(5)
    # write our server stats to a file
    mc_server.write_html_server_status()
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

