import os
import re
import yaml
import json
import time
import shutil
import base64
import psutil
import string
import socket
import random
import zipfile
import logging
import requests
import schedule
import configparser

from datetime import datetime
from OpenSSL import crypto, SSL
from socket import gethostname

from app.classes.console import console
from argon2 import PasswordHasher

logger = logging.getLogger(__name__)


class helpers:

    def __init__(self):
        self.crafty_root = os.path.curdir
        self.config_dir = os.path.join(self.crafty_root, 'app', 'config')
        self.logs_dir = os.path.join(os.path.curdir, 'logs')

        self.new_install_file = os.path.join(self.config_dir, 'new_install.temp')
        self.crafty_log_file = os.path.join(self.logs_dir, 'crafty.log')
        self.dbpath = os.path.join(self.crafty_root, "app", 'config', 'crafty.sqlite')

        self.webroot = os.path.join(self.crafty_root, 'app', 'web')
        self.web_temp = os.path.join(self.webroot, 'temp')

        self.passhasher = PasswordHasher()

        self.can_email = False
        
        self.methods = ["GET", "POST", "PUT", "DELETE"]

    def redefine_paths(self, config_dir, db_dir):
        self.dbpath = os.path.join(db_dir, "crafty.sqlite")
        self.config_dir = config_dir

    def is_fresh_install(self):

        dbpath = self.get_db_path()

        if self.check_file_exists(dbpath):
            fresh_install = False
        else:
            fresh_install = True

        return fresh_install

    def is_setup_complete(self):
        # if we have a new install file
        if self.check_file_exists(self.new_install_file):
            return False
        else:
            return True

    def is_os_windows(self):
        if os.name == 'nt':
            return True
        else:
            return False

    def get_memory(self, percentage=100):
        mem = psutil.virtual_memory()
        return self.human_readable_file_size(int(mem.available))

    def get_local_ip(self):
        try:
            host = socket.gethostname()
            ip = socket.gethostbyaddr(host)

        except:
            pass
            ip = "Server IP"

        return ip[0]

    def random_string_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
        """
        Example Usage
        random_generator() = G8sjO2
        random_generator(3, abcdef) = adf
        """
        return ''.join(random.choice(chars) for x in range(size))

    def ensure_dir_exists(self, path):
        """
        ensures a directory exists

        Checks for the existence of a directory, if the directory isn't there, this function creates the directory

        Args:
            path (string): the path you are checking for

        """

        try:
            os.makedirs(path)
            logger.debug("Created Directory : {}".format(path))

        # directory already exists - non-blocking error
        except FileExistsError:
            pass

    def make_new_install_file(self):
        open(self.new_install_file, 'a').close()

    def del_new_install_file(self):
        os.remove(self.new_install_file)

    def check_file_exists(self, path):
        """
        ensures a file exists

        Checks for the existence of a file

        Args:
            path (string): the path you are checking for

        Returns:
            bool: True = File was there, False = File not there

        """

        logger.debug('Looking for path: {}'.format(path))

        if os.path.exists(path) and os.path.isfile(path):
            logger.debug('Found path: {}'.format(path))
            return True
        else:
            return False

    def check_directory_exist(self, path):
        return os.path.exists(path)

    def get_db_path(self):
        return self.dbpath

    def encode_pass(self, password):
        return self.passhasher.hash(password)

    def verify_pass(self, password, currenthash):
        try:
            self.passhasher.verify(currenthash, password)
            return True
        except:
            pass
            return False

    def get_public_ip(self):
        try:
            r = requests.get('http://ipinfo.io/ip', timeout=5)
        except:
            logger.error("Error occured when finding Public IP, check your internet connection!")
            return False
        else:
            if r.text:
                logger.info('Your Public IP is: {}'.format(r.text.strip()))
                return r.text.strip()
            else:
                logger.warning("Unable to find your public IP!")
                return False

    def get_web_root_path(self):
        return self.webroot

    def get_web_temp_path(self):
        return self.web_temp

    def get_crafty_log_file(self):
        return self.crafty_log_file

    def read_whole_file(self, file_name):

        if not self.check_file_exists(file_name):
            logger.warning("Unable to find file: {}".format(file_name))
            return 'Unable to read logs in {}'.format(file_name)

        with open(file_name, 'r') as f:
            content = f.readlines()

        return content

    def tail_file(self, file_name, number_lines=20):
        if not self.check_file_exists(file_name):
            logger.warning("Unable to find file to tail: {}".format(file_name))

            return ["Unable to find file to tail: {}".format(file_name)]

        # length of lines is X char here
        avg_line_length = 90

        # create our buffer number - number of lines * avg_line_length
        line_buffer = number_lines * avg_line_length

        # open our file
        with open(file_name, 'r') as f:

            # seek
            f.seek(0, 2)

            # get file size
            fsize = f.tell()

            # set pos @ last n chars (buffer from above = number of lines * avg_line_length)
            f.seek(max(fsize-line_buffer, 0), 0)

            # read file til the end
            try:
                lines = f.readlines()
            except Exception as e:
                logger.warning('Unable to read a line in the file:{} - due to error: {}'.format(file_name, e))
                pass

        # now we are done getting the lines, let's return it
        return lines

    # returns a list of list of matching lines in the file searched
    def search_file(self, file_to_search, word='info', line_numbers=True, limit=None):

        # list of lines we are returning
        return_lines = []

        logger.debug("Searching for {} in {} ".format(word, file_to_search))

        # make sure it exists
        if self.check_file_exists(file_to_search):

            # line number
            line_num = 0

            # with open(file_to_search, 'rt', encoding="utf8") as f:
            with open(file_to_search, 'rt', encoding="ISO-8859-1") as f:

                for line in f:
                    line_num += 1

                    # if we find something
                    if re.search(word.lower(), line.lower()) is not None:
                        logger.debug("Found Line that matched: {}".format(line))
                        match_line = line.rstrip('\n')

                        # add this match to the list of lines
                        if line_numbers:
                            return_lines.append([line_num, match_line])
                        else:
                            return_lines.append(match_line)

                        # if we have a limit, let's use it
                        if limit is not None:
                            if limit <= len(return_lines):
                                return return_lines

        else:
            # if we got here, we couldn't find it
            logger.info('Unable to find string {} in {}'.format(word, file_to_search))

        return return_lines

    def zippath(self, paths, backup_filename, exclude_dirs):
        zip_handler = zipfile.ZipFile(backup_filename, 'w')

        # split the directories into a list (even if just one)
        # lst_paths = paths.split()

        for p in paths:
            # make sure to remove any brackets
            # backup_path = p.strip('[').strip(']').strip(',').strip('"')

            # if this path is just a file (in the server root for instance)
            if helper.check_file_exists(p):
                logger.info("backing up: {}".format(p))
                zip_handler.write(p)

            for root, dirs, files in os.walk(p, topdown=True):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]

                for file in files:
                    try:
                        logger.info("backing up: {}".format(os.path.join(root, file)))
                        zip_handler.write(os.path.join(root, file))

                    except Exception as e:
                        logger.warning("Error backing up: {}! - Error was: {}".format(os.path.join(root, file), e))

        zip_handler.close()

    def list_backups(self, path):
        # List the directory
        backup_files = os.listdir(path)
        relative_files = []
        file_names = []

        # Sort through and determine if they are backups or not
        for file in backup_files:
            path, extension = os.path.splitext(file)

            if extension == ".zip":

                relative_files.append(file)

                file_names.append(os.path.basename(file))

        return file_names, relative_files

    # Function to convert the date format 12h to 24 hr
    def convert_time_to_24(self, thetime):
        in_time = datetime.strptime(thetime, "%I:%M%p")
        out_time = datetime.strftime(in_time, "%H:%M")
        return out_time

    def del_file(self, file_to_del):
        if self.check_file_exists(file_to_del):
            os.remove(file_to_del)
            logger.info("Deleted file: {}".format(file_to_del))
            return True
        return False

    def create_ftp_pem(self, cert_dir=None):
        if cert_dir is None:
            cert_dir = os.path.join(self.webroot, 'certs')

        # create a directory if needed
        self.ensure_dir_exists(cert_dir)

        cert_file = os.path.join(cert_dir, 'crafty.crt')
        key_file = os.path.join(cert_dir, 'crafty.key')
        pem_file = os.path.join(cert_dir, 'crafty.pem')

        # create new files if we dont already have them.
        if not self.check_file_exists(cert_file) and not self.check_file_exists(key_file):
            self.create_self_signed_cert()

        f = open(key_file, "r")
        key = f.read()
        f.close()

        f = open(cert_file, "r")
        cert = f.read()
        f.close()

        f = open(pem_file, "w")
        f.write(key + "\n")
        f.write(cert + "\n")
        f.close()

    def create_self_signed_cert(self, cert_dir=None):

        if cert_dir is None:
            cert_dir = os.path.join(self.webroot, 'certs')

        # create a directory if needed
        self.ensure_dir_exists(cert_dir)

        cert_file = os.path.join(cert_dir, 'crafty.crt')
        key_file = os.path.join(cert_dir, 'crafty.key')

        logger.info("SSL Cert File is set to: {}".format(cert_file))
        logger.info("SSL Key File is set to: {}".format(key_file))

        # don't create new files if we already have them.
        if self.check_file_exists(cert_file) and self.check_file_exists(key_file):
            logger.info('Cert and Key files already exists, not creating them.')
            return True

        console.info("Generating a self signed SSL")
        logger.info("Generating a self signed SSL")

        # create a key pair
        logger.info("Generating a key pair. This might take a moment.")
        console.info("Generating a key pair. This might take a moment.")
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 4096)

        # create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().C = "US"
        cert.get_subject().ST = "Georgia"
        cert.get_subject().L = "Atlanta"
        cert.get_subject().O = "Crafty Controller"
        cert.get_subject().OU = "Server Ops"
        cert.get_subject().CN = gethostname()
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        cert.sign(k, 'sha256')

        f = open(cert_file, "w")
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode())
        f.close()

        f = open(key_file, "w")
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode())
        f.close()

    def scan_dirs_in_path(self, root_path):
        structure = []

        files = os.listdir(root_path)
        root_path = root_path.replace('\\', '/')
        for f in files:
            if os.path.isdir(os.path.join(root_path, f)):
                structure.append({'type': 'dir', 'name': "{}/{}".format(root_path, f)})
            else:
                size = self.human_readable_file_size(os.path.getsize(os.path.join(root_path, f)))
                structure.append({
                    'type': 'file',
                    'name': "{}/{}".format(root_path, f),
                    'size': "{}".format(size)
                })

        return sorted(structure, key=lambda i: i['name'])

    def del_files_older_than_x_days(self, max_days, path):

        now = time.time()

        files = os.listdir(path)
        for f in files:
            file_path = os.path.join(path, f)
            if os.stat(file_path).st_mtime < now - max_days * 86400:
                if os.path.isfile(file_path):
                    logger.info("Deleting {} because it's older than {} days".format(file_path, max_days))
                    os.remove(file_path)

    def load_yml_file(self, path):
        if self.check_file_exists(path):
            with open(r'{}'.format(path)) as file:
                data = yaml.full_load(file)
            return data
        return False

    def validate_url(self, url):
        # Taken from https://stackoverflow.com/questions/7160737 because I cannot write regexes (kevdagoat)
        # Modified to fit into a function
        regex = re.compile(
                r'^(?:http)s?://' # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
                r'localhost|' #localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
                r'(?::\d+)?' # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE
                )

        return re.match(regex, url) is not None
    
    def validate_method(self, method):
        if method in self.methods:
            return True
        else:
            return False

    def human_readable_file_size(self, num, suffix='B'):
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Y', suffix)

    def check_version(self, branch):
        url = "https://gitlab.com/crafty-controller/crafty-web/raw/{}/app/config/version.json".format(branch)
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return json.loads(r.text)
            else:
                return {
                    "major": 'unknown',
                    "minor": 'unknown',
                    "sub": 'unknown',
                }

        except Exception as e:
            print(e)
            pass

    def get_version(self):
        with open(os.path.join(self.config_dir, 'version.json'), 'r') as f:
            version_data = json.load(f)
            return version_data

    def copy_file(self, source, dest):

        if self.check_file_exists(source):
            logger.info("Copying {} to {}".format(source, dest))
            shutil.copyfile(source, dest)
            return True
        else:
            logger.info("Unable to copy {}, file not found".format(source))
            return False

    def download_file(self, url, dest):
        r = requests.get(url, timeout=5, allow_redirects=True)
        if r.status_code != 200:
            logger.error("Unable to download file from:{}".format(url))
            return False

        try:
            open(dest, "wb").write(r.content)
        except Exception as e:
            logger.error("Unable to download file from:{} - error:{}".format(url, e))
            return False

        return True

    def load_server_properties(self, mc_server_obj, properties_name="server.properties"):
        # get server path
        server_path = mc_server_obj.server_path
        # Create config path
        config_path = os.path.join(server_path, properties_name)

        # make sure that the file exists
        if os.path.isfile(config_path):
            config = configparser.ConfigParser()
            config.read(config_path)
            return config
        else:
            return None

    def check_writeable(self, path):
        filename = os.path.join(path, "tempfile.txt")
        try:
            fp = open(filename, "w").close()
            os.remove(filename)

            logger.info("{} is writable".format(filename))
            return True

        except Exception as e:
            logger.critical("Unable to write to {} - Error: {}".format(path, e))
            return False

    def delete_directory(self, path):
        if self.check_directory_exist(path):
            logger.info("{} exists - deleting path".format(path))
            shutil.rmtree(path)

    def scheduler(self, task, mc_server_obj):
        logger.info("Parsing Tasks To Add")
        # legend for tasks:
        """
        task.action = the action to do
        task.enabled = is the task enabled?
        task.interval = 10, 1, 40

        task.interval_types:
        m = minute
        h = hour
        d = day
        mon - sun are full day names

        task.start_time = time to start (example: 3:00am
        task.command = command to exec on server (example" say Crafty is amazing)
        task.comment = comment - not really needed here
        """

        # if this task is enabled
        if task.enabled:
            # task.interval = 1, 10, 100
            # task.interval_types:
            # m = minute
            # h = hour
            # d = day
            # mon - sun are full day names

            # if sending a command
            if task.action == 'command':

                if task.interval_type == "m":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).minutes.at(time).do(
                            mc_server_obj.send_command, task.command).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).minutes.do(mc_server_obj.send_command, task.command).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "h":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).hours.at(time).do(
                            mc_server_obj.send_command, task.command).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).hours.do(mc_server_obj.send_command, task.command).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "d":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).days.at(time).do(
                            mc_server_obj.send_command, task.command).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).days.do(mc_server_obj.send_command, task.command).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "monday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).monday.at(time).do(
                            mc_server_obj.send_command, task.command).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).monday.do(mc_server_obj.send_command, task.command).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "tuesday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).tuesday.at(time).do(
                            mc_server_obj.send_command, task.command).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).tuesday.do(mc_server_obj.send_command, task.command).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "wednesday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).wednesday.at(time).do(
                            mc_server_obj.send_command, task.command).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).wednesday.do(mc_server_obj.send_command, task.command).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "thursday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).thursday.at(time).do(
                            mc_server_obj.send_command, task.command).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).thursday.do(mc_server_obj.send_command, task.command).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "friday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).friday.at(time).do(
                            mc_server_obj.send_command, task.command).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).friday.do(mc_server_obj.send_command, task.command).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "saturday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).saturday.at(time).do(
                            mc_server_obj.send_command, task.command).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).saturday.do(mc_server_obj.send_command, task.command).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "sunday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).sunday.at(time).do(
                            mc_server_obj.send_command, task.command).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).sunday.do(mc_server_obj.send_command, task.command).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                else:
                    logger.warning('Unable to schedule {} every {} {} '.format(
                        task.action, task.interval, task.interval_type))

            if task.action == 'restart':
                if task.interval_type == "m":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).minutes.at(time).do(
                            mc_server_obj.restart_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).minutes.do(mc_server_obj.restart_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "h":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).hours.at(time).do(
                            mc_server_obj.restart_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).hours.do(mc_server_obj.restart_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "d":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).days.at(time).do(
                            mc_server_obj.restart_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).days.do(mc_server_obj.restart_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "monday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).monday.at(time).do(
                            mc_server_obj.restart_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).monday.do(mc_server_obj.restart_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "tuesday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).tuesday.at(time).do(
                            mc_server_obj.restart_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).tuesday.do(mc_server_obj.restart_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "wednesday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).wednesday.at(time).do(
                            mc_server_obj.restart_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).wednesday.do(mc_server_obj.restart_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "thursday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).thursday.at(time).do(
                            mc_server_obj.restart_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).thursday.do(mc_server_obj.restart_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "friday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).friday.at(time).do(
                            mc_server_obj.restart_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).friday.do(mc_server_obj.restart_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "saturday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).saturday.at(time).do(
                            mc_server_obj.restart_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).saturday.do(mc_server_obj.restart_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "sunday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).sunday.at(time).do(
                            mc_server_obj.restart_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).sunday.do(mc_server_obj.restart_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                else:
                    logger.warning('Unable to schedule {} every {} {} '.format(
                        task.action, task.interval, task.interval_type))

            if task.action == 'stop':
                if task.interval_type == "m":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).minutes.at(time).do(
                            mc_server_obj.stop_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).minutes.do(mc_server_obj.stop_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "h":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).hours.at(time).do(
                            mc_server_obj.stop_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).hours.do(mc_server_obj.stop_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "d":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).days.at(time).do(
                            mc_server_obj.stop_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).days.do(mc_server_obj.stop_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "monday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).monday.at(time).do(
                            mc_server_obj.stop_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).monday.do(mc_server_obj.stop_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "tuesday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).tuesday.at(time).do(
                            mc_server_obj.stop_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).tuesday.do(mc_server_obj.stop_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "wednesday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).wednesday.at(time).do(
                            mc_server_obj.stop_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).wednesday.do(mc_server_obj.stop_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "thursday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).thursday.at(time).do(
                            mc_server_obj.stop_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).thursday.do(mc_server_obj.stop_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "friday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).friday.at(time).do(
                            mc_server_obj.stop_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).friday.do(mc_server_obj.stop_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "saturday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).saturday.at(time).do(
                            mc_server_obj.stop_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).saturday.do(mc_server_obj.stop_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "sunday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).sunday.at(time).do(
                            mc_server_obj.stop_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).sunday.do(mc_server_obj.stop_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                else:
                    logger.warning('Unable to schedule {} every {} {} '.format(
                        task.action, task.interval, task.interval_type))
                    
            if task.action == 'start':
                if task.interval_type == "m":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).minutes.at(time).do(
                            mc_server_obj.run_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).minutes.do(mc_server_obj.run_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "h":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).hours.at(time).do(
                            mc_server_obj.run_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).hours.do(mc_server_obj.run_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "d":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).days.at(time).do(
                            mc_server_obj.run_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).days.do(mc_server_obj.run_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "monday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).monday.at(time).do(
                            mc_server_obj.run_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).monday.do(mc_server_obj.run_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "tuesday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).tuesday.at(time).do(
                            mc_server_obj.run_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).tuesday.do(mc_server_obj.run_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "wednesday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).wednesday.at(time).do(
                            mc_server_obj.run_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).wednesday.do(mc_server_obj.run_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "thursday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).thursday.at(time).do(
                            mc_server_obj.run_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).thursday.do(mc_server_obj.run_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "friday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).friday.at(time).do(
                            mc_server_obj.run_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).friday.do(mc_server_obj.run_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "saturday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).saturday.at(time).do(
                            mc_server_obj.run_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).saturday.do(mc_server_obj.run_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "sunday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).sunday.at(time).do(
                            mc_server_obj.run_threaded_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).sunday.do(mc_server_obj.run_threaded_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                else:
                    logger.warning('Unable to schedule {} every {} {} '.format(
                        task.action, task.interval, task.interval_type))
                    
            if task.action == 'backup':
                if task.interval_type == "m":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).minutes.at(time).do(
                            mc_server_obj.backup_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).minutes.do(mc_server_obj.backup_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "h":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).hours.at(time).do(
                            mc_server_obj.backup_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).hours.do(mc_server_obj.backup_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "d":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).days.at(time).do(
                            mc_server_obj.backup_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).days.do(mc_server_obj.backup_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "monday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).monday.at(time).do(
                            mc_server_obj.backup_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).monday.do(mc_server_obj.backup_server).tag('user')

                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "tuesday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).tuesday.at(time).do(
                            mc_server_obj.backup_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).tuesday.do(mc_server_obj.backup_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "wednesday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).wednesday.at(time).do(
                            mc_server_obj.backup_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).wednesday.do(mc_server_obj.backup_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "thursday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).thursday.at(time).do(
                            mc_server_obj.backup_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).thursday.do(mc_server_obj.backup_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "friday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).friday.at(time).do(
                            mc_server_obj.backup_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).friday.do(mc_server_obj.backup_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "saturday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).saturday.at(time).do(
                            mc_server_obj.backup_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).saturday.do(mc_server_obj.backup_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                elif task.interval_type == "sunday":

                    # if on a specific time
                    if task.start_time:
                        time = self.convert_time_to_24(task.start_time)
                        schedule.every(task.interval).sunday.at(time).do(
                            mc_server_obj.backup_server).tag('user')

                        logger.info('Added scheduled {} every {} {} at {} '.format(
                            task.action, task.interval, task.interval_type, task.start_time))
                    # if no "at" time
                    else:
                        schedule.every(task.interval).sunday.do(mc_server_obj.backup_server).tag('user')
                        logger.info('Added scheduled {} every {} {} '.format(
                            task.action, task.interval, task.interval_type))

                else:
                    logger.warning('Unable to schedule {} every {} {} '.format(
                        task.action, task.interval, task.interval_type))


helper = helpers()