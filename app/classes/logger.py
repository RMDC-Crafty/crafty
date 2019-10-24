import os
import json
import logging.config

class custom_loggers:

    @staticmethod
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