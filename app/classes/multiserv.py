import logging
from app.classes.minecraft_server import Minecraft_Server
from app.classes.models import MC_settings, Server_Stats
from playhouse.shortcuts import *

logger = logging.getLogger(__name__)


class multi_serve():

    def __init__(self):
        self.servers_list = {}

    def init_all_servers(self):

        if len(self.servers_list) > 0:
            logger.warning("Servers already defined / initiated. Call init_all_servers only once")
            return False

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

                # echo it's now setup to the log
                logger.info("Loading settings for server:{}".format(s.server_name))
        else:
            logger.info("No minecraft servers defined in database")

    def get_server_data(self,server_id):
        if MC_settings.get_by_id(server_id):
            return MC_settings.get_by_id(server_id)
        else:
            logger.critical("Unable to find server id: {}".format(server_id))
            return False

    def setup_new_server_obj(self, server_id):
        server_data = self.get_server_data(server_id)

        if server_data.server_name not in self.servers_list.keys():
            self.servers_list[server_data.server_name] = {
                'server_id': server_id,
                'server_name': server_data.server_name,
                'server_obj': Minecraft_Server()
                }

            self.servers_list[server_data.server_name]['server_obj'].do_init_setup(server_id)
        else:
            logger.critical("Server: {} is already defined!".format(server_data.name))

    def remove_server_object(self, server_id):
        server_data = self.get_server_data(server_id)
        try:
            del self.servers_list[server_data.server_name]
        except:
            pass

    def get_first_server_object(self):
        if len(self.servers_list) > 0:
            srv_obj = next(iter(self.servers_list.items()))
            return srv_obj[1]['server_obj']
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
        server_data = self.get_server_data(server_id)
        if self.servers_list[server_data.server_name]:
            return self.servers_list[server_data.server_name]['server_obj']
        else:
            logger.warning("Unable to find server object for server: {}".format(server_id))

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

    def do_stats_for_servers(self):
        if len(self.servers_list) > 0:

            # for each server defined
            for s in iter(self.servers_list.items()):

                # delete the old history stats for this server
                Server_Stats.delete().where(Server_Stats.server_id == int(s[1]['server_id'])).execute()

                # get the server object
                srv_obj = s[1]['server_obj']

                # get the stats from the object
                stats = srv_obj.get_mc_process_stats()

                Server_Stats.insert({
                    Server_Stats.server_id: s[1]['server_id'],
                    Server_Stats.server_start_time: stats['server_start_time'],
                    Server_Stats.server_running: stats['server_running'],
                    Server_Stats.cpu_usage: stats['cpu_usage'],
                    Server_Stats.memory_usage: stats['memory_usage'],
                    Server_Stats.world_name: stats['world_name'],
                    Server_Stats.world_size: stats['world_size'],
                    Server_Stats.online_players: stats['online'],
                    Server_Stats.max_players: stats['max'],
                    Server_Stats.players: stats['players'],
                    Server_Stats.motd: stats['server_description'],
                    Server_Stats.server_version: stats['server_version'],
                }).execute()

    def get_stats_for_servers(self):

        all_servers_return = {}

        if len(self.servers_list) > 0:

            # for each server defined
            for s in iter(self.servers_list.items()):
                    server_id = s[1]['server_id']
                    q = Server_Stats.select().where(Server_Stats.server_id == int(server_id))

                    if q.exists():
                        server_stats = Server_Stats.get(Server_Stats.server_id == int(server_id))
                        all_servers_return.update({server_id: model_to_dict(server_stats)})
        return all_servers_return

multi = multi_serve()
