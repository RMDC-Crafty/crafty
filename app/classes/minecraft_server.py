import os
import re
import sys
import json
import time
import shlex
import psutil

import datetime
import threading
import subprocess
import logging.config


import pexpect
from pexpect.popen_spawn import PopenSpawn

from app.classes.mc_ping import ping
from app.classes.console import Console
from app.classes.helpers import helpers
from app.classes.models import *

helper = helpers()


class Minecraft_Server():

    def __init__(self):
        # holders for our process
        self.process = None
        self.line = False
        self.PID = None
        self.start_time = None
        self.server_jar = None
        self.server_command = None
        self.server_path = None
        self.server_thread = None
        self.settings = None

        # do init setup
        #self.do_init_setup()

    def do_init_setup(self):
        logging.debug("Minecraft Server Module Loaded")
        Console.info("Loading Minecraft Server Module")

        self.settings = MC_settings.get()
        self.setup_server_run_command()

        # lets check for orphaned servers
        self.check_orphaned_server()


        # do we want to auto launch the minecraft server?
        if self.settings.auto_start_server:
            delay = int(self.settings.auto_start_delay)
            logging.info("Auto Start is Enabled - Waiting {} seconds to start the server".format(delay))
            Console.info("Auto Start is Enabled - Waiting {} seconds to start the server".format(delay))
            time.sleep(int(delay))
            # delay the startup as long as the
            Console.info("Starting Minecraft Server")
            self.run_threaded_server()
        else:
            logging.info("Auto Start is Disabled")
            Console.info("Auto Start is Disabled")

    def setup_server_run_command(self):
        # configure the server
        server_path = self.settings.server_path
        server_jar = self.settings.server_jar
        server_max_mem = self.settings.memory_max
        server_min_mem = self.settings.memory_min
        server_args = self.settings.additional_args

        # set up execute path if we have spaces, we put quotes around it for windows
        if " " in server_path:
            exec_path = '"{}"'.format(server_path)
        else:
            exec_path = server_path

        server_exec_path = os.path.join(exec_path, server_jar)

        self.server_command = 'java -Xms{}M -Xmx{}M -jar {} nogui {}'.format(server_min_mem,
                                                                           server_max_mem,
                                                                           server_exec_path,
                                                                           server_args)
        self.server_path = server_path

    def run_threaded_server(self):
        # start the server
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()

    def stop_threaded_server(self):
        self.stop_server()
        self.server_thread.join()

    def start_server(self):

        if self.check_running():
            Console.warning("Minecraft Server already running...")
            return False

        if os.name == "nt":
            logging.info("Windows Detected - launching cmd")
            self.server_command = self.server_command.replace('\\', '/')
            self.process = pexpect.popen_spawn.PopenSpawn('cmd \n', timeout=None, encoding=None)
            self.process.send('cd {} \n'.format(self.server_path.replace('\\', '/')))
            self.process.send(self.server_command + "\n")
            self.PID = self.process.pid

        else:
            logging.info("Linux Detected - launching Bash")
            self.process = pexpect.popen_spawn.PopenSpawn('/bin/bash \n', timeout=None, encoding=None)

            logging.info("Changing Directories to {}".format(self.server_path))
            self.process.send('cd {} \n'.format(self.server_path))

            logging.info("Sending Server Command: {}".format(self.server_command))
            self.process.send(self.server_command + '\n')

            self.PID = self.process.pid

        ts = time.time()
        self.start_time = str(datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'))
        logging.info("Launching Minecraft server with command: {}".format(self.server_command))
        logging.info("Minecraft Server Running with PID: {}".format(self.PID))


        # write status file
        self.write_html_server_status()

    def send_command(self, command):

        if self.check_running():
            logging.debug('Sending Command: {} to Server via pexpect'.format(command))

            # send it
            self.process.send(command + '\n')
        else:
            logging.warning('Sending Command: {} to Server Failed - Server is not up'.format(command))

    def restart_threaded_server(self):
        if self.check_running():
            self.stop_threaded_server()
            time.sleep(3)
            self.run_threaded_server()
            self.write_html_server_status()

    def stop_server(self):
        logging.info('Sending stop command to server')

        self.send_command('stop')

        for x in range(6):

            if self.check_running():
                logging.debug('Polling says Minecraft Server is running')

                time.sleep(10)

            # now the server is dead, we set process to none
            else:
                logging.debug('Minecraft Server Stopped')
                self.process = None
                self.PID = None
                self.start_time = None
                # return true as the server is down
                return True

        # if we got this far, the server isn't responding, and needs to be forced down
        logging.critical('Unable to stop the server - asking console if they want to force it down')
        Console.critical('The server PID:{} isn\'t responding to stop commands!'.format(self.PID))

        resp = input("Do you want to force the server down? y/n >")
        logging.warning('User responded with {}'.format(resp.lower))

        # ask the parse the response
        if resp.lower() == "y":
            Console.warning("Trying to kill the process")

            # try to kill it with fire!
            self.killpid(self.PID)

            # wait a few seconds to see if we can really kill it
            time.sleep(5)

            # let them know the outcome
            if self.check_running():
                Console.critical("Unable to kill the process - It's still running")
            else:
                Console.info("Process was killed successfully")
        else:
            Console.critical("No worries - I am letting the server run")
            Console.critical("The stop command was still sent though, it might close later, or is unresponsive.")

    def check_running(self):
        # if process is None, we never tried to start
        if self.process is None:
            return False

        else:
            # loop through processes
            for proc in psutil.process_iter():
                try:
                    # Check if process name contains the given name string.
                    if 'java' in proc.name().lower():

                        # join the command line together so we can search it for the server.jar
                        cmdline = " ".join(proc.cmdline())

                        server_jar = self.settings.server_jar

                        if server_jar is None:
                            return False

                        # if we found the server jar in the command line, and the process is java, we can assume it's an
                        # orphaned server.jar running
                        if server_jar in cmdline:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            return False

    def killpid(self, pid):
        logging.info('Killing Process {} and all child processes'.format(pid))
        process = psutil.Process(pid)

        # for every sub process...
        for proc in process.children(recursive=True):
            # kill all the child processes - it sounds too wrong saying kill all the children
            logging.info('Killing process {}'.format(proc.name))
            proc.kill()
        # kill the main process we are after
        logging.info('Killing parent process')
        process.kill()

    def check_orphaned_server(self):

        # loop through processes
        for proc in psutil.process_iter():
            try:
                # Check if process name contains the given name string.
                if 'java' in proc.name().lower():

                    # join the command line together so we can search it for the server.jar
                    cmdline = " ".join(proc.cmdline())

                    server_jar = self.settings.server_jar

                    if server_jar is None:
                        return False

                    # if we found the server jar in the command line, and the process is java, we can assume it's an
                    # orphaned server.jar running
                    if server_jar in cmdline:

                        # set p as the process / hook it
                        p = psutil.Process(proc.pid)
                        pidcreated = datetime.datetime.fromtimestamp(p.create_time())

                        logging.info("Another server found! PID:{}, NAME:{}, CMD:{} ".format(
                            p.pid,
                            p.name(),
                            cmdline
                        ))

                        Console.warning("We found another process running the server.jar.")
                        Console.warning("Process ID: {}".format(p.pid))
                        Console.warning("Process Name: {}".format(p.name()))
                        Console.warning("Process Command Line: {}".format(cmdline))
                        Console.warning("Process Started: {}".format(pidcreated))

                        resp = input("Do you wish to kill this other server process? y/n > ")

                        if resp.lower() == 'y':
                            Console.warning('Attempting to kill process: {}'.format(p.pid))

                            # kill the process
                            p.terminate()
                            # give the process time to die
                            time.sleep(2)
                            Console.warning('Killed: {}'.format(proc.pid))
                            self.check_orphaned_server()

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        return False

    def get_start_time(self):
        if self.check_running():
            return self.start_time
        else:
            return False

    def write_html_server_status(self):

        datime = datetime.datetime.fromtimestamp(psutil.boot_time())
        errors = self.search_for_errors()

        try:
            server_ping = self.ping_server()
        except:
            server_ping = False
            pass

        server_stats = {'cpu_usage': psutil.cpu_percent(interval=0.5) / psutil.cpu_count(),
                        'cpu_cores': psutil.cpu_count(),
                        'mem_percent': psutil.virtual_memory()[2],
                        'disk_percent': psutil.disk_usage('/')[3],
                        'boot_time': str(datime),
                        'mc_start_time': self.get_start_time(),
                        'errors': len(errors['errors']),
                        'warnings': len(errors['warnings']),
                        'world_data': self.get_world_info(),
                        'server_running': self.check_running()
                        }
        if server_ping:
            server_stats.update({'server_description': server_ping.description})
            server_stats.update({'server_version': server_ping.version})
            online_stats = json.loads(server_ping.players)

            if online_stats:
                online_data = {
                    'online': online_stats.get('online', 0),
                    'max': online_stats.get('max', 0),
                    'players': online_stats.get('players', [])
                }
                server_stats.update({'online_stats': online_data})

        else:
            server_stats.update({'server_description': 'Unable To Connect'})
            server_stats.update({'server_version': 'Unable to Connect'})

            online_data = {
                'online': 0,
                'max': 0,
                'players': []
            }
            server_stats.update({'online_stats': online_data})

        json_file_path = os.path.join(helper.get_web_temp_path(), 'server_data.json')

        with open(json_file_path, 'w') as f:
            json.dump(server_stats, f, sort_keys=True, indent=4)
        f.close()

    def backup_worlds(self, announce=True):

        # backup path is crafty_backups in server root
        backup_path = os.path.join(self.settings.server_path, "crafty_backups")
        helper.ensure_dir_exists(backup_path)

        logging.info('Starting Backup Process')

        logging.info('Checking Backup Path Exists')

        if helper.check_directory_exist(backup_path):

            # if server is running
            if announce:
                if self.check_running():
                    self.send_command("say [Crafty Controller] Starting Backup of Server")

            try:
                # make sure we have a backup for this date
                backup_filename = '{}.zip'.format(datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
                backup_full_path = os.path.join(backup_path, backup_filename)

                logging.info("Backing up server directory to: {}".format(backup_filename))

                helper.zippath(self.server_path, backup_full_path, ['crafty_backups'])

                logging.info("Backup Completed")

                if announce:
                    if self.check_running():
                        self.send_command("say [Crafty Controller] Backup Complete")

            except Exception as e:
                logging.error('Unable to create backups- Error: {}'.format(e))

                if announce:
                    if self.check_running():
                        self.send_command('say [Crafty Controller] Unable to create backups - check the logs')

        else:
            logging.error("Unable to find or create backup path!")
            return False

    def list_backups(self):

        backup_path = os.path.join(self.settings.server_path, "crafty_backups")
        helper.ensure_dir_exists(backup_path)

        results = []

        for dirpath, dirnames, filenames in os.walk(backup_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    size = self.human_readable_sizes(os.path.getsize(fp))
                    results.append({'path': fp, 'size': size})

        return results

    def get_world_name(self):
        search_string = 'level-name*'
        worldname = self.search_server_properties(search_string)
        if worldname:
            return worldname
        else:
            return False

    # returns the first setting that = the regex supplied
    def search_server_properties(self, regex='*'):

        # whats the file we are looking for?
        server_prop_file = os.path.join(self.server_path.replace('"', ''), 'server.properties')

        # re of what we are looking for
        # ignoring case - just in case someone used all caps
        pattern = re.compile(regex, re.IGNORECASE)

        # make sure it exists
        if helper.check_file_exists(server_prop_file):
            with open(server_prop_file, 'rt') as f:
                for line in f:
                    # if we find something
                    if pattern.search(line) is not None:
                        match_line = line.rstrip('\n').split("=", 2)

                        # if we have at least 2 items in the list (i.e. there was an = char
                        if len(match_line) == 2:
                            return match_line[1]

            # if we got here, we couldn't find it
            logging.warning('Unable to find string using regex {} in server.properties file'.format(regex))
            return False

        # if we got here, we can't find server.properties (bigger issues)
        logging.warning('Unable to find server.properties file')
        return False

    # because this is a recursive function, we will return bytes, and set human readable later
    def get_dir_size(self, path):
        total = 0
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False):
                total += self.get_dir_size(entry.path)
            else:
                total += entry.stat(follow_symlinks=False).st_size
        return total

    def human_readable_sizes(self,num, suffix='B'):
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                return "%3.1f %s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f %s%s" % (num, 'Yi', suffix)

    def search_for_errors(self):
        log_file = os.path.join(self.server_path, "logs", "latest.log")

        logging.debug("Getting Errors from {}".format(log_file))

        errors = helper.search_file(log_file, "ERROR]")
        warnings = helper.search_file(log_file, "WARN]")

        error_data = {
            'errors': errors,
            'warnings': warnings
        }

        return error_data

    def get_world_info(self):
        world = self.get_world_name()

        if world:
            total_size = 0

            # do a scan of the directories in the server path.
            for root, dirs, files in os.walk(self.server_path, topdown=False):

                # for each directory we find
                for name in dirs:

                    # if the directory name is "region"
                    if name == "region":
                        # log it!
                        logging.debug("Path {} is called region. Getting directory size".format(os.path.join(root, name)))

                        # get this directory size, and add it to the total we have running.
                        total_size += self.get_dir_size(os.path.join(root, name))

            level_total_size = self.human_readable_sizes(total_size)

            return {
                'world_name': world,
                'world_size': level_total_size
            }
        else:
            logging.warning("Unable to find world disk data")
            return {
                'world_name': 'Unable to find world name',
                'world_size': 'Unable to find world size'
            }

    def ping_server(self):

        server_port = self.search_server_properties("server-port")

        # bomb out to default port number
        if not server_port:
            server_port = 25565

        mc_ping = ping('127.0.0.1', server_port)
        return mc_ping

