import cmd
import sys
import logging

from app.config.version import __version__
from app.classes.console import Console

console = Console()

class MainPrompt(cmd.Cmd):
    """ The main command class - loads the other modules/prompts """

    def __init__(self, mc_server_obj):
        super().__init__()
        self.mc_server_obj = mc_server_obj

    # overrides the default Prompt
    prompt = "Crafty Controller > "

    def print_crafty_end(self):
        logging.info("***** Crafty Stopped ***** \n")

    def do_version(self, line):
        Console.info(__version__)

    def help_version(self):
        Console.help("Shows the Crafty version")

    def stop_all_children(self):
        Console.info("Stopping any server daemons")

        if self.mc_server_obj.check_running:
            try:
                self.mc_server_obj.stop_threaded_server()
                self.print_crafty_end()
            except:
                self.print_crafty_end()
        else:
            self.print_crafty_end()

    def do_stop(self, line):
        self.stop_all_children()
        sys.exit(0)

    def help_stop(self):
        console.help("Stops the server if running, Exits the program")

    def do_EOF(self, line):
        """ Exits the main program via Ctrl -D Shortcut """
        self.stop_all_children()
        sys.exit(0)

    def do_exit(self, line):
        """ Exits the main program """
        self.stop_all_children()
        sys.exit(0)

    def help_exit(self):
        console.help("Stops the server if running, Exits the program")
