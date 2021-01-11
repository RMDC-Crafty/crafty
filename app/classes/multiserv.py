import time
import logging
import psutil
import datetime
import schedule


from app.classes.minecraft_server import Minecraft_Server
from app.classes.models import *
from app.classes.helpers import helper
from app.classes.console import console

logger = logging.getLogger(__name__)


class multi_serve():

    def __init__(self):
        self.servers_list = {}

    def get_auto_start_servers_by_rank(self, priority):
        # priority is 1 = high, 2 = medium, 3 = low
        # this returns a list of servers who are setup for auto start, ordered by delay

        if priority == 1:
            logger.info("Getting High Priority Auto Starting Servers")

        elif priority == 2:
            logger.info("Getting Medium Priority Auto Starting Servers")

        else:
            logger.info("Getting Low Priority Auto Starting Servers")

        temp_list = []

        # let's get the priority auto starting servers ordered by delay (lowest delay first)
        servers = MC_settings.select().order_by(MC_settings.auto_start_delay).where(
            MC_settings.auto_start_server == 1,
            MC_settings.auto_start_priority == priority
        )

        for s in servers:
            temp_list.append({
                'id': s.id,
                'name': s.server_name,
                'delay': s.auto_start_delay
            })
        return temp_list

    def init_all_servers(self):

        all_servers = []

        if len(self.servers_list) > 0:
            logger.info("Don't re-init all servers twice")
            return False

        # high priority
        all_servers = all_servers + self.get_auto_start_servers_by_rank(1)

        # medium
        all_servers = all_servers + self.get_auto_start_servers_by_rank(2)

        # low
        all_servers = all_servers + self.get_auto_start_servers_by_rank(3)

        # let's get the non auto starting servers...
        other_servers = MC_settings.select().where(MC_settings.auto_start_server == 0)

        # for each other server not starting, we can just add them whenever
        for s in other_servers:
            all_servers.append({
                'id': s.id,
                'name': s.server_name,
                'delay': s.auto_start_delay
            })

        # for each auto starting server defined
        for s in all_servers:
            # setup the server obj - this kicks off the autostart
            self.setup_new_server_obj(s['id'])

            # create a server object from this id number
            srv_obj = self.get_server_obj(s['id'])

            # reload the server settings
            srv_obj.reload_settings()

            # echo it's now setup to the log
            logger.info("Loading settings for server %s", s['name'])

    def reload_scheduling(self):
        self.reload_user_schedules()
        self.reload_history_settings()


    def reload_user_schedules(self):
        logger.info("Reloading Scheduled Tasks")

        db_data = Schedules.select()

        # clear all user jobs
        schedule.clear('user')

        logger.info("Deleting all old users tasks")

        logger.info("There are {} scheduled jobs to parse:".format(len(db_data)))

        # loop through the tasks in the db
        for task in db_data:
            svr_obj = multi.get_server_obj(task.server_id)
            helper.scheduler(task, svr_obj)

    def do_server_history(self):
        running = self.list_running_servers()
        for s in running:
            srv_obj = self.get_server_obj(s['id'])
            srv_obj.write_usage_history()

    def reload_history_settings(self):
        logger.info("Clearing history usage scheduled jobs")

        # clear all history jobs
        schedule.clear('history')

        query = Crafty_settings.select(Crafty_settings.history_interval)
        history_interval = query[0].history_interval

        logger.info("Creating new history usage scheduled task for every %s minutes", history_interval)

        schedule.every(history_interval).minutes.do(self.do_server_history).tag('history')

    def get_server_data(self, server_id):
        if MC_settings.get_by_id(server_id):
            return MC_settings.get_by_id(server_id)
        else:
            logger.critical("Unable to find server id %s", server_id)
            return False

    def setup_new_server_obj(self, server_id):
        server_data = self.get_server_data(server_id)

        if server_data.server_name not in self.servers_list.keys():
            self.servers_list[server_data.server_name] = {
                'server_id': server_id,
                'server_name': server_data.server_name,
                'server_obj': Minecraft_Server()
                }

            # this kicks off the auto start for this server object
            self.servers_list[server_data.server_name]['server_obj'].do_init_setup(server_id)
        else:
            logger.critical("Server %s is already defined!", server_data.name)

    def remove_server_object(self, server_id):

        svr_obj = self.get_server_obj(server_id)
        server_name = svr_obj.get_mc_server_name()

        try:
            del self.servers_list[server_name]
            logger.info("Removed server \"%s\" from multi server list", server_name)

            # delete the server - and clean up other areas of the db
            MC_settings.delete().where(MC_settings.id == int(server_id)).execute()
            Backups.delete().where(Backups.server_id == int(server_id)).execute()
            History.delete().where(History.server_id == int(server_id)).execute()
            Server_Stats.delete().where(Server_Stats.server_id == int(server_id)).execute()


            logger.info('Deleted Server ID %s', server_id)

        except:
            logger.exception("Unable to remove server ID %s (%s) from multi server list. Traceback:", server_id, server_name)
            pass

        # print('reloading scheduling')
        # self.reload_scheduling()

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
                        'crashed': srv_obj.check_crashed(),
                        'auto_start': srv_obj.settings.auto_start_server
                    })

        return server_list

    def get_server_obj(self, server_id):
        server_data = self.get_server_data(server_id)
        try:
            if self.servers_list[server_data.server_name]:
                return self.servers_list[server_data.server_name]['server_obj']
            else:
                logger.warning("Unable to find server object for server id %s", server_id)
        except:
            logger.exception("Exception occured when finding server id %s", server_id)

    def run_server(self, server_id):
        Remote.insert({
            Remote.command: 'start_mc_server',
            Remote.server_id: server_id,
            Remote.command_source: 'local'
        }).execute()

    def stop_server(self, server_id):
        Remote.insert({
            Remote.command: 'stop_mc_server',
            Remote.server_id: server_id,
            Remote.command_source: 'local'
        }).execute()

    def stop_all_servers(self):
        servers = self.list_running_servers()
        logger.info("Found %s running server(s)", len(servers))
        logger.info("Stopping All Servers")

        for s in servers:
            logger.info("Stopping Server ID %s (%s)", s['id'], s['name'])
            console.info("Stopping Server ID {} ({})".format(s['id'], s['name']))

            # get object
            svr_obj = self.get_server_obj(s['id'])
            running = svr_obj.check_running()

            # issue the stop command
            self.stop_server(s['id'])

            # while it's running, we wait
            while running:
                logger.info("Server %s is still running - waiting 2s to see if it stops", s['name'])
                console.info("Server {} is still running - waiting 2s to see if it stops".format(s['name']))
                running = svr_obj.check_running()
                time.sleep(2)

            # let's wait 2 seconds so the remote commands get cleared and then we can do another loop
            time.sleep(2)

        logger.info("All Servers Stopped")

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

                # get the server object
                srv_obj = s[1]['server_obj']

                # get the stats from the object
                stats = srv_obj.get_mc_process_stats()

                # delete the old history stats for this server
                # Server_Stats.delete().where(Server_Stats.server_id == int(s[1]['server_id'])).execute()

                exists = Server_Stats.select().where(Server_Stats.server_id == int(s[1]['server_id'])).exists()

                if exists:
                    Server_Stats.update({
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
                        Server_Stats.server_ip: stats['server_ip'],
                        Server_Stats.server_port: stats['server_port'],
                    }).where(Server_Stats.server_id == int(s[1]['server_id'])).execute()
                else:
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
                        Server_Stats.server_ip: stats['server_ip'],
                        Server_Stats.server_port: stats['server_port'],
                    }).execute()

    def get_stats_for_server(self, server_id):
        q = Server_Stats.select().where(Server_Stats.server_id == int(server_id))

        if q.exists():
            server_stats = Server_Stats.get(Server_Stats.server_id == int(server_id))
            return model_to_dict(server_stats)
        else:
            return False

    def get_stats_for_servers(self):

        all_servers_return = {}

        if len(self.servers_list) > 0:

            # for each server defined
            for s in iter(self.servers_list.items()):
                    server_id = s[1]['server_id']
                    q = Server_Stats.select().where(Server_Stats.server_id == int(server_id))

                    if q.exists():
                        server_stats = Server_Stats.get(Server_Stats.server_id == int(server_id))
                        stats = model_to_dict(server_stats)

                        # let's get the server object - and ask it's name
                        srv_obj = self.get_server_obj(server_id)
                        stats['name'] = srv_obj.get_mc_server_name(server_id)

                        # all_servers_return.update({server_id: model_to_dict(server_stats)})
                        all_servers_return.update({server_id: stats})
        return all_servers_return

    def do_host_status(self):
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())

        try:
            cpu_freq = psutil.cpu_freq()
        except NotImplementedError:
            cpu_freq = psutil._common.scpufreq(current=0, min=0, max=0)
        if cpu_freq is None:
            cpu_freq = psutil._common.scpufreq(current=0, min=0, max=0)

        insert_id = Host_Stats.insert({
            Host_Stats.boot_time: str(boot_time),
            Host_Stats.cpu_usage: round(psutil.cpu_percent(interval=0.5) / psutil.cpu_count(), 2),
            Host_Stats.cpu_cores: psutil.cpu_count(),
            Host_Stats.cpu_cur_freq: round(cpu_freq[0], 2),
            Host_Stats.cpu_max_freq: cpu_freq[2],
            Host_Stats.mem_percent: psutil.virtual_memory()[2],
            Host_Stats.mem_usage: helper.human_readable_file_size(psutil.virtual_memory()[3]),
            Host_Stats.mem_total: helper.human_readable_file_size(psutil.virtual_memory()[0]),
            Host_Stats.disk_percent: psutil.disk_usage('/')[3],
            Host_Stats.disk_usage: helper.human_readable_file_size(psutil.disk_usage('/')[1]),
            Host_Stats.disk_total: helper.human_readable_file_size(psutil.disk_usage('/')[0]),
        }).execute()

        # make sure we only have 1 record/row
        Host_Stats.delete().where(Host_Stats.id < int(insert_id)).execute()

    def get_host_status(self):
        q = Host_Stats.get()
        data = model_to_dict(q)
        return data


multi = multi_serve()
