import tornado.web
import tornado.escape 
import logging.config

from app.classes.models import Roles, Users, check_role_permission
from app.classes.helpers import helper

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
        self.finish(self.return_response(403, 'accessdenied', '', 'You were denied access to the requested resource'))
    
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


class Online(BaseHandler):
    
    def get(self):
        token = self.get_argument('token')
        user = self.authenticate_user(token)
        
        if user is None:
            self.access_denied('unknown')
        
        if not check_role_permission(user, 'api_access'):
            self.access_denied(user)

        self.return_response(200, '', {'online':True}, '')
        
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
        if command:
            if self.mcserver.check_running:
                self.mcserver.send_command(command)
                self.return_response(200, '', {"run": True}, '')
            else:
                self.return_response(200, {'error':'SVR_NOT_RUNNING'}, {}, {})
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
        
        server_stats = helper.get_installation_stats(self.mcserver)
        
        self.return_response(200, {}, server_stats, {})
        
        
            
            
    
    