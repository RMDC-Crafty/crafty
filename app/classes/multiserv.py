import logging
from app.classes.minecraft_server import Minecraft_Server

logger = logging.getLogger(__name__)

class multi_serve():

    def __init__(self):
        self.servers_list = []

    def setup_new_server_obj(self, server_id):
        server_instance = {
            'server_id': server_id,
            'server_obj': Minecraft_Server()
        }
        server_instance['server_obj'].do_init_setup(server_id)

        self.servers_list.append(server_instance)

    def remove_server_object(self,server_id):
        for s in self.servers_list:
            if s['server_id'] == server_id:
                s['server_obj'].stop_threaded_server()
                self.servers_list.remove(s)

    def list_servers(self):
        print(self.servers_list)

    def get_server_obj(self,server_id):
        for s in self.servers_list:
            if s['server_id'] == server_id:
                return s['server_obj']




multi = multi_serve()