import os
import secrets
import threading
import tornado.web
import tornado.escape 
import logging.config

from app.classes.models import Roles, Users, check_role_permission, Remote, model_to_dict
from app.classes.multiserv import multi
from app.classes.helpers import helper
from app.classes.backupmgr import backupmgr

logger = logging.getLogger(__name__)

class BaseHandler(tornado.web.RequestHandler):
        
    def check_xsrf_cookie(self): 
        # Disable CSRF protection on API routes
        pass
    
    def return_response(self, status, errors, data, messages):
        # Define a standardized response 
        self.write({ 
                "status": status,
                "data": data,
                "errors": errors,
                "messages": messages
                })
    
    def access_denied(self, user):
        logger.info("User %s was denied access to API route", user)
        self.set_status(403)
        self.finish(self.return_response(403, {'error':'ACCESS_DENIED'}, {}, {'info':'You were denied access to the requested resource'}))
    
    def authenticate_user(self, token):
        try:
            logger.debug("Searching for specified token")
            user_data = Users.get(api_token=token)
            logger.debug("Checking results")
            if user_data:
                # Login successful! Return the username
                logger.info("User {} has authenticated to API".format(user_data.username))
                return user_data.username
            else:
                logging.debug("Auth unsuccessful")
                return None
                
        except:
            logger.warning("Traceback occurred when authenticating user to API. Most likely wrong token")
            return None
            pass
        
class SendCommand(BaseHandler):
    
    def initialize(self, mcserver):
        self.mcserver = mcserver
    
    def post(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access') and not check_role_permission(user, 'svr_control'):
            self.access_denied(user)
        
        command = self.get_body_argument('command', default=None, strip=True)
        server_id = self.get_argument('id')
        if command:
            server = multi.get_server_obj(server_id)
            if server.check_running:
                server.send_command(command)
                self.return_response(200, '', {"run": True}, '')
            else:
                self.return_response(200, {'error':'SER_NOT_RUNNING'}, {}, {})
        else:
            self.return_response(200, {'error':'NO_COMMAND'}, {}, {})
            
class GetHostStats(BaseHandler):
    
    def initialize(self, mcserver):
        self.mcserver = mcserver
    
    def get(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access') and not check_role_permission(user, 'logs'):
            self.access_denied(user)
        
        stats = multi.get_host_status()
        stats.pop('time') # We dont need the request time 
        self.return_response(200, {}, stats, {})
        
class GetServerStats(BaseHandler):
    
    def initialize(self, mcserver):
        self.mcserver = mcserver
    
    def get(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access') and not check_role_permission(user, 'logs'):
            self.access_denied(user)
        
        stats = multi.get_stats_for_servers()
        data = []
        
        for server in stats:
            server = stats[server]
            server.pop('time') # We dont need the request time 
            data.append(server)
            
        self.return_response(200, {}, data, {})
        
class SearchMCLogs(BaseHandler):
    
    def initialize(self, mcserver):
        self.mcserver = mcserver
        
    def post(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access') and not check_role_permission(user, 'logs'):
            self.access_denied(user)
            
        search_string = self.get_argument('query', default=None, strip=True)
        server_id = self.get_argument('id')
        
        server = multi.get_server_obj(server_id)
        logfile = os.path.join(server.server_path, 'logs', 'latest.log')
        
        data = helper.search_file(logfile, search_string)
        line_list = []
        
        if data:
            for line in data:
                line_list.append({'line_num': line[0], 'message': line[1]})
                
        self.return_response(200, {}, line_list, {})
    
class GetMCLogs(BaseHandler):
    
    def initialize(self, mcserver):
        self.mcserver = mcserver
        
    def get(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access') and not check_role_permission(user, 'logs'):
            self.access_denied(user)
        
        server_id = self.get_argument('id')
        server = multi.get_server_obj(server_id)

        logfile = os.path.join(server.server_path, 'logs', 'latest.log')
        data = helper.search_file(logfile, '')
        line_list = []
        
        if data:
            for line in data:
                line_list.append({'line_num': line[0], 'message': line[1]})
                
        self.return_response(200, {}, line_list, {})    
        
class GetCraftyLogs(BaseHandler):
        
    def get(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access') and not check_role_permission(user, 'logs'):
            self.access_denied(user)
            
        filename = self.get_argument('name')
        logfile = os.path.join('logs', filename + '.log')
        
        data = helper.search_file(logfile, '')
        line_list = []
        
        if data:
            for line in data:
                line_list.append({'line_num': line[0], 'message': line[1]})
                
        self.return_response(200, {}, line_list, {}) 
        
class SearchCraftyLogs(BaseHandler):
        
    def post(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access') and not check_role_permission(user, 'logs'):
            self.access_denied(user)
            
        filename = self.get_argument('name')
        query = self.get_argument('query')
        logfile = os.path.join('logs', filename + '.log')
        
        data = helper.search_file(logfile, query)
        line_list = []
        
        if data:
            for line in data:
                line_list.append({'line_num': line[0], 'message': line[1]})
                
        self.return_response(200, {}, line_list, {}) 

class ForceServerBackup(BaseHandler):
    
    def initialize(self, mcserver):
        self.mcserver = mcserver
        
    def post(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access') and not check_role_permission(user, 'backups'):
            self.access_denied(user)
            
        server_id = self.get_argument('id')
        server = multi.get_server_obj(server_id)
            
        backup_thread = threading.Thread(name='backup', target=server.backup_server, daemon=False)
        backup_thread.start()
        
        self.return_response(200, {}, {'code':'SER_BAK_CALLED'}, {})

class StartServer(BaseHandler):
    
    def initialize(self, mcserver):
        self.mcserver = mcserver
    
    def post(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access') and not check_role_permission(user, 'svr_control'):
            self.access_denied(user)
        
        server_id = self.get_argument('id')
        server = multi.get_server_obj(server_id)
            
        if not server.check_running():
            Remote.insert({
                Remote.command: 'start_mc_server',
                Remote.server_id: server_id,
                Remote.command_source: "localhost"
            }).execute()
            self.return_response(200, {}, {'code':'SER_START_CALLED'}, {})
        else:
            self.return_response(500, {'error':'SER_RUNNING'}, {}, {})
    
class StopServer(BaseHandler):
    
    def initialize(self, mcserver):
        self.mcserver = mcserver
        
    def post(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access') and not check_role_permission(user, 'svr_control'):
            self.access_denied(user)
        
        server_id = self.get_argument('id')
        server = multi.get_server_obj(server_id)
        
        if server.check_running():
            Remote.insert({
                Remote.command: 'stop_mc_server',
                Remote.server_id: server_id,
                Remote.command_source: "localhost"
            }).execute()
            
            self.return_response(200, {}, {'code':'SER_STOP_CALLED'}, {})
        else:
            self.return_response(500, {'error':'SER_NOT_RUNNING'}, {}, {})

class RestartServer(BaseHandler):
        
    def initialize(self, mcserver):
        self.mcserver = mcserver
        
    def post(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access') and not check_role_permission(user, 'svr_control'):
            self.access_denied(user)
        
        server_id = self.get_argument('id')
        server = multi.get_server_obj(server_id)
                
        server.restart_threaded_server()
        self.return_response(200, {}, {'code':'SER_RESTART_CALLED'}, {})

class CreateUser(BaseHandler):
    
    def post(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access') and not check_role_permission(user, 'config'):
            self.access_denied(user)
        
        new_username = self.get_argument("username")
        
        # TODO: implement role checking
        #new_role = self.get_argument("role", 'Mod')

        if new_username:
            new_pass = helper.random_string_generator()
            new_token = secrets.token_urlsafe(32)
            result = Users.insert({
                Users.username: new_username,
                Users.role: 'Mod',
                Users.password: helper.encode_pass(new_pass),
                Users.api_token: new_token
            }).execute()
            
            self.return_response(200, {}, {'code':'COMPLETE', 'username': new_username, 'password': new_pass, 'api_token': new_token}, {})
        else:
            self.return_response(500, {'error':'MISSING_PARAMS'}, {}, {'info':'Some paramaters failed validation'})

class DeleteUser(BaseHandler):
    
    def post(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access') and not check_role_permission(user, 'config'):
            self.access_denied(user)
        
        username = self.get_argument("username", None, True)

        if username == 'Admin':
            self.return_response(500, {'error':'NOT_ALLOWED'}, {}, {'info':'You cannot delete the admin user'})
        else:
            if username:
                Users.delete().where(Users.username == username).execute()
                self.return_response(200, {}, {'code':'COMPLETED'}, {})
                
class ListServers(BaseHandler):
    
    def initialize(self, mcserver):
        self.mcserver = mcserver
    
    def get(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access'):
            self.access_denied(user)
        
        self.return_response(200, {}, {"code": "COMPLETED", "servers": multi.list_servers()}, {})

            
        