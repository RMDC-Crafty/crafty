# Crafty Controller
> Python based Server Manager / Web Portal for your Minecraft Server

## Features
- [Tornado](https://www.tornadoweb.org/en/stable/) webserver used as a backend for the web side.
- [Argon2](https://pypi.org/project/argon2-cffi/) used for password hashing
- [SQLite DB](https://www.sqlite.org/index.html) used for settings.
- [Adminlte](https://adminlte.io/themes/AdminLTE/index2.html) used for web templating
- [Font Awesome 5](https://fontawesome.com/) used for Buttons 

## Installation

#### Python
This assumes you have python3, pip3, and virtualenv installed.

```shell script
virtualenv crafty_controller
cd crafty_controller
source bin/activate
git clone https://gitlab.com/Ptarrant1/crafty-web.git
cd crafty-controller/
pip3 install -r requirements.txt
python run.py
```
## Release History
* 2.0.Alpha
    * Work in progress

## Documentation
- TODO

## Meta
Phillip Tarrant - [Project Homepage](https://craftycontrol.com/)

Distributed under the MIT license. See LICENSE.txt for more information.

[GIT Repo](https://gitlab.com/Ptarrant1/crafty-web)
