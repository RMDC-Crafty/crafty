import tornado.web
import logging
from app.classes.handlers.base_handler import BaseHandler

logger = logging.getLogger(__name__)

class My404Handler(BaseHandler):
    # Override prepare() instead of get() to cover all possible HTTP methods.
    def prepare(self):
        self.set_status(404)
        self.render("public/404.html")