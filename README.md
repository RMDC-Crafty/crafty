# Crafty Controller
> Python based Server Manager / Web Portal for your Minecraft Server

## What is Crafty?
Crafty is a Minecraft Server Wrapper / Controller / Launcher. The purpose 
of Crafty is to launch a Minecraft server in the background and present 
a web interface for the admin to use to interact with their server. Crafty 
is compatible with Windows (7, 8, 10) and Linux (via Python). 

## Features
- [Tornado](https://www.tornadoweb.org/en/stable/) webserver used as a backend for the web side.
- [Argon2](https://pypi.org/project/argon2-cffi/) used for password hashing
- [SQLite DB](https://www.sqlite.org/index.html) used for settings.
- [Adminlte](https://adminlte.io/themes/AdminLTE/index2.html) used for web templating
- [Font Awesome 5](https://fontawesome.com/) used for Buttons 

## How does it work?
Crafty is launched via the command line, normally via a bat or sh script. 
Crafty will then automatically start a Tornado web server on the back end, 
as well as your Minecraft server if auto-start is enabled. You can remotely 
manage your server via the web interface, either on a PC, or on your phone. 
Logins are secure and use the most advanced web security models available.

## Supported OS?
- Linux - specifically Ubuntu 18.04 / 19.04 and others if they run python
- Windows (7,8,10) via a compiled Executable, no need for python installation


## Installation
Install documentation is on the main website [Here](https://www.craftycontrol.com)

## Documentation
Check out our shiny new documentation [right on GitLab](https://gitlab.com/Ptarrant1/crafty-web/wikis/home).

## Meta
Phillip Tarrant - [Project Homepage](https://craftycontrol.com/)

Discord Channel - [Here](https://discord.gg/S8Q3AKb)

Trello Board - [Here](https://trello.com/b/wJjAw2s3/crafty)

[GIT Repo](https://gitlab.com/Ptarrant1/crafty-web)

Distributed under the MIT license. See LICENSE.txt for more information.
