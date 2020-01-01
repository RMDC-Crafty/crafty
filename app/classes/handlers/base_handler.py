import tornado.web
import logging

logger = logging.getLogger(__name__)

class BaseHandler(tornado.web.RequestHandler):
    # tornado.locale.set_default_locale('es_ES')
    # tornado.locale.set_default_locale('de_DE')

    def get_current_user(self):
        return self.get_secure_cookie("user", max_age_days=1)
