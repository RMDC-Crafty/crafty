import os
import logging
import threading

from time import sleep

from app.classes.multiserv import multi
from app.classes.helpers import helper
from app.classes.models import Backups, model_to_dict

logger = logging.getLogger(__name__)


class MultiBackup():

    def backup_server(self, server_id):
        # Grab the server object
        logger.info("Backing up server %s", server_id)
        server_obj = multi.get_server_obj(server_id)
        # Start the backup thread
        backup_thread = threading.Thread(name='backup_server_{}'.format(server_id), target=server_obj.backup_server, daemon=False)
        backup_thread.start()
        logger.info("Backup thread running for server %s", server_id)

    def backup_all_servers(self):
        logger.warning("All server backup called. This may load your server massively!")
        # List all servers
        servers = multi.list_servers()

        # Iterate over them
        for server in servers:
            server_id = server['id']

            # Grab the server object
            server_obj = multi.get_server_obj(server_id)

            # Start the backup thread
            logger.info("Backing up server %s", server_id)
            backup_thread = threading.Thread(name='backup_server_{}'.format(server_id), target=server_obj.backup_server, daemon=False)
            backup_thread.start()
            logger.info("Backup thread running for server %s", server_id)

            # Slow down the process creation for older systems
            sleep(1)

    def get_backup_folder_for_server(self, server_id):
        server_data = multi.get_server_data(server_id)
        backup_folder = "{}-{}".format(server_data.id, server_data.server_name)
        return backup_folder

    def list_backups_for_server(self, server_id):
        # Grab our backup path from the DB
        backup_list = Backups.get(Backups.server_id == int(server_id))

        # Join into a full path
        backup_folder = self.get_backup_folder_for_server(server_id)
        server_backup_dir = os.path.join(backup_list.storage_location, backup_folder)

        #helper.ensure_dir_exists(server_backup_dir)

        svr_obj = multi.get_server_obj(server_id)
        return svr_obj.list_backups()

    def list_all_backups(self):
        # Grab our backup path from the DB
        backup_list = Backups.get()
        backup_data = model_to_dict(backup_list)

        # List all MC Servers
        servers = multi.list_servers()
        backup_files = []

        # Iterate over all the servers
        for server in servers:
            server_id = server['id']

            # Create path
            path = os.path.join(backup_data['storage_location'], server_id)

            # Search and concat
            file_names, relative_files = helper.list_backups(path)
            backup_files = backup_data + relative_files
        return backup_files


backupmgr = MultiBackup()
