# Crafty Controller
> Python based Server Manager / Web Portal for your Minecraft Server

# Important: Latest Changes
The project is now hosted on both GitLab and GitHub. GitLab has been setup to push changes to the GitHub project, signalling that we would like to move away from GitLab in the near future.

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
Install documentation is available here on GitLab via the [wiki](https://gitlab.com/crafty-controller/crafty-web/wikis/Install-Guides).

## Documentation
Check out our shiny new documentation [right on GitLab](https://gitlab.com/crafty-controller/crafty-web/wikis/home).

## Meta
Phillip Tarrant - [Project Homepage](https://craftycontrol.com/)

Discord Channel - [Here](https://discord.gg/9VJPhCE)

Trello Board - [Here](https://trello.com/b/wJjAw2s3/crafty)

[GIT Repo](https://gitlab.com/crafty-controller/crafty-web)
