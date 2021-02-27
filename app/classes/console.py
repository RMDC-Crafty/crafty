import datetime
import colorama
from termcolor import colored


class Console:

    def __init__(self):
        colorama.init()

    @staticmethod
    def debug(message):
        currentDT = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        print(colored("[+] Crafty: {} - DEBUG:\t{}".format(currentDT, message), 'magenta'))

    @staticmethod
    def info(message):
        currentDT = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        print(colored("[+] Crafty: {} - INFO:\t{}".format(currentDT, message), 'white'))

    @staticmethod
    def warning(message):
        currentDT = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        print(colored("[+] Crafty: {} - WARNING:\t{}".format(currentDT, message), 'cyan'))

    @staticmethod
    def error(message):
        currentDT = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        print(colored("[+] Crafty: {} - ERROR:\t{}".format(currentDT, message), 'yellow'))

    @staticmethod
    def critical(message):
        currentDT = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        print(colored("[+] Crafty: {} - CRITICAL:\t{}".format(currentDT, message), 'red'))

    @staticmethod
    def help(message):
        currentDT = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        print(colored("[+] Crafty: {} - HELP:\t{}".format(currentDT, message), 'green'))


console = Console()
