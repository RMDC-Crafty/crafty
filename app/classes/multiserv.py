import logging
from app.classes.minecraft_server import Minecraft_Server
from app.classes.models import MC_settings

logger = logging.getLogger(__name__)

class multi_serve():

    def __init__(self):
        self.servers_list = []

    def init_all_servers(self):

        self.servers_list = []

        all_servers = MC_settings.select()

        if len(all_servers) > 0:

            # for each server defined
            for s in all_servers:
                # setup the server obj
                self.setup_new_server_obj(s.id)

                # create a server object from this id number
                srv_obj = self.get_server_obj(s.id)

                # reload the server settings
                srv_obj.reload_settings()

                # set the server name
                server_name = srv_obj.get_mc_server_name(s.id)
                # echo it's now setup to the log
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

        all_servers = MC_settings.select()
        server_list = []
        if len(all_servers) > 0:
            # for each server
            for s in all_servers:
                # is the server running?
                srv_obj = self.get_server_obj(s.id)

                server_list.append({
                        'id': srv_obj.server_id,
                        'name': srv_obj.get_mc_server_name(),
                        'running': srv_obj.check_running(),
                        'auto_start': srv_obj.settings.auto_start_server
                    })

        return server_list

    def get_server_obj(self, server_id):
        for s in self.servers_list:
            if int(s['server_id']) == int(server_id):
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

    def list_running_servers(self):
        all_servers = MC_settings.select()
        running_servers = []

        if len(all_servers) > 0:
            # for each server
            for s in all_servers:
                # is the server running?
                srv_obj = multi.get_server_obj(s.id)
                running = srv_obj.check_running()

                # if so, let's add a dictonary to the list of running servers
                if running:
                    running_servers.append({
                        'id': srv_obj.server_id,
                        'name': srv_obj.get_mc_server_name()
                    })

        return running_servers

    def get_server_root_path(self, server_id):
        srv_obj = self.get_server_obj(int(server_id))
        return srv_obj.server_path




multi = multi_serve()
