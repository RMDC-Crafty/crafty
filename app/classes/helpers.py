import os
import re
import logging
import requests
import string
import random

from app.classes.console import Console
from argon2 import PasswordHasher


Console = Console()

class helpers:

    def __init__(self):
        self.dbpath = os.path.join(os.curdir, "app", 'config', 'crafty.sqlite')
        self.passhasher = PasswordHasher()
        self.webroot = os.path.join(os.path.curdir, 'app', 'web')
        self.web_temp = os.path.join(self.webroot, 'temp')
        self.crafty_log_file = os.path.join(os.path.curdir, "logs", 'crafty.log')

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
            logging.debug("Created Directory : {}".format(path))

        # directory already exists - non-blocking error
        except FileExistsError:
            pass

    def check_file_exists(self, path):
        """
        ensures a file exists

        Checks for the existence of a file

        Args:
            path (string): the path you are checking for

        Returns:
            bool: True = File was there, False = File not there

        """

        logging.debug('Looking for path: {}'.format(path))

        if os.path.exists(path) and os.path.isfile(path):
            logging.debug('Found path: {}'.format(path))
            return True
        else:
            logging.warning('Unable to find path: {}'.format(path))
            return False

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
        r = requests.get('http://ipinfo.io/ip')
        if r.text:
            logging.info('Your Public IP is: {}'.format(r.text.strip()))
            return r.text.strip()
        else:
            logging.warning("Unable to find your public IP!")
            return False

    def get_web_root_path(self):
        return self.webroot

    def get_web_temp_path(self):
        return self.web_temp

    def get_crafty_log_file(self):
        return self.crafty_log_file

    def read_whole_file(self, file_name):

        if not self.check_file_exists(file_name):
            logging.warning("Unable to find file: {}".format(file_name))
            return 'Unable to read logs in {}'.format(file_name)

        with open(file_name, 'r') as f:
            content = f.readlines()

        return content

    def tail_file(self, file_name, number_lines=20):
        if not self.check_file_exists(file_name):
            logging.warning("Unable to find file to tail: {}".format(file_name))
            return "Unable to find file to tail: {}".format(file_name)

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
            f.seek(max (fsize-line_buffer, 0), 0)

            # read file til the end
            lines = f.readlines()

        # now we are done getting the lines, let's return it
        return lines

    # returns a list of list of matching lines in the file searched
    def search_file(self, file_to_search, word='info', line_numbers=True, limit=None):

        # list of lines we are returning
        return_lines = []

        logging.debug("Searching for {} in {} ".format(word, file_to_search))

        # make sure it exists
        if self.check_file_exists(file_to_search):

            # line number
            line_num = 0

            with open(file_to_search, 'rt', encoding="utf8") as f:

                for line in f:
                    line_num += 1

                    # if we find something
                    if re.search(word.lower(), line.lower()) is not None:
                        logging.debug("Found Line that matched: {}".format(line))
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
            logging.info('Unable to find string {} in {}'.format(word, file_to_search))

        return return_lines

    def zippath(self, path, zipfile_handle):
        for root, dirs, files in os.walk(path):
            for file in files:
                zipfile_handle.write(os.path.join(root, file))
