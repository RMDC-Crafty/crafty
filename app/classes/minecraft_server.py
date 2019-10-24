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
        self.do_init_setup()


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

        Console.info("Starting Minecraft Server")

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
        Console.info("Minecraft Server Running with PID: {}".format(self.PID))

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
        Console.info('Stopping Minecraft Server')
        self.send_command('Stop')

        for x in range(6):

            if self.check_running():
                logging.debug('Polling says Minecraft Server is running')
                Console.info('Waiting 10 seconds for all threads to close. Stop command issued {} seconds ago'.format(x * 10))
                time.sleep(10)

            # now the server is dead, we set process to none
            else:
                logging.debug('Minecraft Server Stopped')
                Console.info("Minecraft Server Stopped")
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