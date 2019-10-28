import os
import re
import sys
import json
import time
import shlex
import psutil
import zipfile
import datetime
import threading
import subprocess
import logging.config

from app.classes.console import Console
from app.classes.helpers import helpers
from app.classes.db import db_wrapper

Helper = helpers()



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

        self.db = db_wrapper(Helper.get_db_path())
        self.settings = None

        # do init setup
        #self.do_init_setup()

    def do_init_setup(self):
        logging.debug("Minecraft Server Module Loaded")
        Console.info("Loading Minecraft Server Module")

        self.settings = self.db.get_mc_settings()

        self.setup_server_run_command()

        # lets check for orphaned servers
        self.check_orphaned_server()


        # do we want to auto launch the minecraft server?
        if self.settings['auto_start_server'] == 'y':
            delay = int(self.settings['auto_start_delay'])
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

        server_path = self.settings['server_path']
        server_jar = self.settings['server_jar']
        server_max_mem = self.settings['memory_max']
        server_min_mem = self.settings['memory_min']
        server_args = self.settings['additional_args']

        # set up execute path
        server_exec_path = os.path.join(server_path, server_jar)

        self.server_command = "java -Xms{}M -Xmx{}M -jar {} nogui {}".format(server_min_mem,
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

        try:
            logging.info("Launching Minecraft Server with command {}".format(self.server_command))
            self.process = subprocess.Popen(shlex.split(self.server_command),
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            cwd=self.server_path,
                                            shell=False,
                                            universal_newlines=True)

        except Exception as err:
            logging.critical("Unable to start server!")
            Console.critical("Unable to start server!")
            sys.exit(0)

        self.PID = self.process.pid
        ts = time.time()
        self.start_time = str(datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'))
        logging.info("Minecraft Server Running with PID: {}".format(self.PID))


        # write status file
        self.write_html_server_status()

    def send_command(self, command):
        logging.debug('Sending Command: {} to Server via stdin'.format(command))

        # encode the command
        command.encode()

        # send it
        self.process.stdin.write(command + '\n')

        # flush the buffer to send the command
        self.process.stdin.flush()

        # give the command time to finish
        time.sleep(.25)

    def stop_server(self):
        logging.info('Sending stop command to server')

        self.send_command('Stop')

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
            # poll to see if it's still running - None = Running | Negative Int means Stopped
            poll = self.process.poll()

            if poll is None:
                return True
            else:
                # reset process to None for next run
                self.process = None
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

                    server_jar = self.settings['server_jar']

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

        json_file_path = os.path.join( Helper.get_web_temp_path(), 'server_data.json')

        with open(json_file_path, 'w') as f:
            json.dump(server_stats, f, sort_keys=True, indent=4)
        f.close()

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
        server_prop_file = os.path.join(self.server_path, 'server.properties')

        # re of what we are looking for
        # ignoring case - just in case someone used all caps
        pattern = re.compile(regex, re.IGNORECASE)

        # make sure it exists
        if Helper.check_file_exists(server_prop_file):
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

        errors = Helper.search_file(log_file, "ERROR]")
        warnings = Helper.search_file(log_file, "WARN]")

        error_data = {
            'errors': errors,
            'warnings': warnings
        }

        return error_data

    def get_world_info(self):
        world = self.get_world_name()

        if world:
            level_path = os.path.join(self.server_path, world)
            nether_path = os.path.join(self.server_path, world + "_nether")
            end_path = os.path.join(self.server_path, world + "_the_end")

            level_total_size = self.get_dir_size(level_path)
            nether_total_size = self.get_dir_size(nether_path)
            end_total_size = self.get_dir_size(end_path)

            # doing a sep line to keep readable
            level_total_size = self.human_readable_sizes(level_total_size)
            nether_total_size = self.human_readable_sizes(nether_total_size)
            end_total_size = self.human_readable_sizes(end_total_size)

            return {
                'world_name': world,
                'world_size': level_total_size,
                'nether_size': nether_total_size,
                'end_size': end_total_size
            }
        else:
            logging.warning("Unable to find world disk data")
            return False
