import time
import glob
import logging
import schedule
import bleach
import threading
import tornado.web
import tornado.escape
from pathlib import Path

from app.classes.console import console
from app.classes.models import *
from app.classes.handlers.base_handler import BaseHandler
from app.classes.web_sessions import web_session
from app.classes.multiserv import multi
from app.classes.ftp import ftp_svr_object
from app.classes.backupmgr import backupmgr

logger = logging.getLogger(__name__)

class AdminHandler(BaseHandler):

    def initialize(self, mcserver):
        self.mcserver = mcserver
        self.console = console
        self.session = web_session(self.current_user)

    @tornado.web.authenticated
    def get(self, page):

        name = tornado.escape.json_decode(self.current_user)
        user_data = get_perms_for_user(name)

        context = {
            'user_data': user_data,
            'version_data': helper.get_version(),
            'servers_defined': multi.list_servers(),
            'managed_server': self.session.get_data(self.current_user, 'managed_server'),
            'servers_running': multi.list_running_servers(),
            'mc_servers_data': multi.get_stats_for_servers()
        }

        if page == 'unauthorized':
            template = "admin/denied.html"

        elif page == "reload_web":
            template = "admin/reload_web_settings.html"

            web_data = Webserver.get()
            context['user_data'] = user_data
            context['web_settings'] = model_to_dict(web_data)

            self.render(
                template,
                data=context
            )
            # reload web server
            Remote.insert({
                Remote.command: 'restart_web_server',
                Remote.server_id: 1,  # this doesn't really matter as we are not tying to a server
                Remote.command_source: 'local'
            }).execute()

        elif page == 'reload_mc_settings':
            Remote.insert({
                Remote.command: 'reload_mc_settings',
                Remote.server_id: 1, # this doesn't really matter as we are not tying to a server
                Remote.command_source: 'local'

            }).execute()

            self.redirect("/admin/config")

        elif page == 'dashboard':
            errors = bleach.clean(self.get_argument('errors', ''))
            context['errors'] = errors
            context['host_stats'] = multi.get_host_status()

            template = "admin/dashboard.html"

        elif page == 'change_password':
            template = "admin/change_pass.html"

        elif page == 'virtual_console':
            if not check_role_permission(user_data['username'], 'svr_console'):
                self.redirect('/admin/unauthorized')

            context['server_id'] = bleach.clean(self.get_argument('id', ''))

            mc_data = MC_settings.get_by_id(context['server_id'])

            context['server_name'] = mc_data.server_name

            template = "admin/virt_console.html"

        elif page == "backups":
            if not check_role_permission(user_data['username'], 'backups'):
                self.redirect('/admin/unauthorized')
                
            server_id = bleach.clean(self.get_argument('id', ''))
            mc_data = MC_settings.get_by_id(server_id)
            
            template = "admin/backups.html"

            backup_data = Backups.get_by_id(server_id)

            backup_data = model_to_dict(backup_data)

            backup_path = backup_data['storage_location']
            backup_dirs = json.loads(backup_data['directories'])

            context['backup_data'] = json.loads(backup_data['directories'])
            context['backup_config'] = backup_data

            # get a listing of directories in the server path.
            context['directories'] = helper.scan_dirs_in_path(mc_data.server_path)

            context['server_root'] = mc_data.server_path

            context['server_name'] = mc_data.server_name
            context['server_id'] = mc_data.id
            context['backup_paths'] = backup_dirs
            context['backup_path'] = backup_path
            context['current_backups'] = backupmgr.list_backups_for_server(server_id)

            context['saved'] = False
            context['invalid'] = False

        elif page == "all_backups":
            if not check_role_permission(user_data['username'], 'backups'):
                self.redirect('/admin/unauthorized')

            template = "admin/backups.html"
            # END
            
            backup_list = Backups.get()
            backup_data = model_to_dict(backup_list)
            backup_path = backup_data['storage_location']
            backup_dirs = json.loads(backup_data['directories'])
            
            context['backup_paths'] = backup_dirs
            context['backup_path'] = backup_path
            context['current_backups'] = backupmgr.list_all_backups()
            context['server_name'] = "All Servers"

        elif page == "schedules":
            if not check_role_permission(user_data['username'], 'schedules'):
                self.redirect('/admin/unauthorized')

            saved = bleach.clean(self.get_argument('saved', ''))
            server_id = int(bleach.clean(self.get_argument('id', 1)))

            db_data = Schedules.select().where(Schedules.server_id == server_id)

            template = "admin/schedules.html"
            context['db_data'] = db_data
            context['saved'] = saved
            context['server_id'] = server_id

        elif page == "schedule_disable":
            if not check_role_permission(user_data['username'], 'schedules'):
                self.redirect('/admin/unauthorized')

            schedule_id = self.get_argument('taskid', 1)
            server_id = self.get_argument('id', 1)

            q = Schedules.update(enabled=0).where(Schedules.id == schedule_id)
            q.execute()

            self._reload_schedules()

            self.redirect("/admin/schedules?id={}".format(server_id))

        elif page == "schedule_enable":
            if not check_role_permission(user_data['username'], 'schedules'):
                self.redirect('/admin/unauthorized')

            schedule_id = self.get_argument('taskid', 1)
            server_id = self.get_argument('id', 1)

            q = Schedules.update(enabled=1).where(Schedules.id == schedule_id)
            q.execute()

            self._reload_schedules()

            self.redirect("/admin/schedules?id={}".format(server_id))

        elif page == 'config':
            if not check_role_permission(user_data['username'], 'config'):
                self.redirect('/admin/unauthorized')

            saved = bleach.clean(self.get_argument('saved', ''))
            invalid = bleach.clean(self.get_argument('invalid', ''))

            template = "admin/config.html"
            crafty_data = Crafty_settings.get()
            # ftp_data = Ftp_Srv.get()
            web_data = Webserver.get()
            users = Users.select()
            roles = Roles.select()

            # context['ftp_user'] = ftp_data.user
            # context['ftp_pass'] = ftp_data.password
            # context['ftp_port'] = ftp_data.port

            context['saved'] = saved
            context['invalid'] = invalid

            context['crafty_settings'] = model_to_dict(crafty_data)
            context['web_settings'] = model_to_dict(web_data)

            context['users'] = users
            context['users_count'] = len(users)
            context['roles'] = roles

        elif page == 'server_config':
            if not check_role_permission(user_data['username'], 'config'):
                self.redirect('/admin/unauthorized')

            saved = bleach.clean(self.get_argument('saved', ''))
            invalid = bleach.clean(self.get_argument('invalid', ''))
            server_id = bleach.clean(self.get_argument('id', 1))
            errors = bleach.clean(self.get_argument('errors', ''))

            context['errors'] = errors

            if server_id is None:
                self.redirect("/admin/dashboard")

            template = "admin/server_config.html"

            mc_data = MC_settings.get_by_id(server_id)

            page_data = {}
            context['saved'] = saved
            context['invalid'] = invalid
            context['mc_settings'] = model_to_dict(mc_data)

            context['server_root'] = context['mc_settings']['server_path']

            srv_obj = multi.get_server_obj(server_id)
            context['server_running'] = srv_obj.check_running()

            host_data = Host_Stats.get()
            context['max_memory'] = host_data.mem_total

        elif page == "server_control":
            if not check_role_permission(user_data['username'], 'svr_control'):
                self.redirect('/admin/unauthorized')

            server_id = bleach.clean(self.get_argument('id', 1))

            if server_id is None:
                self.redirect("/admin/dashboard")

            template = "admin/server_control.html"
            logfile = helper.get_crafty_log_file()

            mc_data = MC_settings.get_by_id(server_id)

            srv_obj = multi.get_server_obj(server_id)
            context['server_running'] = srv_obj.check_running()
            context['mc_settings'] = model_to_dict(mc_data)
            context['server_updating'] = self.mcserver.check_updating()
            context['players'] = context['mc_servers_data'][int(server_id)]['players'].split(',')
            context['players_online'] = context['mc_servers_data'][int(server_id)]['online_players']
            context['world_info'] = srv_obj.get_world_info()

        elif page == 'commands':
            if not check_role_permission(user_data['username'], 'svr_console'):
                self.redirect('/admin/unauthorized')

            command = bleach.clean(self.get_argument("command", None, True))
            id = self.get_argument("id", None, True)

            # grab any defined server object and reload the settings
            any_serv_obj = multi.get_first_server_object()
            any_serv_obj.reload_settings()

            if command == "server_stop":
                Remote.insert({
                    Remote.command: 'stop_mc_server',
                    Remote.server_id: id,
                    Remote.command_source: "localhost"
                }).execute()
                next_page = "/admin/virtual_console?id={}".format(id)

            elif command == "server_start":
                Remote.insert({
                    Remote.command: 'start_mc_server',
                    Remote.server_id: id,
                    Remote.command_source: "localhost"
                }).execute()
                next_page = "/admin/virtual_console?id={}".format(id)

            elif command == "server_restart":
                Remote.insert({
                    Remote.command: 'restart_mc_server',
                    Remote.server_id: id,
                    Remote.command_source: "localhost"
                }).execute()
                next_page = "/admin/virtual_console?id={}".format(id)

            elif command == "ftp_server_start":
                Remote.insert({
                    Remote.command: 'start_ftp',
                    Remote.server_id: id,
                    Remote.command_source: 'localhost'
                }).execute()
                time.sleep(2)
                next_page = "/admin/files?id={}".format(id)

            elif command == 'ftp_server_stop':
                Remote.insert({
                    Remote.command: 'stop_ftp',
                    Remote.server_id: id,
                    Remote.command_source: 'localhost'
                }).execute()
                time.sleep(2)
                next_page = "/admin/files?id={}".format(id)

            elif command == "backup":
                backupmgr.backup_server(id)
                time.sleep(4)
                next_page = '/admin/backups?id={}'.format(id)
            
            elif command == "backup_all":
                backupmgr.backup_all_servers()
                time.sleep(4)
                next_page = '/admin/backups'

            elif command == 'update_jar':
                Remote.insert({
                    Remote.command: 'update_server_jar',
                    Remote.server_id: id,
                    Remote.command_source: 'localhost'
                }).execute()
                time.sleep(2)
                next_page = "/admin/server_control?id={}".format(id)

            elif command == 'revert_jar':
                Remote.insert({
                    Remote.command: 'revert_server_jar',
                    Remote.server_id: id,
                    Remote.command_source: 'localhost'
                }).execute()
                time.sleep(2)
                next_page = "/admin/server_control?id={}".format(id)

            elif command == 'destroy_world':
                Remote.insert({
                    Remote.command: 'destroy_world',
                    Remote.server_id: id,
                    Remote.command_source: "localhost"
                }).execute()
                next_page = "/admin/virtual_console?id={}".format(id)

            self.redirect(next_page)

        elif page == 'get_logs':
            if not check_role_permission(user_data['username'], 'logs'):
                self.redirect('/admin/unauthorized')

            server_id = bleach.clean(self.get_argument('id', None))
            mc_data = MC_settings.get_by_id(server_id)

            context['server_name'] = mc_data.server_name
            context['server_id'] = server_id

            srv_object = multi.get_server_obj(server_id)

            data = []

            server_log = os.path.join(mc_data.server_path, 'logs', 'latest.log')

            if server_log is not None:
                data = helper.tail_file(server_log, 500)
                data.insert(0, "Lines trimmed to ~500 lines for speed sake \n ")
            else:
                data.insert(0, "Unable to find {} \n ".format(
                    os.path.join(mc_data.server_path, 'logs', 'latest.log')))

            crafty_data = helper.tail_file(helper.crafty_log_file, 100)
            crafty_data.insert(0, "Lines trimmed to ~100 lines for speed sake \n ")

            scheduler_data = helper.tail_file(os.path.join(helper.logs_dir, 'schedule.log'), 100)
            scheduler_data.insert(0, "Lines trimmed to ~100 lines for speed sake \n ")

            access_data = helper.tail_file(os.path.join(helper.logs_dir, 'tornado-access.log'), 100)
            access_data.insert(0, "Lines trimmed to ~100 lines for speed sake \n ")

            ftp_data = helper.tail_file(os.path.join(helper.logs_dir, 'ftp.log'), 100)
            ftp_data.insert(0, "Lines trimmed to ~100 lines for speed sake \n ")

            errors = srv_object.search_for_errors()
            template = "admin/logs.html"

            context['log_data'] = data
            context['errors'] = errors
            context['crafty_log'] = crafty_data
            context['scheduler'] = scheduler_data
            context['access'] = access_data
            context['ftp'] = ftp_data

        elif page == "files":
            if not check_role_permission(user_data['username'], 'files'):
                self.redirect('/admin/unauthorized')

            template = "admin/files.html"

            server_id = bleach.clean(self.get_argument('id', 1))
            context['server_id'] = server_id

            srv_object = multi.get_server_obj(server_id)
            context['pwd'] = srv_object.server_path

            context['listing'] = helper.scan_dirs_in_path(context['pwd'])
            context['parent'] = None

            context['ext_list'] = [".txt", ".yml", "ties", "json", '.conf', 'cfg']

        else:
            # 404
            template = "public/404.html"
            context = {}

        self.render(
            template,
            data=context
        )

    @tornado.web.authenticated
    def post(self, page):

        name = tornado.escape.json_decode(self.current_user)
        user_data = get_perms_for_user(name)

        # server_data = self.get_server_data()
        context = {
            'user_data': user_data,
            'version_data': helper.get_version(),
            'servers_defined': multi.list_servers(),
            'managed_server': self.session.get_data(self.current_user, 'managed_server'),
            'servers_running': multi.list_running_servers(),
            'mc_servers_data': multi.get_stats_for_servers()
        }

        if page == 'change_password':
            entered_password = bleach.clean(self.get_argument('password'))
            encoded_pass = helper.encode_pass(entered_password)

            q = Users.update({Users.password: encoded_pass}).where(Users.username == user_data['username'])
            q.execute()

            self.clear_cookie("user")
            self.redirect("/")

        elif page == 'schedules':
            action = bleach.clean(self.get_argument('action', ''))
            interval = bleach.clean(self.get_argument('interval', ''))
            interval_type = bleach.clean(self.get_argument('type', ''))
            sched_time = bleach.clean(self.get_argument('time', ''))
            command = bleach.clean(self.get_argument('command', ''))
            comment = bleach.clean(self.get_argument('comment', ''))
            server_id = int(self.get_argument('server_id', ''))

            result = (
                Schedules.insert(
                    enabled=True,
                    action=action,
                    interval=interval,
                    interval_type=interval_type,
                    start_time=sched_time,
                    command=command,
                    comment=comment,
                    server_id=server_id
                )
                .on_conflict('replace')
                .execute()
            )

            self._reload_schedules()

            self.redirect("/admin/schedules?id={}".format(server_id))

        elif page == 'config':

            config_type = bleach.clean(self.get_argument('config_type'))

            if config_type == 'mc_settings':

                # Define as variables to eliminate multiple function calls, slowing the processing down
                server_path = self.get_argument('server_path')
                server_jar = self.get_argument('server_jar')
                java_path = self.get_argument('java_path')
                server_path_exists = helper.check_directory_exist(server_path)

                # Use pathlib to join specified server path and server JAR file then check if it exists
                jar_exists = helper.check_file_exists(os.path.join(server_path, server_jar))

                # Check if custom Java path is specified and if it exists
                if java_path == 'java':
                    java_path_exists = True
                else:
                    java_path_exists = helper.check_file_exists(java_path)

                if server_path_exists and jar_exists and java_path_exists:
                    q = MC_settings.update({
                        MC_settings.server_name: self.get_argument('server_name'),
                        MC_settings.server_path: server_path,
                        MC_settings.server_jar: server_jar,
                        MC_settings.memory_max: self.get_argument('memory_max'),
                        MC_settings.memory_min: self.get_argument('memory_min'),
                        MC_settings.additional_args: self.get_argument('additional_args'),
                        MC_settings.pre_args: self.get_argument('pre_args'),
                        MC_settings.java_path: java_path,
                        MC_settings.auto_start_server: int(self.get_argument('auto_start_server')),
                        MC_settings.server_port: self.get_argument('server_port'),
                        MC_settings.server_ip: self.get_argument('server_ip'),
                        MC_settings.jar_url: self.get_argument('jar_url'),
                        MC_settings.crash_detection: self.get_argument('crash_detection')
                    }).where(MC_settings.id == 1)

                    q.execute()
                    self.mcserver.reload_settings()

                # Restructure things a bit and add Java path check
                elif not server_path_exists:
                    # Redirect to "config invalid" page and log an event
                    logger.error('Minecraft server directory does not exist')
                    self.redirect("/admin/config?invalid=True")

                elif not jar_exists:
                    logger.error('Minecraft server JAR does not exist at {}'.format(server_path))
                    self.redirect("/admin/config?invalid=True")

                else:
                    logger.error('Minecraft server Java path does not exist')
                    self.redirect("/admin/config?invalid=True")

            elif config_type == 'ftp_settings':
                ftp_user = bleach.clean(self.get_argument('ftp_user'))
                ftp_pass = bleach.clean(self.get_argument('ftp_pass'))
                ftp_port = bleach.clean(self.get_argument('ftp_port'))

                Ftp_Srv.update({
                    Ftp_Srv.user: ftp_user,
                    Ftp_Srv.password: ftp_pass,
                    Ftp_Srv.port: ftp_port,
                }).execute()

            elif config_type == 'crafty_settings':
                interval = bleach.clean(self.get_argument('historical_interval'))
                max_age = bleach.clean(self.get_argument('history_max_age'))
                lang = bleach.clean(self.get_argument('language'))
                web_port = int(float(self.get_argument('port_number')))

                q = Crafty_settings.update({
                    Crafty_settings.history_interval: interval,
                    Crafty_settings.history_max_age: max_age,
                    Crafty_settings.language: lang,
                }).where(Crafty_settings.id == 1).execute()

                q = Webserver.update({
                    Webserver.port_number: web_port
                }).execute()

                # reload the history settings
                multi.reload_history_settings()


            self.redirect("/admin/config?saved=True")

        elif page == "server_config":
            # Define as variables to eliminate multiple function calls, slowing the processing down
            server_path = bleach.clean(self.get_argument('server_path'))
            server_jar = bleach.clean(self.get_argument('server_jar'))
            server_id = bleach.clean(self.get_argument('server_id'))
            server_name = bleach.clean(self.get_argument('server_name'))
            java_path = bleach.clean(self.get_argument('java_path'))
            errors = bleach.clean(self.get_argument('errors', ''))

            context['errors'] = errors

            server_path_exists = helper.check_directory_exist(server_path)

            # Use pathlib to join specified server path and server JAR file then check if it exists
            jar_exists = helper.check_file_exists(os.path.join(server_path, server_jar))

            # Check if Java executable exists if custom path is specified
            if java_path == 'java':
                java_path_exists = True
            else:
                java_path_exists = helper.check_file_exists(java_path)

            if server_path_exists and jar_exists and java_path_exists:
                MC_settings.update({
                    MC_settings.server_name: server_name,
                    MC_settings.server_path: server_path,
                    MC_settings.server_jar: server_jar,
                    MC_settings.memory_max: bleach.clean(self.get_argument('memory_max')),
                    MC_settings.memory_min: bleach.clean(self.get_argument('memory_min')),
                    MC_settings.additional_args: bleach.clean(self.get_argument('additional_args')),
                    MC_settings.pre_args: bleach.clean(self.get_argument('pre_args')),
                    MC_settings.java_path: java_path,
                    MC_settings.auto_start_server: int(float(self.get_argument('auto_start_server'))),
                    MC_settings.auto_start_delay: int(float(self.get_argument('auto_start_delay'))),
                    MC_settings.auto_start_priority: int(float(self.get_argument('auto_start_priority'))),
                    MC_settings.crash_detection: int(float(self.get_argument('crash_detection'))),
                    MC_settings.server_port: int(float(self.get_argument('server_port'))),
                    MC_settings.server_ip: bleach.clean(self.get_argument('server_ip')),
                    MC_settings.jar_url: bleach.clean(self.get_argument('jar_url')),
                }).where(MC_settings.id == server_id).execute()

                srv_obj = multi.get_first_server_object()
                srv_obj.reload_settings()

                self.redirect("/admin/dashboard")

            # Restructure things a bit and add Java path check
            elif not server_path_exists:
                # Redirect to "config invalid" page and log an event
                logger.error('Minecraft server directory not exist')
                self.redirect("/admin/server_config?id={}&errors={}".format(server_id, "Server Path Does Not Exists"))

            elif not jar_exists:
                logger.error('Minecraft server JAR does not exist at {}'.format(server_path))
                self.redirect("/admin/server_config?id={}&errors={}".format(server_id, "Server Jar Does Not Exists"))

            else:
                logger.error('Minecraft server Java path does not exist')
                self.redirect("/admin/server_config?id={}&errors={}".format(server_id, "Java Path Does Not Exist"))

        elif page == 'files':

            next_dir = bleach.clean(self.get_argument('next_dir'))
            server_id = bleach.clean(self.get_argument('server_id'))
            path = Path(next_dir)

            template = "admin/files.html"
            context['pwd'] = next_dir

            context['server_id'] = server_id

            context['listing'] = helper.scan_dirs_in_path(context['pwd'])

            mc_data = MC_settings.get_by_id(server_id)
            mc_settings = model_to_dict(mc_data)

            mc_settings['server_path'] = str(mc_settings['server_path']).replace("\\", '/')

            # let's remove the server directory from the path...
            asked_for_dir = next_dir.replace(mc_settings['server_path'], '')

            # if the server directory plus the directory asked for doesn't exits...
            # this must be an attempt to do path traversal...so we set them back to server path.
            if not helper.check_directory_exist(mc_settings['server_path'] + asked_for_dir):
                context['pwd'] = mc_settings['server_path']
                context['listing'] = helper.scan_dirs_in_path(mc_settings['server_path'])
                next_dir = mc_settings['server_path']

            if next_dir == mc_settings['server_path']:
                context['parent'] = None
            else:
                context['parent'] = path.parent
                context['parent'] = str(context['parent']).replace("\\", '/')

            context['ext_list'] = [".txt", ".yml", "ties", "json", '.conf', '.cfg', '.toml']


            self.render(
                template,
                data=context
            )

        elif page == 'add_server':
            server_name = bleach.clean(self.get_argument('server_name', ''))
            server_path = bleach.clean(self.get_argument('server_path', ''))
            create_server_path = bleach.clean(self.get_argument('create_server_path', ''))
            server_jar = bleach.clean(self.get_argument('server_jar', ''))
            server_jar_url = bleach.clean(self.get_argument('server_jar_url', ''))
            max_mem = bleach.clean(self.get_argument('max_mem', ''))
            min_mem = bleach.clean(self.get_argument('min_mem', ''))
            auto_start = bleach.clean(self.get_argument('auto_start', ''))

            samename = MC_settings.select().where(MC_settings.server_name == server_name)
            if samename.exists():
                logger.error("2 servers can't have the same name - Can't add server")
                error = "Another server is already called: {}".format(server_name)

            samepath = MC_settings.select().where(MC_settings.server_path == server_path)
            if samepath.exists():
                logger.error("2 servers can't have the same path - Can't add server")
                error = "Another server is already using: {}".format(server_path)

            error = None

            if create_server_path == 'on':
                helper.ensure_dir_exists(server_path)

            # does this server path / jar exist?
            server_path_exists = helper.check_directory_exist(server_path)

            if not server_path_exists:
                logger.error("Server path {} doesn't exist - Can't add server".format(server_path))
                error = "Server Path Does Not Exists"

            # Use pathlib to join specified server path and server JAR file then check if it exists
            server_jar_path = os.path.join(server_path, server_jar)
            jar_exists = helper.check_file_exists(server_jar_path)

            if not jar_exists and server_jar_url:
                download_complete = helper.download_file(server_jar_url, server_jar_path)
                if not download_complete:
                    logger.error("Unable to download server jar from {}".format(server_jar_url))
                    error = "Unable to Download Server Jar"

            jar_exists = helper.check_file_exists(server_jar_path)

            if not jar_exists and error is None:
                logger.error("Server jar {} doesn't exist - Can't add server".format(server_jar_path))
                error = "Server Jar Does Not Exists"

            # does a server with this name already exists?
            existing = MC_settings.select(MC_settings.server_name).where(MC_settings.server_name == server_name)
            if existing and error is None:
                logger.error("A server with that name already exists - Can't add server {}".format(server_name))
                error = "A server with that name already exists"

            if error is None:
                new_server_id = MC_settings.insert({
                    MC_settings.server_name: server_name,
                    MC_settings.server_path: server_path,
                    MC_settings.server_jar: server_jar,
                    MC_settings.memory_max: max_mem,
                    MC_settings.memory_min: min_mem,
                    MC_settings.additional_args: "",
                    MC_settings.java_path: "java",
                    MC_settings.auto_start_server: auto_start,
                    MC_settings.auto_start_delay: 10,
                    MC_settings.auto_start_priority: 1,
                    MC_settings.crash_detection: 0,
                    MC_settings.server_port: 25565,
                    MC_settings.server_ip: "127.0.0.1"
                }).execute()

                #add a backup folder
                directories = [server_path, ]
                backup_directory = json.dumps(directories)

                # default backup settings
                Backups.insert({
                    Backups.directories: backup_directory,
                    Backups.storage_location: os.path.abspath(os.path.join(helper.crafty_root, 'backups')),
                    Backups.max_backups: 7,
                    Backups.server_id: new_server_id
                }).execute()

                logger.info("Added ServerID: {} - {}".format(new_server_id, server_name))

                multi.setup_new_server_obj(new_server_id)
                multi.do_stats_for_servers()
                self.redirect("/admin/dashboard")
            else:
                self.redirect("/admin/dashboard?errors={}".format(error))

        elif page == 'backups':
            checked = self.get_arguments('backup')
            max_backups = int(self.get_argument('max_backups', 1))
            backup_storage = bleach.clean(self.get_argument('storage_location', ''))
            server_id = bleach.clean(self.get_argument('server_id', ''))

            if len(checked) == 0 or len(backup_storage) == 0:
                logger.error('Backup settings Invalid: Checked: {}, max_backups: {}, backup_storage: {}'
                             .format(checked, max_backups, backup_storage))
                self.redirect("/admin/config?invalid=True")

            else:
                logger.info("Backup directories set to: {}".format(checked))
                json_dirs = json.dumps(list(checked))

                Backups.update(
                    {
                        Backups.directories: json_dirs,
                        Backups.max_backups: max_backups,
                        Backups.storage_location: backup_storage,
                        Backups.server_id: int(server_id)
                    }
                ).where(Backups.server_id == int(server_id)).execute()

            self.redirect("/admin/backups?id={}".format(server_id))

        elif page == 'upload':
            server_id = bleach.clean(self.get_argument('server_id', ''))

            # did we get a file?
            if len(self.request.files['file1']) < 1:
                self.write("No File Selected... Please go back and try again")
                logger.error("No file found in upload handler - data: {}".format(self.request.files['file1']))
                return False

            file1 = self.request.files['file1'][0]
            pwd = bleach.clean(self.get_argument('pwd'))

            template = "admin/files.html"
            original_fname = file1['filename']

            path = Path(pwd)

            mc_data = MC_settings.get_by_id(server_id)
            mc_settings = model_to_dict(mc_data)

            mc_settings['server_path'] = str(mc_settings['server_path']).replace("\\", '/')

            # let's remove the server directory from the path...
            asked_for_dir = pwd.replace(mc_settings['server_path'], '')

            file_path = mc_settings['server_path'] + asked_for_dir
            file_data = file1['body']

            result = self._upload_file(file_data, file_path, original_fname)

            context['upload_success'] = result
            context['pwd'] = pwd
            context['server_id'] = server_id

            # if the server directory plus the directory asked for doesn't exits...
            # this must be an attempt to do path traversal...so we set them back to server path.
            if not helper.check_directory_exist(mc_settings['server_path'] + asked_for_dir):
                context['pwd'] = mc_settings['server_path']

            context['listing'] = helper.scan_dirs_in_path(mc_settings['server_path'])
            next_dir = mc_settings['server_path']

            if next_dir == mc_settings['server_path']:
                context['parent'] = None
            else:
                context['parent'] = path.parent
                context['parent'] = str(context['parent']).replace("\\", '/')

            context['ext_list'] = [".txt", ".yml", "ties", "json", '.conf', '.cfg']

            self.render(
                template,
                data=context
            )

    def _reload_schedules(self):
        '''
        logger.info("Reloading Scheduled Tasks")

        db_data = Schedules.select()

        # clear all user jobs
        schedule.clear('user')

        logger.info("Deleting all old tasks")

        logger.info("There are {} scheduled jobs to parse:".format(len(db_data)))

        # loop through the tasks in the db
        for task in db_data:
            helper.scheduler(task, self.mcserver)
        '''
        multi.reload_user_schedules()

    def _upload_file(self, file_data, file_path, file_name):

        error = ""

        file_full_path = os.path.join(file_path, file_name)

        if not helper.check_writeable(file_path):
            error = "Unwritable Path"

        if error != "":
            logger.error("Unable to save uploaded file due to: {}".format(error))
            return False

        output_file = open(file_full_path, 'wb')
        output_file.write(file_data)
        logger.info('Saving File: {}'.format(file_full_path))
        return True
