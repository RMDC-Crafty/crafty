import os
import sys
import time
import json
import logging
import argparse
import threading
import logging.config
import datetime
import subprocess

def is_venv():
    return hasattr(sys, 'real_prefix') or sys.base_prefix != sys.prefix

try:
    import argon2
    import yaml
    import secrets
    import schedule
    from termcolor import colored
    from OpenSSL import crypto, SSL
    from app.classes.console import console

except Exception as e:
    print("/" * 75 + "\n")
    print("\t\t\tWTF!!! \n \t\t(What a terrible failure) \n")
    print("/" * 75 + "\n")
    print(" Crafty is unable to find required modules")
    print(" Some common causes of this issue include:")
    print("\t * Modules didn't install: Did pip install -r requirements.txt run correctly?")
    print("\t * You haven't activated your virtual environment, maybe try activating it?")
    print("\n Need Help? We are here to help! - https://discord.gg/XR5x3ZM \n")
    print("Exception caught: {}".format(e))
    if is_venv:
        pipinstall = str(input("A virtual environment has been detected, would you like to try reinstalling the modules? [yes/no]: "))
        pipinstall = pipinstall.lower()
        print(pipinstall)
        if pipinstall == str("yes"):
            file = open("requirements.txt" , "r")

            for line in file:
                req = line.split("/n")
                command_list = [sys.executable, "-m", "pip", "install", req]
                with subprocess.Popen(command_list, stdout=subprocess.PIPE) as proc:
                    print(proc.stdout.read())
            print("Please Run Crafty Again!")
            sys.exit(1)
        else:
            print("Not reinstalling modules, join the discord for further assistance!")
            sys.exit(1)
    else:
        print("It has been detected that you are not in a virtual environment, maybe try activating it?")
        print("If you are not sure how to do this, ask for help in our discord!")
        pipinstall = str(input("If you have chosen to not use a virtual environment, would you like to try reinstalling the modules? [yes/no]: "))
        pipinstall = pipinstall.lower()
        print(pipinstall)
        if pipinstall == str("yes"):
            file = open("requirements.txt" , "r")

            for line in file:
                req = line.split("/n")
                command_list = [sys.executable, "-m", "pip", "install", req]
                with subprocess.Popen(command_list, stdout=subprocess.PIPE) as proc:
                    print(proc.stdout.read())
            print("Please Run Crafty Again!")
            sys.exit(1)
        else:
            print("Not reinstalling modules, join the discord for further assistance!")
            sys.exit(1)


def setup_logging(debug=False):
    logging_config_file = os.path.join(os.path.curdir,
                                       'app',
                                       'config',
                                       'logging.json'
                                       )

    if os.path.exists(logging_config_file):

        # open our logging config file
        with open(logging_config_file, 'rt') as f:
            logging_config = json.load(f)
            if debug:
                logging_config['loggers']['']['level'] = 'DEBUG'
            logging.config.dictConfig(logging_config)
    else:
        logging.basicConfig(level=logging.DEBUG)
        logging.warning("Unable to read logging config from {}".format(logging_config_file))


def do_intro():
    version_data = helper.get_version()
    version = "{}.{}.{}".format(version_data['major'], version_data['minor'], version_data['sub'])

    intro = """
    {lines}
    #\t\tWelcome to Crafty Controller - v.{version}\t\t      #
    {lines}
    #   \tServer Manager / Web Portal for your Minecraft server\t      #
    #   \t\tHomepage: www.craftycontrol.com\t\t\t      #
    {lines}
    """.format(lines="/" * 75, version=version)

    print(intro)


def show_help():
    console.help("-h: shows this message")
    console.help("-k: stops all crafty processes")
    console.help("--no-console: don't start the console")
    sys.exit(0)


def start_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


def send_kill_command():
    # load the remote commands obj
    from app.classes.remote_coms import remote_commands
    from app.classes.http import tornado_srv
    from app.classes.models import peewee, Remote

    # start the remote commands watcher thread
    remote_coms = remote_commands(tornado_srv)
    remote_coms_thread = threading.Thread(target=remote_coms.start_watcher, daemon=True, name="Remote_Coms")
    remote_coms_thread.start()

    Remote.insert({
        Remote.command: 'exit_crafty',
        Remote.server_id: 1,
        Remote.command_source: 'local'
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
    try:
        open(log_file, 'a').close()
    except Exception as e:
        console.critical("Unable to open log file!")
        sys.exit(1)

    daemon_mode = False

    parser = argparse.ArgumentParser("Crafty Web - A Minecraft Server GUI")

    parser.add_argument('-k', '--kill-all',
                        action='store_true',
                        help="Find and terminate all running Crafty instances on the host system."
    )

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Sets Crafty's logging level to debug."
                        )

    parser.add_argument('-d', '--daemonize',
                        action='store_true',
                        help="Prevent exit of crafty.py and disable console."
                        )

    parser.add_argument('-c', '--config',
                        help="Specify a config file to tell Crafty where to store it's database, version, etc."
                        )

    args = parser.parse_args()

    # sets up our logger
    setup_logging(debug=args.verbose)

    # setting up the logger object
    logger = logging.getLogger(__name__)

    # now that logging is setup - let's import the rest of the things we need to run
    from app.classes.helpers import helper

    if not is_venv:
        logger.critical("Not in a virtual environment! Exiting")
        console.critical("Not in a virtual environment! Exiting")
        sys.exit(1)

    logger.info("***** Crafty Launched: Verbose {} *****".format(args.verbose))

    # announce the program
    do_intro()

    admin_pass = None

    # load config file and reprogram default values
    if args.config:
        config_path = os.path.join(os.curdir, args.config)
        logger.info("Loading config from file {}".format(config_path))
        try:
            with open(config_path) as f:
                cfg = yaml.safe_load(f)
                f.close()
        except:
            logger.exception("Specified config has invalid syntax/cannot be read. Traceback:")
        else:
            logger.info("Setting config and db paths")
            helper.redefine_paths(cfg['config_dir'], cfg['db_dir'])

            if not args.daemonize:
                daemon_mode = cfg['daemon_mode']
    else:
        logger.warning("No config specified")

    # prioritize command line flags
    if args.kill_all:
        send_kill_command()

    if args.daemonize:
        daemon_mode = args.daemonize

    # do we have access to write to our folder?
    if not helper.check_writeable(os.curdir):
        logger.info("***** Crafty Stopped ***** \n")
        sys.exit(1)

    # is this a fresh install?
    fresh_install = helper.is_fresh_install()

    # doing a more focused import here, because * imports can be a little crazy.
    # also import after config and cmd args
    from app.classes.models import peewee, Users, MC_settings, Webserver, Schedules, History, Crafty_settings, Backups, Roles, Remote, Ftp_Srv

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
    # from app.classes.minecraft_server import mc_server
    from app.classes.http import tornado_srv
    from app.classes.craftycmd import MainPrompt
    from app.classes.minecraft_server import mc_server

    from app.classes.remote_coms import remote_commands
    from app.classes.multiserv import multi

    logger.info("Starting Scheduler Daemon")
    console.info("Starting Scheduler Daemon")

    scheduler = threading.Thread(name='Scheduler', target=start_scheduler, daemon=True)
    scheduler.start()

    # startup Tornado if we aren't killing all craftys
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

        ''' moving this to 3.2
        if not daemon_mode:
            currentDT = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
            message = "Would you like us to setup a minecraft server for you? [y/n]: "
            setupmcsrv = str(input(colored("[+] Crafty: {} - INFO:\t{}".format(currentDT, message), 'white')))
            setupmcsrv = setupmcsrv.lower()
            if setupmcsrv == 'y':
                if os.name == 'nt':
                    os.system("python app\minecraft\mcservcreate.py")
                else:
                    os.system("python app/minecraft/mcservcreate.py")
        else:
            console.warning("Not prompting for first server due to daemonize mode")
        '''

    # for each server that is defined, we set them up in the multi class, so we have them ready for later.

    multi.init_all_servers()

    # do one now...
    multi.do_host_status()

    # do our scheduling
    multi.reload_scheduling()

    # schedule our stats
    schedule.every(10).seconds.do(multi.do_stats_for_servers).tag('server_stats')
    schedule.every(10).seconds.do(multi.do_host_status).tag('server_stats')

    multi.reload_user_schedules()

    # start the remote commands watcher thread
    remote_coms = remote_commands(tornado_srv)
    remote_coms_thread = threading.Thread(target=remote_coms.start_watcher, daemon=True, name="Remote_Coms")
    remote_coms_thread.start()

    console.info("Crafty Startup Procedure Complete")
    console.help("Type 'stop' or 'exit' to shutdown Crafty")

    if not daemon_mode:
        Crafty = MainPrompt(mc_server)
        Crafty.cmdloop()
    else:
        logger.info("Not starting crafty console due to daemonize mode")

    if daemon_mode:
        # Freeze the program in a loop
        logger.info("Freezing program due to daemonize mode")
        while True:
            # fixes a 100% CPU usage issue in daemonized mode - thanks ImMeta for finding this.
            time.sleep(1)

