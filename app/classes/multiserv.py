import logging
from app.classes.minecraft_server import Minecraft_Server
from app.classes.models import MC_settings

logger = logging.getLogger(__name__)

class multi_serve():

    def __init__(self):
        self.servers_list = []

    def init_all_servers(self):
        all_servers = MC_settings.select()
        if len(all_servers) > 0:
            for s in all_servers:
                multi.setup_new_server_obj(s.id)
                srv_obj = multi.get_server_obj(s.id)

                srv_obj.reload_settings()
                server_name = srv_obj.get_mc_server_name(s.id)
                logger.info("Loading settings for server:{}".format(server_name))
        else:
            logger.info("No minecraft servers defined in database")

    def setup_new_server_obj(self, server_id):
        server_instance = {
            'server_id': server_id,
            'server_obj': Minecraft_Server()
        }
        server_instance['server_obj'].do_init_setup(server_id)

        self.servers_list.append(server_instance)

    def remove_server_object(self, server_id):
        for s in self.servers_list:
            if s['server_id'] == server_id:
                s['server_obj'].stop_threaded_server()
                self.servers_list.remove(s)

    def get_first_server_object(self):
        if len(self.servers_list) > 0:
            return self.servers_list[0]['server_obj']
        else:
            return False

    def list_servers(self):
        return self.servers_list

    def get_server_obj(self, server_id):
        for s in self.servers_list:
            if s['server_id'] == server_id:
                return s['server_obj']

    def run_server(self, server_id):
        svr_obj = self.get_server_obj(server_id)
        svr_obj.run_threaded_server()

    def stop_server(self, server_id):
        svr_obj = self.get_server_obj(server_id)
        svr_obj.stop_threaded_server()

    def stop_all_servers(self):
        logger.info("Stopping All Servers")
        all_servers = MC_settings.select()
        if len(all_servers) > 0:
            for s in all_servers:
                self.stop_server(s.id)
                server_name = s.get_mc_server_name()
                logger.info("Stopping server:{}".format(server_name))


multi = multi_serve()
