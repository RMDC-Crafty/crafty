import tornado.web
import tornado.escape
import schedule
import bleach

from app.classes.console import console
from app.classes.models import *
from app.classes.handlers.base_handler import BaseHandler
from app.classes.web_sessions import web_session
from app.classes.multiserv import multi
from app.classes.ftp import ftp_svr_object
from app.classes.backupmgr import backupmgr
from zipfile import ZipFile
import shutil

logger = logging.getLogger(__name__)

class AjaxHandler(BaseHandler):

    def initialize(self, mcserver):
        self.mcserver = mcserver
        self.console = console
        self.session = web_session(self.current_user)

    @tornado.web.authenticated
    def get(self, page):

        name = tornado.escape.json_decode(self.current_user)
        user_data = get_perms_for_user(name)

        if page == 'server_log':
            server_id = bleach.clean(self.get_argument('id'))
            if not user_data['logs']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Server log (ID {})".format(server_id)))
                self.redirect('/admin/unauthorized')

            if server_id is None:
                logger.warning("Server ID not found in server_log ajax call")
                return False

            server_path = multi.get_server_root_path(server_id)

            server_log = os.path.join(server_path, 'logs', 'latest.log')
            data = helper.tail_file(server_log, 40)

            for d in data:
                self.write(d.encode("utf-8"))

        elif page == 'history':
            server_id = bleach.clean(self.get_argument("server_id",''))
            if not user_data['svr_control']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Server history (ID {})".format(server_id)))
                self.redirect('/admin/unauthorized')

            db_data = History.select().where(History.server_id == server_id)
            return_data = []
            for d in db_data:
                row_data = {
                    'time': d.time.strftime("%m/%d/%Y %H:%M:%S"),
                    'cpu': d.cpu,
                    'mem': d.memory,
                    'players': d.players
                }
                return_data.append(row_data)

            self.write(json.dumps(return_data))

        elif page == 'update_check':
            if not user_data['config']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Update Check"))
                self.redirect('/admin/unauthorized')
            context = {
                'master': helper.check_version('master'),
                'beta': helper.check_version('beta'),
                'snaps': helper.check_version('snapshot'),
                'current': helper.get_version()
            }

            self.render(
                'ajax/version.html',
                data=context
            )

        elif page == 'host_cpu_infos':  

            name = tornado.escape.json_decode(self.current_user)
            user_data = get_perms_for_user(name)

            context = {
                'host_stats': multi.get_host_status()
            }                 
                    
            self.render(
                'ajax/host_cpu_infos.html',
                data=context
            )

        elif page == 'host_ram_infos':  

            name = tornado.escape.json_decode(self.current_user)
            user_data = get_perms_for_user(name)

            context = {
                'host_stats': multi.get_host_status()
            }                 
                    
            self.render(
                'ajax/host_ram_infos.html',
                data=context
            )

        elif page == 'host_disk_infos':  

            name = tornado.escape.json_decode(self.current_user)
            user_data = get_perms_for_user(name)

            context = {
                'host_stats': multi.get_host_status()
            }                 
                    
            self.render(
                'ajax/host_disk_infos.html',
                data=context
            )

        elif page == 'host_running_servers':  

            name = tornado.escape.json_decode(self.current_user)
            user_data = get_perms_for_user(name)

            context = {
                'servers_running': multi.list_running_servers(),
                'servers_defined': multi.list_servers(),
            }                 
                    
            self.render(
                'ajax/host_running_servers.html',
                data=context
            )

        elif page == 'server_status':  

            name = tornado.escape.json_decode(self.current_user)
            user_data = get_perms_for_user(name)

            context = {
                'user_data': user_data,
                'mc_servers_data': multi.get_stats_for_servers()
            }     

            server_id = bleach.clean(self.get_argument('id'))
            srv_obj = multi.get_server_obj(server_id)
            
            context['srv'] = {
                        'id': srv_obj.server_id,
                        'name': srv_obj.get_mc_server_name(),
                        'running': srv_obj.check_running(),
                        'crashed': srv_obj.check_crashed(),
                        'auto_start': srv_obj.settings.auto_start_server
                    }
                    
            self.render(
                'ajax/server_status.html',
                data=context
            )

        elif page == 'server_infos':
            server_id = bleach.clean(self.get_argument('id', 1))
            if not user_data['svr_control']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Server Info (ID:{})".format(server_id)))
                self.redirect('/admin/unauthorized')

            name = tornado.escape.json_decode(self.current_user)
            user_data = get_perms_for_user(name)

            context = {
                'user_data': user_data,
                'mc_servers_data': multi.get_stats_for_servers()
            }     

            srv_obj = multi.get_server_obj(server_id)
            
            context['srv'] = {
                        'id': srv_obj.server_id,
                        'name': srv_obj.get_mc_server_name(),
                        'running': srv_obj.check_running(),
                        'crashed': srv_obj.check_crashed(),
                        'auto_start': srv_obj.settings.auto_start_server
                    }
                    
            self.render(
                'ajax/server_infos.html',
                data=context
            )

        elif page == 'get_file':
            file_path = bleach.clean(self.get_argument('file_name'))
            server_id = bleach.clean(self.get_argument('server_id'))

            if not user_data['files']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Get file (ID:{}, path:{})".format(server_id, file_path)))
                self.redirect('/admin/unauthorized')

            mc_data = MC_settings.get_by_id(server_id)
            mc_settings = model_to_dict(mc_data)

            mc_settings['server_path'] = str(mc_settings['server_path']).replace("\\", '/')

            # let's remove the server directory from the path...
            asked_for_path = file_path.replace(mc_settings['server_path'], '')
            built_path = mc_settings['server_path'] + asked_for_path

            # if the server directory plus the path asked for doesn't exits...
            # this must be an attempt to do path traversal...so we bomb out.
            if not helper.check_file_exists(built_path):
                raise Exception("possible file traversal detected {}".format(file_path))

            else:
                f = open(file_path, "r")
                file_data = f.read()
                context = {
                    "file_data": file_data,
                    "file_path": file_path,
                    "server_id": server_id
                }

                self.render(
                    'ajax/edit_file.html',
                    data=context
                )

    @tornado.web.authenticated
    def post(self, page):

        name = tornado.escape.json_decode(self.current_user)
        user_data = get_perms_for_user(name)

        if page == "send_command":
            if not user_data['svr_console']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Send Command"))
                self.redirect('/admin/unauthorized')
            command = bleach.clean(self.get_body_argument('command', default=None, strip=True))
            server_id = bleach.clean(self.get_argument('id'))

            if server_id is None:
                logger.warning("Server ID not found in send_command ajax call")

            srv_obj = multi.get_server_obj(server_id)

            if command:
                if srv_obj.check_running():
                    srv_obj.send_command(command)

        elif page == 'del_file':
            if not user_data['files']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Delete File"))
                self.redirect('/admin/unauthorized')
            file_to_del = bleach.clean(self.get_body_argument('file_name', default=None, strip=True))
            server_id = bleach.clean(self.get_argument('server_id', default=None, strip=True))

            # let's make sure this path is in the backup directory and not somewhere else
            # we don't want someone passing a path like /etc/passwd in the raw, so we are only passing the filename
            # to this function, and then tacking on the storage location in front of the filename.

            backup_folder = backupmgr.get_backup_folder_for_server(server_id)

            # Grab our backup path from the DB
            backup_list = Backups.get(Backups.server_id == int(server_id))
            server_backup_file = os.path.join(backup_list.storage_location, backup_folder, file_to_del)

            if server_backup_file and helper.check_file_exists(server_backup_file):
                helper.del_file(server_backup_file)

        elif page == 'del_schedule':
            if not user_data['schedule']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Delete Schedule"))
                self.redirect('/admin/unauthorized')
            id_to_del = bleach.clean(self.get_body_argument('id', default=None, strip=True))

            if id_to_del:
                logger.info("Got command to del schedule {}".format(id_to_del))
                q = Schedules.delete().where(Schedules.id == id_to_del)
                q.execute()

            multi.reload_user_schedules()

        elif page == 'search_logs':
            if not user_data['logs']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Search Logs"))
                self.redirect('/admin/unauthorized')
            search_string = bleach.clean(self.get_body_argument('search', default=None, strip=True))
            server_id = bleach.clean(self.get_body_argument('id', default=None, strip=True))

            data = MC_settings.get_by_id(server_id)
            logfile = os.path.join(data.server_path, 'logs', 'latest.log')
            data = helper.search_file(logfile, search_string)
            if data:
                temp_data = ""
                for d in data:
                    line = "Line Number: {} {}".format(d[0], d[1])
                    temp_data = "{}\n{}".format(temp_data, line)
                return_data = temp_data

            else:
                return_data = "Unable to find your string: {}".format(search_string)
            self.write(return_data)

        elif page == 'add_user':
            if not user_data['config']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Add User"))
                self.redirect('/admin/unauthorized')

            new_username = bleach.clean(self.get_argument("username", None, True))

            if new_username:
                new_pass = helper.random_string_generator()
                api_token = helper.random_string_generator(32)

                result = Users.insert({
                    Users.username: new_username,
                    Users.role: 'Mod',
                    Users.api_token: api_token,
                    Users.password: helper.encode_pass(new_pass)
                }).execute()

                self.write(new_pass)

        elif page == "edit_user_role":
            if not user_data['config']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Edit User Role"))
                self.redirect('/admin/unauthorized')

            username = bleach.clean(self.get_argument("username", None, True))
            role = bleach.clean(self.get_argument("role", None, True))

            if username == 'Admin':
                self.write("Not Allowed")
            else:
                if username and role:
                    Users.update({
                        Users.role: role
                    }).where(Users.username == username).execute()

                    self.write('updated')

        elif page == "change_password":
            if not user_data['config']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Change other user's password"))
                self.redirect('/admin/unauthorized')

            username = bleach.clean(self.get_argument("username", None, True))
            newpassword = bleach.clean(self.get_argument("password", None, True))

            if username and newpassword:
                Users.update({
                    Users.password: helper.encode_pass(newpassword)
                }).where(Users.username == username).execute()

            self.write(newpassword)

        elif page == 'del_user':
            if not user_data['config']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Delete User"))
                self.redirect('/admin/unauthorized')

            username = bleach.clean(self.get_argument("username", None, True))

            if username == 'Admin':
                self.write("Not Allowed")
            else:
                if username:
                    Users.delete().where(Users.username == username).execute()
                    self.write("{} deleted".format(username))

        elif page == 'add_role':
            if not user_data['config']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Add Role"))
                self.redirect('/admin/unauthorized')

            new_rolename = bleach.clean(self.get_argument("rolename", None, True))

            if new_rolename:

                result = Roles.insert({
                    Roles.name: new_rolename,
                    Roles.svr_control: False,
                    Roles.svr_console: False,
                    Roles.logs: False,
                    Roles.backups: False,
                    Roles.schedules: False,
                    Roles.config: False,
                    Roles.files: False,
                    Roles.api_access: False,
                }).execute()

                self.write("{}".format(new_rolename))

                        
        elif page == 'edit_role':
            if not user_data['config']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Edit Role"))
                self.redirect('/admin/unauthorized')

            rolename = bleach.clean(self.get_argument("rolename", None, True))
            
            new_svr_control = 'True' == bleach.clean(self.get_argument("svr_control", False, True))
            new_svr_console = 'True' == bleach.clean(self.get_argument("svr_console", False, True))
            new_logs = 'True' == bleach.clean(self.get_argument("logs", False, True))
            new_backups = 'True' == bleach.clean(self.get_argument("backups", False, True))
            new_schedules = 'True' == bleach.clean(self.get_argument("schedules", False, True))
            new_config = 'True' == bleach.clean(self.get_argument("config", False, True))
            new_files = 'True' == bleach.clean(self.get_argument("files", False, True))
            new_api_access = 'True' == bleach.clean(self.get_argument("api_access", False, True))

            if rolename:
                result = Roles.update({
                    Roles.svr_control: new_svr_control,
                    Roles.svr_console: new_svr_console,
                    Roles.logs: new_logs,
                    Roles.backups: new_backups,
                    Roles.schedules: new_schedules,
                    Roles.config: new_config,
                    Roles.files: new_files,
                    Roles.api_access: new_api_access,
                }).where(Roles.name == rolename).execute()
                    
                self.write("{} edited".format(rolename))

        elif page == 'del_role':
            if not user_data['config']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Delete Role"))
                self.redirect('/admin/unauthorized')

            rolename = bleach.clean(self.get_argument("rolename", None, True))

            if rolename == 'Admin':
                self.write("Not Allowed")
            else:
                if rolename:
                    Roles.delete().where(Roles.name == rolename).execute()
                    self.write("{} deleted".format(rolename))

        elif page == 'save_file':
            if not user_data['files']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Save File"))
                self.redirect('/admin/unauthorized')
            file_data = self.get_argument('file_contents')
            file_path = bleach.clean(self.get_argument("file_path"))
            server_id = bleach.clean(self.get_argument("server_id"))

            mc_data = MC_settings.get_by_id(server_id)
            mc_settings = model_to_dict(mc_data)

            mc_settings['server_path'] = str(mc_settings['server_path']).replace("\\", '/')

            # let's remove the server directory from the path...
            asked_for_path = file_path.replace(mc_settings['server_path'], '')
            built_path = mc_settings['server_path'] + asked_for_path

            # if the server directory plus the path asked for doesn't exits...
            # this must be an attempt to do path traversal...so we bomb out.
            if not helper.check_file_exists(built_path):
                raise Exception("possible file traversal detected {}".format(file_path))

            try:
                file = open(file_path, 'w')
                file.write(file_data)
                file.close()
                logger.info("File {} saved with new content".format(file_path))
            except Exception as e:
                logger.error("Unable to save {} due to {} error".format(file_path, e))
            self.redirect("/admin/files?id={}".format(server_id))

        elif page == "del_server_file":
            if not user_data['files']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Delete File"))
                self.redirect('/admin/unauthorized')
            file_path = bleach.clean(self.get_argument("file_name"))
            server_id = bleach.clean(self.get_argument("server_id"))

            mc_data = MC_settings.get_by_id(server_id)
            mc_settings = model_to_dict(mc_data)

            mc_settings['server_path'] = str(mc_settings['server_path']).replace("\\", '/')

            # let's remove the server directory from the path...
            asked_for_path = file_path.replace(mc_settings['server_path'], '')
            built_path = mc_settings['server_path'] + asked_for_path

            if helper.check_directory_exist(built_path):
                try:
                    shutil.rmtree(built_path)
                    logger.info("Deleting {}".format(built_path))
                except Exception as e:
                    logger.error("Unable to delete {} due to {} error".format(file_path, e))

            if helper.check_file_exists(built_path):
                try:
                    os.remove(file_path)
                    logger.info("File {} deleted".format(file_path))
                except Exception as e:
                    logger.error("Unable to delete {} due to {} error".format(file_path, e))

            self.redirect("/admin/files?id={}".format(server_id))

        elif page == "new_file_folder":
            if not user_data['files']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "New Folder"))
                self.redirect('/admin/unauthorized')
            type = bleach.clean(self.get_argument("type"))
            server_id = bleach.clean(self.get_argument("server_id"))
            pwd = bleach.clean(self.get_argument("pwd"))
            name = bleach.clean(self.get_argument("name"))

            mc_data = MC_settings.get_by_id(server_id)
            mc_settings = model_to_dict(mc_data)

            mc_settings['server_path'] = str(mc_settings['server_path']).replace("\\", '/')

            # let's remove the server directory from the path...
            asked_for_path = pwd.replace(mc_settings['server_path'], '')
            built_path = mc_settings['server_path'] + asked_for_path

            path = os.path.join(pwd, name)

            if type == "folder":
                logger.info("Creating folder at {}".format(path))
                try:
                    os.mkdir(path)
                except Exception as e:
                    logger.error("Unable to create folder at {} due to {}".format(path, e))
            else:
                logger.info("Creating File at {}".format(path))

                try:
                    with open(path, "w") as fobject:
                        fobject.close()
                except Exception as e:
                    logger.error("Unable to create file at {} due to {}".format(path, e))


        elif page == "unzip_server_file":
            if not user_data['files']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Unzip File"))
                self.redirect('/admin/unauthorized')
            file_path = bleach.clean(self.get_argument("file_name"))
            server_id = bleach.clean(self.get_argument("server_id"))
            pwd = bleach.clean(self.get_argument("pwd"))

            mc_data = MC_settings.get_by_id(server_id)
            mc_settings = model_to_dict(mc_data)

            mc_settings['server_path'] = str(mc_settings['server_path']).replace("\\", '/')

            # let's remove the server directory from the path...
            asked_for_path = file_path.replace(mc_settings['server_path'], '')
            built_path = mc_settings['server_path'] + asked_for_path

            # if the server directory plus the path asked for doesn't exits...
            # this must be an attempt to do path traversal...so we bomb out.
            if not helper.check_file_exists(built_path):
                raise Exception("possible file traversal detected {}".format(file_path))

            try:
                with ZipFile(file_path, "r") as zipObj:
                    logger.info("Exctracting file: {} to dir {}".format(file_path,pwd))
                    zipObj.extractall(pwd)

            except Exception as e:
                logger.error("Unable to extract: {} due to error: {}".format(file_path, e))

            self.redirect("/admin/files?id={}".format(server_id))


        elif page == "destroy_server":
            if not user_data['config']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Destroy Server"))
                self.redirect('/admin/unauthorized')
            server_id = bleach.clean(self.get_body_argument('server_id', default=None, strip=True))

            if server_id is not None:

                # stop any server stats going on...
                schedule.clear('server_stats')

                # remove it from multi
                multi.remove_server_object(server_id)

                # reschedule the things
                multi.reload_scheduling()

                self.write("Success")


