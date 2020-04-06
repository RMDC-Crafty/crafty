import tornado.web
import logging
from app.classes.models import Crafty_settings

logger = logging.getLogger(__name__)

class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        return self.get_secure_cookie("user", max_age_days=1)
