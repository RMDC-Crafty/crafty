import time
import tornado.web
import tornado.escape
import bleach
from pathlib import Path

from app.classes.console import console
from app.classes.models import *
from app.classes.handlers.base_handler import BaseHandler
from app.classes.multiserv import multi
from app.classes.ftp import ftp_svr_object

logger = logging.getLogger(__name__)

class SetupHandler(BaseHandler):

    def initialize(self, mcserver):
        self.mcserver = mcserver
        self.console = console

    @tornado.web.authenticated
    def get(self, page):

        context = {}
        template = ''

        errors = self.get_argument('errors', '')

        if page == 'step1':
            context = {
                'is_windows': helper.is_os_windows(),
                'mem': helper.get_memory(),
                'new_pass': helper.random_string_generator(10),
                'errors': errors
                }
            template = "setup/step1.html"
            helper.del_file(helper.new_install_file)

        else:
            # 404
            template = "public/404.html"
            context = {}

        self.render(
            template,
            data=context
        )

    def post(self, page):
        if page == 'step1':
            server_name = bleach.clean(self.get_argument('server_name', ''))
            server_path = bleach.clean(self.get_argument('server_path', ''))
            server_jar = bleach.clean(self.get_argument('server_jar', ''))
            max_mem = bleach.clean(self.get_argument('max_mem', ''))
            min_mem = bleach.clean(self.get_argument('min_mem', ''))
            auto_start = bleach.clean(self.get_argument('auto_start', ''))

            server_path_exists = helper.check_directory_exist(server_path)

            if not server_path_exists:
                self.redirect('/setup/step1.html?errors=Server Path not found')

            # Use pathlib to join specified server path and server JAR file then check if it exists
            jar_exists = helper.check_file_exists(os.path.join(server_path, server_jar))

            if not jar_exists:
                self.redirect('/setup/step1.html?errors=Server Jar not found')

            if server_path_exists and jar_exists:
                MC_settings.insert({
                    MC_settings.server_name: server_name,
                    MC_settings.server_path: server_path,
                    MC_settings.server_jar: server_jar,
                    MC_settings.memory_max: max_mem,
                    MC_settings.memory_min: min_mem,
                    MC_settings.additional_args: "",
                    MC_settings.java_path: "java",
                    MC_settings.auto_start_server: auto_start,
                    MC_settings.auto_start_delay: 10,
                    MC_settings.auto_start_priority: 1,
                    MC_settings.crash_detection: 0,
                    MC_settings.server_port: 25565,
                    MC_settings.server_ip: "127.0.0.1"
                }).execute()

                directories = [server_path, ]
                backup_directory = json.dumps(directories)

                # default backup settings
                Backups.insert({
                    Backups.directories: backup_directory,
                    Backups.storage_location: os.path.abspath(os.path.join(helper.crafty_root, 'backups')),
                    Backups.max_backups: 7,
                    Backups.server_id: 1
                }).execute()

                time.sleep(.5)

                # do initial setup
                multi.init_all_servers()

                # reload the server settings
                srv_obj = multi.get_first_server_object()
                srv_obj.reload_settings()

                # do FTP setup
                ftp_svr_object.setup_ftp()

                multi.do_stats_for_servers()
                multi.do_host_status()

                # load the dashboard
                self.redirect("/admin/dashboard")