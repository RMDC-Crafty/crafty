import os
import sys
import time
import logging


from app.classes.logger import custom_loggers
from app.classes.helpers import helpers
from app.classes.console import Console
from app.config.version import __version__
from app.config.version import __version_suffix__
from app.classes.craftycmd import MainPrompt
from app.classes.db import db_wrapper
from app.classes.install import installer

from app.classes.minecraft_server import Minecraft_Server
from app.classes.http import webserver

Helper = helpers()
console = Console()
Webserver = webserver()


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

    dbpath = Helper.get_db_path()

    if Helper.check_file_exists(dbpath):
        return True
    else:
        logging.info("Unable to find: {} - Launching Creation script".format(dbpath))

        # create the db
        db = db_wrapper(dbpath)
        try:
            db.create_new_db()
            db = None
        except:
            logging.critical("Unable to create db - Exiting")
            console.critical("Unable to create db - Exiting")
            sys.exit(1)

        return False


def run_installer():

    dbpath = Helper.get_db_path()
    setup = installer(dbpath)
    setup.do_install()


def setup_admin():
    dbpath = Helper.get_db_path()

    setup = installer(dbpath)
    admin_password = setup.create_admin()
    if admin_password is not None:
        console.info("Your Admin Username is: Admin")
        console.info("Your Admin password is: {}".format(admin_password))
        console.info("Please login to the web portal and change this ASAP")


def main():

    # if we don't have a sql_db, we create one, and run the installers
    if not check_for_sql_db():
        run_installer()

        do_intro()

        # startup Tornado -
        Webserver.start_web_server()
        time.sleep(.5)

        # setup the new admin password (random)
        setup_admin()

    else:
        # startup Tornado -
        do_intro()
        Webserver.start_web_server()
        time.sleep(.5)


    time.sleep(.5)

    mc_server = Minecraft_Server()

    time.sleep(.5)

    Crafty = MainPrompt(mc_server)
    Crafty.cmdloop()


if __name__ == '__main__':
    """ Our Main Starter """
    custom_loggers.setup_logging()
    logging.info("***** Crafty Launched *****")

    if __version_suffix__ == "alpha" or __version_suffix__ == "beta":
        crafty_log_level = 'DEBUG'
    else:
        crafty_log_level = 'INFO'

    logging.info("Setting Log Level: {}".format(crafty_log_level.upper()))
    logger = logging.getLogger()
    logger.setLevel(crafty_log_level.upper())

    main()

