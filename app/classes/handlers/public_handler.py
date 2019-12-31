import logging
import tornado.web
import tornado.escape

from app.classes.console import console
from app.classes.models import *
from app.classes.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)

class PublicHandler(BaseHandler):

    def initialize(self):
        self.console = console

    def set_current_user(self, user):
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user), expires_days=1)
        else:
            self.clear_cookie("user")

    def get(self, page=None):

        self.clear_cookie("user")

        server_data = self.get_server_data()

        template = "public/login.html"
        context = server_data
        context['login'] = None

        self.render(
            template,
            data=context
        )


    def post(self):
        entered_user = self.get_argument('username')
        entered_password = self.get_argument('password')


        try:
            user_data = Users.get(Users.username == entered_user)

            if user_data:
                # if the login is good and the pass verified, we go to the dashboard
                login_result = helper.verify_pass(entered_password, user_data.password)
                if login_result:
                    self.set_current_user(entered_user)

                    if helper.check_file_exists(helper.new_install_file):
                        next_page = "/setup/step1"
                    else:
                        next_page = '/admin/dashboard'

                    self.redirect(next_page)
        except:
            pass

        server_data = self.get_server_data()

        template = "public/login.html"
        context = server_data
        context['login'] = False

        self.render(
            template,
            data=context
        )



    def get_server_data(self):
        server_file = os.path.join( helper.get_web_temp_path(), "server_data.json")

        if helper.check_file_exists(server_file):
            with open(server_file, 'r') as f:
                server_data = json.load(f)
            return server_data
        else:
            logger.warning("Unable to find server_data file for dashboard: {}".format(server_file))
            fake_data = {
                "server_description": "Unable To Connect",
                "server_running": False,
                "server_version": "Unable to Connect",
            }
            return fake_data