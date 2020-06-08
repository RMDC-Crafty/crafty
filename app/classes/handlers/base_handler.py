import tornado.web
import logging
<<<<<<< HEAD
from app.classes.models import Crafty_settings
=======
>>>>>>> snapshot

logger = logging.getLogger(__name__)

class BaseHandler(tornado.web.RequestHandler):
<<<<<<< HEAD
=======
    # tornado.locale.set_default_locale('es_ES')
    # tornado.locale.set_default_locale('de_DE')
>>>>>>> snapshot

    def get_current_user(self):
        return self.get_secure_cookie("user", max_age_days=1)
