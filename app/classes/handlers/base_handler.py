import tornado.web
import logging

logger = logging.getLogger(__name__)

class BaseHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        #self.set_header("Permissions-Policy
        #self.set_header("Content-Security-Policy
        self.set_header("Strict-Transport-Security", "max-age=31536000")
        self.set_header("X-XSS-Protection", "1; mode=block")
        self.set_header("X-Frame-Options", "DENY")
        self.set_header("X-Content-Type-Options", "nosniff")

    def get_current_user(self):
        return self.get_secure_cookie("user", max_age_days=1)
