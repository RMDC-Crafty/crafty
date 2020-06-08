import tornado.web
import logging

logger = logging.getLogger(__name__)

class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        return self.get_secure_cookie("user", max_age_days=1)
