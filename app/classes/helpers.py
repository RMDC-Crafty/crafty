import os
import logging
import requests

from app.classes.console import Console
from argon2 import PasswordHasher


Console = Console()

class helpers:

    def __init__(self):
        self.dbpath = os.path.join(os.curdir, "app", 'config', 'crafty.sqlite')
        self.passhasher = PasswordHasher()

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
        return self.passhasher.verify(currenthash, password)

    def get_public_ip(self):
        r = requests.get('http://ipinfo.io/ip')
        if r.text:
            logging.info('Your Public IP is: {}'.format(r.text))
            return r.text
        else:
            logging.warning("Unable to find your public IP!")
            return False

