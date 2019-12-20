import time
import psutil
import schedule
import threading
import logging.config


import pexpect
from pexpect.popen_spawn import PopenSpawn

from app.classes.mc_ping import ping
from app.classes.console import console
from app.classes.models import *
from app.classes.ftp import ftp_svr_object


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
        self.updating = False

    def reload_settings(self):
        logging.info("Reloading MC Settings from the DB")

        self.settings = MC_settings.get()
        self.setup_server_run_command()

    def do_auto_start(self):
        # do we want to auto launch the minecraft server?
        if self.settings.auto_start_server:
            delay = int(self.settings.auto_start_delay)
            logging.info("Auto Start is Enabled - Waiting {} seconds to start the server".format(delay))
            console.info("Auto Start is Enabled - Waiting {} seconds to start the server".format(delay))
            time.sleep(int(delay))
            # delay the startup as long as the
            console.info("Starting Minecraft Server")
            self.run_threaded_server()
        else:
            logging.info("Auto Start is Disabled")
            console.info("Auto Start is Disabled")

    def do_init_setup(self):
        logging.debug("Minecraft Server Module Loaded")
        console.info("Loading Minecraft Server Module")

        if helper.is_setup_complete():
            self.reload_settings()
            schedule.every(10).seconds.do(self.write_html_server_status)
            self.write_usage_history()
            self.reload_history_settings()


        # lets check for orphaned servers - allows for multiple servers running
        # self.check_orphaned_server()

        # if the db file exists, this isn't a fresh start
        if helper.is_setup_complete():
            self.do_auto_start()

    def setup_server_run_command(self):
        # configure the server
        server_path = self.settings.server_path
        server_jar = self.settings.server_jar
        server_max_mem = self.settings.memory_max
        server_min_mem = self.settings.memory_min
        server_args = self.settings.additional_args
        server_pre_args = self.settings.pre_args

        # set up execute path if we have spaces, we put quotes around it for windows
        if " " in server_path:
            exec_path = '"{}"'.format(server_path)
        else:
            exec_path = server_path

        server_exec_path = os.path.join(exec_path, server_jar)

        self.server_command = 'java -Xms{}M -Xmx{}M {} -jar {} nogui {}'.format(server_min_mem,
                                                                            server_max_mem,
                                                                            server_pre_args,
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
            console.warning("Minecraft Server already running...")
            return False

        logging.info("Launching Minecraft server with command: {}".format(self.server_command))

        if os.name == "nt":
            logging.info("Windows Detected - launching cmd")
            self.server_command = self.server_command.replace('\\', '/')
            self.process = pexpect.popen_spawn.PopenSpawn('cmd \r\n', timeout=None, encoding=None)
            self.process.send('cd {} \r\n'.format(self.server_path.replace('\\', '/')))
            self.process.send(self.server_command + "\r\n")

        else:
            logging.info("Linux Detected - launching Bash")
            self.process = pexpect.popen_spawn.PopenSpawn('/bin/bash \n', timeout=None, encoding=None)

            logging.info("Changing Directories to {}".format(self.server_path))
            self.process.send('cd {} \n'.format(self.server_path))

            logging.info("Sending Server Command: {}".format(self.server_command))
            self.process.send(self.server_command + '\n')

        self.PID = helper.find_progam_with_server_jar(self.settings.server_jar)

        ts = time.time()
        self.start_time = str(datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'))

        logging.info("Minecraft Server Running with PID: {}".format(self.PID))

        # write status file
        self.write_html_server_status()

    def send_command(self, command):

        if not self.check_running() and command.lower() != 'start':
            logging.warning("Server not running, unable to send command: {}".format(command))
            return False

        logging.debug('Sending Command: {} to Server via pexpect'.format(command))

        # send it
        self.process.send(command + '\n')

    def restart_threaded_server(self):
        Remote.insert({
            Remote.command: 'restart_mc_server'
        }).execute()

    def stop_server(self):

        if self.detect_bungee_waterfall():
            logging.info('Waterfall/Bungee Detected: Sending end command to server')
            self.send_command("end")
        else:
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
        logging.critical('Unable to stop the server - force it down {}'.format(self.PID))

        self.killpid(self.PID)

    def check_running(self):
        # if process is None, we never tried to start
        if self.PID is None:
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

                        # if we found the server jar, and the process is java, we can assume it's our server
                        if server_jar in cmdline:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            # the server crashed, or isn't found - so let's reset things.
            logging.warning("The server seems to have vanished, did it crash?")
            self.process = None
            self.PID = None

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

                        console.warning("We found another process running the server.jar.")
                        console.warning("Process ID: {}".format(p.pid))
                        console.warning("Process Name: {}".format(p.name()))
                        console.warning("Process Command Line: {}".format(cmdline))
                        console.warning("Process Started: {}".format(pidcreated))

                        resp = input("Do you wish to kill this other server process? y/n > ")

                        if resp.lower() == 'y':
                            console.warning('Attempting to kill process: {}'.format(p.pid))

                            # kill the process
                            p.terminate()
                            # give the process time to die
                            time.sleep(2)
                            console.warning('Killed: {}'.format(proc.pid))
                            self.check_orphaned_server()

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        return False

    def get_start_time(self):
        if self.check_running():
            return self.start_time
        else:
            return False

    def write_usage_history(self):

        server_stats = {
            'cpu_usage': psutil.cpu_percent(interval=0.5) / psutil.cpu_count(),
            'mem_percent': psutil.virtual_memory()[2]
            }
        try:
            server_ping = self.ping_server()

        except:
            server_ping = False
            pass

        if server_ping:
            online_stats = json.loads(server_ping.players)
            online_data = {'online': online_stats.get('online', 0)}
        else:
            online_data = {'online': 0}

        # write performance data to db
        insert_result = History.insert(
            cpu=server_stats['cpu_usage'],
            memory=server_stats['mem_percent'],
            players=online_data['online']
        ).execute()

        logging.info("Inserted History Record Number {}".format(insert_result))

        query = Crafty_settings.select(Crafty_settings.history_max_age)
        max_days = query[0].history_max_age

        # auto-clean on max days
        max_age = datetime.datetime.now() - datetime.timedelta(days=max_days)

        # delete items older than 1 week
        History.delete().where(History.time < max_age).execute()

    def write_html_server_status(self):

        self.check_running()

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
                        'mem_usage': helper.human_readable_file_size(psutil.virtual_memory()[3]),
                        'mem_total': helper.human_readable_file_size(psutil.virtual_memory()[0]),
                        'disk_percent': psutil.disk_usage('/')[3],
                        'disk_usage': helper.human_readable_file_size(psutil.disk_usage('/')[1]),
                        'disk_total': helper.human_readable_file_size(psutil.disk_usage('/')[0]),
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

    def backup_server(self, announce=True):

        # backup path is saved in the db
        backup_list = Backups.get()
        backup_data = model_to_dict(backup_list)

        backup_path = backup_data['storage_location']
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

                backup_list = Backups.get()
                backup_data = model_to_dict(backup_list)
                backup_dirs = json.loads(backup_data['directories'])

                helper.zippath(backup_dirs, backup_full_path, ['crafty_backups'])

                logging.info("Backup Completed")

                if announce:
                    if self.check_running():
                        self.send_command("say [Crafty Controller] Backup Complete")

            except Exception as e:
                logging.error('Unable to create backups- Error: {}'.format(e))

                if announce:
                    if self.check_running():
                        self.send_command('say [Crafty Controller] Unable to create backups - check the logs')

            # remove any extra backups
            max_backups = backup_data['max_backups']
            logging.info('Checking for backups older than {} days'.format(max_backups))
            helper.del_files_older_than_x_days(max_backups, backup_path)



        else:
            logging.error("Unable to find or create backup path!")
            return False

    def list_backups(self):
        backup_list = Backups.get()
        backup_data = model_to_dict(backup_list)
        backup_path = backup_data['storage_location']
        helper.ensure_dir_exists(backup_path)

        results = []

        for dirpath, dirnames, filenames in os.walk(backup_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    size = helper.human_readable_file_size(os.path.getsize(fp))
                    results.append({'path': fp, 'size': size})

        return results

    def get_world_name(self):
        search_string = 'level-name*'
        worldname = self.search_server_properties(search_string)
        if worldname:
            return worldname
        else:
            return "Not Found"

    def detect_bungee_waterfall(self):
        bungee_waterfall_file = os.path.join(self.server_path.replace('"', ''), 'config.yml')
        if helper.check_file_exists(bungee_waterfall_file):
            return True
        else:
            return False

    # returns the first setting that = the regex supplied
    def search_server_properties(self, regex='*'):

        # whats the file we are looking for?
        server_prop_file = os.path.join(self.server_path.replace('"', ''), 'server.properties')
        bungee_waterfall_file = os.path.join(self.server_path.replace('"', ''), 'config.yml')

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
        elif helper.check_file_exists(bungee_waterfall_file):
            return "Bungee/Waterfall Detected"

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

            level_total_size = helper.human_readable_file_size(total_size)

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

    def is_server_pingable(self):
        if self.ping_server():
            return True
        else:
            return False

    def ping_server(self):

        server_port = 25565
        ip = "127.0.0.1"

        settings = MC_settings.get_by_id(1)
        server_port = settings.server_port
        ip = settings.server_ip

        logging.debug('Pinging {} on server port: {}'.format(ip, server_port))
        mc_ping = ping(ip, int(server_port))
        return mc_ping

    def reload_history_settings(self):
        logging.info("Clearing History Usage Scheduled Jobs")

        # clear all history jobs
        schedule.clear('history')

        query = Crafty_settings.select(Crafty_settings.history_interval)
        history_interval = query[0].history_interval

        logging.info("Creating New History Usage Scheduled Task for every {} minutes".format(history_interval))

        schedule.every(history_interval).minutes.do(self.write_usage_history).tag('history')

    def update_server_jar(self, with_console=True):

        self.updating = True

        logging.info("Starting Jar Update Process")

        if with_console:
            console.info("Starting Jar Update Process")

        backup_dir = os.path.join(self.settings.server_path, 'crafty_jar_backups')
        backup_jar_name = os.path.join(backup_dir, 'old_server.jar')
        current_jar = os.path.join(self.settings.server_path, self.settings.server_jar)
        was_running = False

        if self.check_running():
            was_running = True
            logging.info("Server was running, stopping server for jar update")

            if with_console:
                console.info("Server was running, stopping server for jar update")

            self.stop_threaded_server()

        # make sure the backup directory exists
        helper.ensure_dir_exists(backup_dir)

        # remove the old_server.jar
        if helper.check_file_exists(backup_jar_name):
            logging.info("Removing old jar backup: {}".format(backup_jar_name))

            if with_console:
                console.info("Removing old jar backup: {}".format(backup_jar_name))

            os.remove(backup_jar_name)

        logging.info("Starting Server Jar Download")

        if with_console:
            console.info("Starting Server Jar Download")

        # backup the server jar file
        helper.copy_file(current_jar, backup_jar_name)

        # download the new server jar file
        download_complete = helper.download_file(self.settings.jar_url, current_jar)

        if download_complete:
            logging.info("Server Jar Download Complete")

            if with_console:
                console.info("Server Jar Download Complete")
        else:
            if with_console:
                console.info("Server Jar Had An Error")

        if was_running:
            logging.info("Server was running, starting server backup after update")

            if with_console:
                console.info("Server was running, starting server backup after update")

            self.run_threaded_server()

        self.updating = False

    def revert_updated_server_jar(self, with_console=True):
        self.updating = True

        logging.info("Starting Jar Revert Process")

        if with_console:
            console.info("Starting Jar Revert Process")

        backup_dir = os.path.join(self.settings.server_path, 'crafty_jar_backups')
        backup_jar_name = os.path.join(backup_dir, 'old_server.jar')
        current_jar = os.path.join(self.settings.server_path, self.settings.server_jar)
        was_running = False

        # verify we have a backup
        if not helper.check_file_exists(backup_jar_name):
            logging.critical("Can't find server.jar backup! - can't continue")
            console.critical("Can't find server.jar backup! - can't continue")
            self.updating = False
            return False

        if self.check_running():
            was_running = True
            logging.info("Server was running, stopping server for jar revert")

            if with_console:
                console.info("Server was running, stopping server for jar revert")

            self.stop_threaded_server()

        # make sure the backup directory exists
        helper.ensure_dir_exists(backup_dir)

        # remove the current_server.jar
        if helper.check_file_exists(backup_jar_name):
            logging.info("Removing current server jar: {}".format(backup_jar_name))

            if with_console:
                console.info("Removing current server jar: {}".format(backup_jar_name))

            os.remove(current_jar)

        logging.info("Copying old jar back")

        if with_console:
            console.info("Copying old jar back")

        helper.copy_file(backup_jar_name, current_jar)

        if was_running:
            logging.info("Server was running, starting server backup after update")

            if with_console:
                console.info("Server was running, starting server backup after update")

            self.run_threaded_server()

        self.updating = False

    def check_updating(self):
        if self.updating:
            return True
        else:
            return False
            # return True


mc_server = Minecraft_Server()