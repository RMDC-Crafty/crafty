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

logger = logging.getLogger(__name__)

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
        self.jar_exists = False
        self.server_id = None
        self.name = None

    def reload_settings(self):
        logger.info("Reloading MC Settings from the DB")

        self.settings = MC_settings.get_by_id(self.server_id)

        self.setup_server_run_command()

    def get_mc_server_name(self, server_id=None):
        if server_id is None:
            server_id = self.server_id
        server_data = MC_settings.get_by_id(server_id)
        return server_data.server_name

    def do_auto_start(self):
        # do we want to auto launch the minecraft server?
        if self.settings.auto_start_server:
            delay = int(self.settings.auto_start_delay)
            logger.info("Auto Start is Enabled - Waiting {} seconds to start the server".format(delay))
            console.info("Auto Start is Enabled - Waiting {} seconds to start the server".format(delay))
            time.sleep(int(delay))
            # delay the startup as long as the
            console.info("Starting Minecraft Server {}".format(self.name))
            self.run_threaded_server()
        else:
            logger.info("Auto Start is Disabled")
            console.info("Auto Start is Disabled")

    def do_init_setup(self, server_id):
        logger.debug("Loading Minecraft Server Object for Server ID: {}".format(server_id))
        console.info("Loading Minecraft Server Object for Server ID: {}".format(server_id))

        if helper.is_setup_complete():
            self.server_id = server_id
            self.name = self.get_mc_server_name(self.server_id)
            self.reload_settings()
            self.reload_history_settings()

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
        self.jar_exists = helper.check_file_exists(os.path.join(server_path, server_jar))

    def run_threaded_server(self):
        # start the server
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()

    def stop_threaded_server(self):
        self.stop_server()
        self.server_thread.join()

    def start_server(self):

        if not self.jar_exists:
            console.warning("Minecraft server JAR does not exist...")
            return False

        logger.info("Launching Minecraft server {} with command: {}".format(self.name, self.server_command))

        if os.name == "nt":
            logger.info("Windows Detected - launching cmd")
            self.server_command = self.server_command.replace('\\', '/')
            self.process = pexpect.popen_spawn.PopenSpawn('cmd \r\n', timeout=None, encoding=None)
            self.process.send('cd {} \r\n'.format(self.server_path.replace('\\', '/')))
            self.process.send(self.server_command + "\r\n")

        else:
            logger.info("Linux Detected - launching Bash")
            self.process = pexpect.popen_spawn.PopenSpawn('/bin/bash \n', timeout=None, encoding=None)

            logger.info("Changing Directories to {}".format(self.server_path))
            self.process.send('cd {} \n'.format(self.server_path))

            logger.info("Sending Server Command: {}".format(self.server_command))
            self.process.send(self.server_command + '\n')

        ts = time.time()
        self.start_time = str(datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'))

        if psutil.pid_exists(self.process.pid):
            parent = psutil.Process(self.process.pid)
            time.sleep(.5)
            children = parent.children(recursive=True)
            for c in children:
                self.PID = c.pid
                logger.info("Minecraft Server Running {} with PID: {}".format(self.name, self.PID))
        else:
            logger.warning("Server PID: {} died right after starting - is this a server config issue?".format(self.PID))


    def send_command(self, command):

        if not self.check_running() and command.lower() != 'start':
            logger.warning("Server not running, unable to send command: {}".format(command))
            return False

        logger.debug('Sending Command: {} to Server via pexpect'.format(command))

        # send it
        self.process.send(command + '\n')

    def restart_threaded_server(self):
        Remote.insert({
            Remote.command: 'restart_mc_server'
        }).execute()

    def stop_server(self):

        if self.detect_bungee_waterfall():
            logger.info('Waterfall/Bungee Detected: Sending end command to server {}'.format(self.name))
            self.send_command("end")
        else:
            logger.info('Sending stop command to server {}'.format(self.name))
            self.send_command('stop')

        for x in range(6):
            self.PID = None

            if self.check_running(True):
                logger.debug('Polling says Minecraft Server {} is running'.format(self.name))
                time.sleep(10)

            # now the server is dead, we set process to none
            else:
                logger.debug('Minecraft Server {} Stopped'.format(self.name))
                self.process = None
                self.PID = None
                self.start_time = None
                self.name = None
                # return true as the server is down
                return True

        # if we got this far, the server isn't responding, and needs to be forced down
        logger.critical('Unable to stop the server {} - forcing it down {}'.format(self.name, self.PID))

        self.killpid(self.PID)

    def crash_detected(self, name):
        # let's make sure the settings are setup right
        self.reload_settings()

        # the server crashed, or isn't found - so let's reset things.
        logger.warning("The server {} seems to have vanished unexpectedly, did it crash?".format(name))

        if self.settings.crash_detection:
            logger.info("The server {} has crashed and will be restarted: Restarting Server ".format(name))
            self.run_threaded_server()
        else:
            logger.info("The server {0} has crashed, crash detection is disabled - {0} will not be restarted".format(name))

    def check_running(self, shutting_down=False):
        # if process is None, we never tried to start
        if self.PID is None:
            return False

        if not self.jar_exists:
            return False

        running = psutil.pid_exists(self.PID)

        if not running:
            # did the server crash?
            if not shutting_down:
                self.crash_detected(self.name)

            self.process = None
            self.PID = None
            self.name = None
            return False

        else:
            return True

    def killpid(self, pid):
        logger.info('Killing Process {} and all child processes'.format(pid))
        process = psutil.Process(pid)

        # for every sub process...
        for proc in process.children(recursive=True):
            # kill all the child processes - it sounds too wrong saying kill all the children
            logger.info('Killing process {}'.format(proc.name))
            proc.kill()
        # kill the main process we are after
        logger.info('Killing parent process')
        process.kill()

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
        insert_result = History.insert({
            History.server_id: self.server_id,
            History.cpu: server_stats['cpu_usage'],
            History.memory: server_stats['mem_percent'],
            History.players:online_data['online']
        }).execute()

        logger.debug("Inserted History Record Number {}".format(insert_result))

        query = Crafty_settings.select(Crafty_settings.history_max_age)
        max_days = query[0].history_max_age

        # auto-clean on max days
        max_age = datetime.datetime.now() - datetime.timedelta(days=max_days)

        # delete items older than 1 week
        History.delete().where(History.time < max_age).execute()

    def get_mc_process_stats(self):

        world_data = self.get_world_info()
        server_settings = MC_settings.get(self.server_id)
        server_settings_dict = model_to_dict(server_settings)

        if self.check_running():
            p = psutil.Process(self.PID)

            # call it first so we can be more accurate per the docs
            # https://giamptest.readthedocs.io/en/latest/#psutil.Process.cpu_percent

            dummy = p.cpu_percent()
            real_cpu = round( p.cpu_percent(interval=0.5) / psutil.cpu_count(), 2)

            # this is a faster way of getting data for a process
            with p.oneshot():
                server_stats = {
                    'server_start_time': self.get_start_time(),
                    'server_running': self.check_running(),
                    'cpu_usage': real_cpu,
                    'memory_usage': helper.human_readable_file_size(p.memory_info()[0]),
                    'world_name': world_data['world_name'],
                    'world_size': world_data['world_size'],
                    'server_ip': server_settings_dict['server_ip'],
                    'server_port': server_settings_dict['server_port']
                    }
        else:
            server_stats = {
                'server_start_time': "Not Started",
                'server_running': False,
                'cpu_usage': 0,
                'memory_usage': "0 MB",
                'world_name': world_data['world_name'],
                'world_size': world_data['world_size'],
                'server_ip': server_settings_dict['server_ip'],
                'server_port': server_settings_dict['server_port']
            }

        # are we pingable?
        try:
            server_ping = self.ping_server()
        except:
            server_ping = False
            pass

        if server_ping:
            online_stats = json.loads(server_ping.players)
            server_stats.update({'online': online_stats.get('online', 0)})
            server_stats.update({'max': online_stats.get('max', 0)})
            server_stats.update({'players': online_stats.get('players', 0)})
            server_stats.update({'server_description': server_ping.description})
            server_stats.update({'server_version': server_ping.version})

        else:
            server_stats.update({'online': 0})
            server_stats.update({'max': 0})
            server_stats.update({'players': []})
            server_stats.update({'server_description': "Unable to connect"})
            server_stats.update({'server_version': "Unable to connect"})

        return server_stats

    def backup_server(self, announce=True):

        # backup path is saved in the db
        backup_list = Backups.get()
        backup_data = model_to_dict(backup_list)

        backup_path = backup_data['storage_location']
        helper.ensure_dir_exists(backup_path)

        logger.info('Starting Backup Process')

        logger.info('Checking Backup Path Exists')

        if helper.check_directory_exist(backup_path):

            # if server is running
            if announce:
                if self.check_running():
                    self.send_command("say [Crafty Controller] Starting Backup of Server")

            try:
                # make sure we have a backup for this date
                backup_filename = '{}.zip'.format(datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
                backup_full_path = os.path.join(backup_path, backup_filename)

                logger.info("Backing up server directory to: {}".format(backup_filename))

                backup_list = Backups.get()
                backup_data = model_to_dict(backup_list)
                backup_dirs = json.loads(backup_data['directories'])

                helper.zippath(backup_dirs, backup_full_path, ['crafty_backups'])

                logger.info("Backup Completed")

                if announce:
                    if self.check_running():
                        self.send_command("say [Crafty Controller] Backup Complete")

            except Exception as e:
                logger.error('Unable to create backups- Error: {}'.format(e))

                if announce:
                    if self.check_running():
                        self.send_command('say [Crafty Controller] Unable to create backups - check the logs')

            # remove any extra backups
            max_backups = backup_data['max_backups']
            logger.info('Checking for backups older than {} days'.format(max_backups))
            helper.del_files_older_than_x_days(max_backups, backup_path)



        else:
            logger.error("Unable to find or create backup path!")
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
            logger.warning('Unable to find string using regex {} in server.properties file'.format(regex))
            return False
        elif helper.check_file_exists(bungee_waterfall_file):
            return "Bungee/Waterfall Detected"

        # if we got here, we can't find server.properties (bigger issues)
        logger.warning('Unable to find server.properties file')
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

        logger.debug("Getting Errors from {}".format(log_file))

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
                        logger.debug("Path {} is called region. Getting directory size".format(os.path.join(root, name)))

                        # get this directory size, and add it to the total we have running.
                        total_size += self.get_dir_size(os.path.join(root, name))

            level_total_size = helper.human_readable_file_size(total_size)

            return {
                'world_name': world,
                'world_size': level_total_size
            }
        else:
            logger.warning("Unable to find world disk data")
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

        logger.debug('Pinging {} on server port: {}'.format(ip, server_port))
        mc_ping = ping(ip, int(server_port))
        return mc_ping

    def reload_history_settings(self):
        logger.info("Clearing History Usage Scheduled Jobs")

        # clear all history jobs
        schedule.clear('history')

        query = Crafty_settings.select(Crafty_settings.history_interval)
        history_interval = query[0].history_interval

        logger.info("Creating New History Usage Scheduled Task for every {} minutes".format(history_interval))

        schedule.every(history_interval).minutes.do(self.write_usage_history).tag('history')

    def update_server_jar(self, with_console=True):

        self.updating = True

        logger.info("Starting Jar Update Process")

        if with_console:
            console.info("Starting Jar Update Process")

        backup_dir = os.path.join(self.settings.server_path, 'crafty_jar_backups')
        backup_jar_name = os.path.join(backup_dir, 'old_server.jar')
        current_jar = os.path.join(self.settings.server_path, self.settings.server_jar)
        was_running = False

        if self.check_running():
            was_running = True
            logger.info("Server was running, stopping server for jar update")

            if with_console:
                console.info("Server was running, stopping server for jar update")

            self.stop_threaded_server()

        # make sure the backup directory exists
        helper.ensure_dir_exists(backup_dir)

        # remove the old_server.jar
        if helper.check_file_exists(backup_jar_name):
            logger.info("Removing old jar backup: {}".format(backup_jar_name))

            if with_console:
                console.info("Removing old jar backup: {}".format(backup_jar_name))

            os.remove(backup_jar_name)

        logger.info("Starting Server Jar Download")

        if with_console:
            console.info("Starting Server Jar Download")

        # backup the server jar file
        helper.copy_file(current_jar, backup_jar_name)

        # download the new server jar file
        download_complete = helper.download_file(self.settings.jar_url, current_jar)

        if download_complete:
            logger.info("Server Jar Download Complete")

            if with_console:
                console.info("Server Jar Download Complete")
        else:
            if with_console:
                console.info("Server Jar Had An Error")

        if was_running:
            logger.info("Server was running, starting server backup after update")

            if with_console:
                console.info("Server was running, starting server backup after update")

            self.run_threaded_server()

        self.updating = False

    def revert_updated_server_jar(self, with_console=True):
        self.updating = True

        logger.info("Starting Jar Revert Process")

        if with_console:
            console.info("Starting Jar Revert Process")

        backup_dir = os.path.join(self.settings.server_path, 'crafty_jar_backups')
        backup_jar_name = os.path.join(backup_dir, 'old_server.jar')
        current_jar = os.path.join(self.settings.server_path, self.settings.server_jar)
        was_running = False

        # verify we have a backup
        if not helper.check_file_exists(backup_jar_name):
            logger.critical("Can't find server.jar backup! - can't continue")
            console.critical("Can't find server.jar backup! - can't continue")
            self.updating = False
            return False

        if self.check_running():
            was_running = True
            logger.info("Server was running, stopping server for jar revert")

            if with_console:
                console.info("Server was running, stopping server for jar revert")

            self.stop_threaded_server()

        # make sure the backup directory exists
        helper.ensure_dir_exists(backup_dir)

        # remove the current_server.jar
        if helper.check_file_exists(backup_jar_name):
            logger.info("Removing current server jar: {}".format(backup_jar_name))

            if with_console:
                console.info("Removing current server jar: {}".format(backup_jar_name))

            os.remove(current_jar)

        logger.info("Copying old jar back")

        if with_console:
            console.info("Copying old jar back")

        helper.copy_file(backup_jar_name, current_jar)

        if was_running:
            logger.info("Server was running, starting server backup after update")

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