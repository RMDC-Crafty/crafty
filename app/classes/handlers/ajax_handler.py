import tornado.web
import tornado.escape

from app.classes.console import console
from app.classes.models import *
from app.classes.handlers.base_handler import BaseHandler
from app.classes.web_sessions import web_session
from app.classes.multiserv import multi
from app.classes.ftp import ftp_svr_object

logger = logging.getLogger(__name__)

class AjaxHandler(BaseHandler):

    def initialize(self, mcserver):
        self.mcserver = mcserver
        self.console = console

    @tornado.web.authenticated
    def get(self, page):

        if page == 'server_log':
            server_id = self.get_argument('id')

            if server_id is None:
                logger.warning("Server ID not found in server_log ajax call")

            server_path = multi.get_server_root_path(server_id)

            server_log = os.path.join(server_path, 'logs', 'latest.log')
            data = helper.tail_file(server_log, 40)

            for d in data:
                self.write(d.encode("utf-8"))

        elif page == 'history':
            db_data = History.select()
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

        elif page == 'get_file':
            file_path = self.get_argument('file_name')
            f = open(file_path, "r")
            file_data = f.read()
            context = {
                "file_data": file_data,
                "file_path":file_path
            }

            self.render(
                'ajax/edit_file.html',
                data=context

            )

        elif page == 'update_jar':
            Remote.insert({
                Remote.command: 'update_server_jar'
            }).execute()

        elif page == 'revert_jar':
            Remote.insert({
                Remote.command: 'revert_server_jar'
            }).execute()


    def post(self, page):

        name = tornado.escape.json_decode(self.current_user)
        user_data = get_perms_for_user(name)

        if page == "send_command":
            command = self.get_body_argument('command', default=None, strip=True)
            server_id = self.get_argument('id')

            if server_id is None:
                logger.warning("Server ID not found in send_command ajax call")

            srv_obj = multi.get_server_obj(server_id)

            if command:
                if srv_obj.check_running():
                    srv_obj.send_command(command)

        elif page == 'del_file':
            file_to_del = self.get_body_argument('file_name', default=None, strip=True)
            if file_to_del:
                helper.del_file(file_to_del)

        elif page == 'del_schedule':
            id_to_del = self.get_body_argument('id', default=None, strip=True)

            if id_to_del:
                logger.info("Got command to del schedule {}".format(id_to_del))
                q = Schedules.delete().where(Schedules.id == id_to_del)
                q.execute()

        elif page == 'search_logs':
            search_string = self.get_body_argument('search', default=None, strip=True)
            server_id = self.get_body_argument('id', default=None, strip=True)

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

            new_username = self.get_argument("username", None, True)

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

        elif page == "edit_role":
            if not user_data['config']:
                logger.warning("User: {} with Role: {} Attempted Access to: {} and was denied".format(
                    user_data['username'], user_data['role_name'], "Delete User"))
                self.redirect('/admin/unauthorized')

            username = self.get_argument("username", None, True)
            role = self.get_argument("role", None, True)

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
                    user_data['username'], user_data['role_name'], "Delete User"))
                self.redirect('/admin/unauthorized')

            username = self.get_argument("username", None, True)
            newpassword = self.get_argument("password", None, True)

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

            username = self.get_argument("username", None, True)

            if username == 'Admin':
                self.write("Not Allowed")
            else:
                if username:
                    Users.delete().where(Users.username == username).execute()
                    self.write("{} deleted".format(username))

        elif page == 'save_file':
            file_data = self.get_argument('file_contents')
            file_path = self.get_argument("file_path")
            try:
                file = open(file_path, 'w')
                file.write(file_data)
                file.close()
                logger.error("File {} saved with new content".format(file_path))
            except Exception as e:
                logger.error("Unable to save {} due to {} error".format(file_path, e))
            self.redirect("/admin/files")

        elif page == "destroy_server":
            server_id = self.get_body_argument('server_id', default=None, strip=True)
            if server_id is not None:
                MC_settings.delete_by_id(server_id)
                multi.remove_server_object(server_id)