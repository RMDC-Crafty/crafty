# Changelog
All notable changes to this project will be documented in this file.

## [v2.0.RC1]
This version of Crafty focuses on Waterfall/Bungee Support, Permissions/Roles
and cleanup/refactoring to get ready for possible RC status.

### Additions
Waterfall/Bungee Support - Crafty no longer fails if there isn't a server.properties.
Waterfall/Bungee Support - Crafty will send "end" for waterfall/bungee instead of stop
New Table added to DB to store server roles. Create 4 new roles as default - Admin, Staff, Mod, Backup
Added roles and Permissions page to the users tab on the config page.

### Changes
Added datatables to Errors Log on logging page.
Fixed potential bug where Backup save path could be blank
Fixed potential bug where backup folders could be blank (nothing checked)
Fixed bug where waterfall servers desc are not showing


### Bug Fixes
#19 - Datatables error on logs page with no errors/warnings


## [v2.0.beta2]
This version of Crafty focuses on Schedules, and more customization of 
Crafty via configuration options.  

### Additions
- Addition of schedules
- Historical Data graph on dashboard.
- Logs page now has a tabbed interface with multiple logs and a search option.
- Added Pre arguments to be configured
- config page changed to have a tabbed interface
- Historical Data is configurable in conf page
- HTTPS only interface with Self Signed Certs

### Changes
- moved scheduled logs to own file
- removed old Alpha 1 documentation - replaced with page that links to craftycontrol.com
- fixed windows path issues / errors.
- database should create new tables as needed upon upgrade, still recommend starting a new one
- backups now backup whatever you want - all configurable in the interface - preserving full paths for easy restore option

### Bug Fixes
* Fixed a bug where invalid Login name would cause error on page. - Thanks IAbooseYou

* Fixed a bug where if unable to find world information, page would bomb out - Thanks ConnorTron, DragonKnight, PengwinPlays

* Fixed a bug where if logs weren't found, page would bomb out - both virtual console and logs page - Thanks Kornster
    
* Fixed issue number 2 & 3 related to getting player numbers and server version - Thanks Kornster / ConnorTron
   
* Fixed issue number 4 dealing with log file encoding -  Thanks Jarly

* Fixed issue #10 signout now works - Thanks ConnorTron

* Fixed issue number 9 for scheduling - Thanks Penguin

## [v2.0.alpha]
This version of Crafty is a complete rebuild of Crafty from the ground up.
Crafty is now a web based platform and thus is a different product than
Crafty 1.0, hence the 2.0 name.

- [Tornado](https://www.tornadoweb.org/en/stable/) webserver used as a backend for the web side.
- [Argon2](https://pypi.org/project/argon2-cffi/) used for password hashing
- [SQLite DB](https://www.sqlite.org/index.html) used for settings.
- [Adminlte](https://adminlte.io/themes/AdminLTE/index2.html) used for web templating
- [Font Awesome 4](https://fontawesome.com/) used for Buttons 
