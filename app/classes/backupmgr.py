import os
import logging
import threading

from time import sleep

from app.classes.multiserv import multi_serve as multisrv

logger = logging.getLogger(__name__)

class MultiBackup():
    
    def backup_server(server_id):
        # Grab the server object
        logger.info("Backing up server %s", server_id)
        server_obj = multisrv.get_server_obj(server_id)
        # Start the backup thread
        backup_thread = threading.Thread(name='backup_server_{}'.format(server_id), target=server_obj.backup_server, daemon=False)
        backup_thread.start()
        logger.info("Backup thread running for server %s", server_id)
    
    def backup_all_servers():
        logger.warn("All server backup called. This may load your server massively!")
        # List all servers
        servers = multisrv.list_servers()
        
        # Iterate over them 
        for server in servers:
            server_id = server['id']
            
            # Grab the server object
            server_obj = multisrv.get_server_obj(server_id)
            
            # Start the backup thread
            logger.info("Backing up server %s", server_id)
            backup_thread = threading.Thread(name='backup_server_{}'.format(server_id), target=server_obj.backup_server, daemon=False)
            backup_thread.start()
            logger.info("Backup thread running for server %s", server_id)
            
            # Slow down the process creation for older systems
            sleep(1) 

backupmgr = MultiBackup()