import os
import sys
import time
import json
import secrets
import logging
import schedule
import threading
import logging.config


def setup_logging():
    logging_config_file = os.path.join(os.path.curdir, 'app', 'config', 'logging.json')

    if os.path.exists(logging_config_file):

        # open our logging config file
        with open(logging_config_file, 'rt') as f:
            logging_config = json.load(f)
            logging.config.dictConfig(logging_config)
    else:
        logging.basicConfig(level=logging.DEBUG)
        logging.warning("Unable to read logging config from {} - falling to default mode".format(logging_config_file))

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
    Remote.insert({
        Remote.command: 'exit_crafty'
    }).execute()
    time.sleep(2)
    sys.exit(0)

if __name__ == '__main__':
    """ Our Main Starter """
    log_file = os.path.join(os.path.curdir, 'logs', 'crafty.log')

    # ensure the log directory is there
    try:
        os.makedirs(os.path.join(os.path.curdir, 'logs'))

    except Exception as e:
        pass

    # ensure the log file is there
    open(log_file, 'a').close()

    # sets up our custom logger
    setup_logging()

    # setting up the logger object
    logger = logging.getLogger(__name__)

    # now that logging is setup - let's import the rest of the things we need to run
    from app.classes.helpers import helper
    from app.classes.console import console

    # doing a more focused import here, because * imports can be a little crazy.
    from app.classes.models import peewee, Users, MC_settings, Webserver, Schedules, History, Crafty_settings, Backups, Roles, Remote, Ftp_Srv

    # make sure our web temp directory is there
    helper.ensure_dir_exists(os.path.join(os.path.curdir, "app", 'web', 'temp'))

    # checking for additional arguments such as -k
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

    logger.info("***** Crafty Launched *****")

    # announce the program
    do_intro()

    admin_pass = None

    # is this a fresh install?
    fresh_install = helper.is_fresh_install()

    # creates the database tables / sqlite database file
    peewee.create_tables()

    if fresh_install:
        # save a file in app/config/new_install so we know this is a new install
        helper.make_new_install_file()

        admin_pass = helper.random_string_generator()
        admin_token = secrets.token_urlsafe(32)
  
        peewee.default_settings(admin_pass, admin_token)

    else:
        peewee.do_database_migrations()

    # only import / new database tables are created do we load the rest of the things!
    from app.classes.ftp import ftp_svr_object
    from app.classes.minecraft_server import mc_server
    from app.classes.http import tornado_srv
    from app.classes.craftycmd import MainPrompt
    from app.classes.remote_coms import remote_commands

    logger.info("Starting Scheduler Daemon")
    console.info("Starting Scheduler Daemon")

    scheduler = threading.Thread(name='Scheduler', target=start_scheduler, daemon=True)
    scheduler.start()

    mc_server.do_init_setup()



    # startup Tornado
    tornado_srv.start_web_server(True)
    websettings = Webserver.get()
    port_number = websettings.port_number

    console.info("Starting Tornado HTTPS Server https://{}:{}".format(helper.get_local_ip(), port_number))
    if fresh_install:
        console.info("Please connect to https://{}:{} to continue the install:".format(
            helper.get_local_ip(), port_number))
        console.info("Your Username is: Admin")
        console.info("Your Password is: {}".format(admin_pass))
        console.info("Your Admin token is: {}".format(admin_token))

    # start the remote commands watcher thread
    remote_coms = remote_commands(mc_server, tornado_srv)
    remote_coms_thread = threading.Thread(target=remote_coms.start_watcher, daemon=True, name="Remote_Coms")
    remote_coms_thread.start()

    console.info("Crafty Startup Procedure Complete")
    console.help("Type 'stop' or 'exit' to shutdown the system")

    Crafty = MainPrompt(mc_server)
    Crafty.cmdloop()

