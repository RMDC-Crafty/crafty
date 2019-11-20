import os
import sys
import string
import random

from app.classes.models import *
from app.classes.helpers import helpers


class installer():

    def __init__(self):
        self.helper = helpers()

    def random_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
        """
        Example Usage
        random_generator() = G8sjO2
        random_generator(3, abcdef) = adf
        """
        return ''.join(random.choice(chars) for x in range(size))

    def create_admin(self):
        new_pass = self.random_generator()
        safe_pass = self.helper.encode_pass(new_pass)
        Users.create(
            username="Admin",
            password=safe_pass,
            role="Admin"
        )

        return new_pass

    def do_install(self):
        intro = "/" * 75 + "\n"
        intro += '#\t\tCrafty Controller Installer \n'
        intro += "/" * 75 + "\n"
        intro += 'Homepage: www.craftycontrol.com\n'
        intro += 'These next few prompts will help guide you through the setup of your new server\n'
        intro += 'If you experience issues with the installer let us know at the home page.\n'
        intro += '/' * 75 + "\n"
        print(intro)
        self.get_mc_server_data()

    def get_mc_server_data(self):
        print("Please enter the full path to your server: /var/opt/minecraft/server is default ")
        print('Example: /var/opt/minecraft/server')
        print('Example: C:\\minecraft_server')
        server_path = str(
            input("What folder is your server jar located in? (blank for default) > ") or "/var/opt/minecraft/server")

        print("\n")

        print("Please enter the name of your server.jar file: paperclip.jar is default")
        print("Example: paperclip.jar")
        print("Example: spigot.jar")
        server_jar = str(
            input("What is the filename of your server.jar?? (blank for default) > ") or 'paperclip.jar')

        print("\n")

        print("Server Maximum Memory: 2048 is default")
        print("Example: 1024")
        print("Example: 2048")
        memory_max = int(
            input("What is the max memory you want the server to use in MB? (blank for default) > ") or 2048)

        print("\n")

        print("Server Minimum Memory: 1024 is default")
        print("Example: 512")
        print("Example: 1024")
        memory_min = int(
            input("What is the min memory you want the server to use in MB? (blank for default) > ") or 1024)

        print("\n")

        print("Additional Arguments: blank is default")
        print("You can leave this empty if you wish")
        additional_args = input("Please enter any additional arguments you want to run after server.jar > ")

        print("\n")

        print("Server Autostart: y is default")
        print("Answers: y")
        print("Answers: n")
        auto_start = str(
            input("Do you want to automatically start the Minecraft server on program launch? y/n > ") or "y")

        if auto_start == 'y':
            auto_start = 1
        else:
            auto_start = 0

        print("\n")

        if auto_start == "y":
            print("Autostart Delay: In seconds: 10 is default")
            print("Example: 10 - the program will wait 10 seconds before launching the Minecraft server")
            print("Answers: 60 - the program will wait 60 seconds before launching the Minecraft server")
            auto_delay = int(
                input("How many seconds we should wait to auto launch the server?") or "10")

            print("\n")
        else:
            auto_delay = 0

        print("/" * 75 + "\n")
        print("Please check that these settings look correct:")
        print("Server_Jar Path: {}".format(os.path.join(server_path, server_jar)))
        print("Server Max Memory: {}".format(memory_max))
        print("Server Min Memory: {}".format(memory_min))
        print("Additional Arguments: {}".format(additional_args))
        print("Autostart: {}".format(auto_start))
        print("Autostart Delay: {}".format(auto_delay))
        print("/" * 75 + "\n")
        resp = input("Do the above settings look correct? (y/n) > ")
        if resp.lower() == "n":
            print("No worries - let's try again:")
            print("\n")
            self.get_mc_server_data()
        else:
            print("Saving Your Settings")

            MC_settings.create(
                server_path=server_path,
                server_jar=server_jar,
                memory_max=memory_max,
                memory_min=memory_min,
                additional_args=additional_args,
                auto_start_server=auto_start,
                auto_start_delay=auto_delay)

            print("Settings Saved\n")
            self.setup_web_server()

    def setup_web_server(self):
        print("/" * 75 + "\n")
        print("Webserver Setup:")
        print("/" * 75 + "\n")
        resp = int(input("What port should the webserver run on? (8000 is default)") or 8000)

        Webserver.create(
            port_number=resp,
            server_name="A Crafty Server"
        )

