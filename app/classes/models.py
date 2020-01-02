import os
import json
import datetime
from peewee import *
from playhouse.shortcuts import model_to_dict, dict_to_model
from playhouse.migrate import *
from app.classes.helpers import helper
import logging

# SQLite database using WAL journal mode and 10MB cache.
database = SqliteDatabase(helper.get_db_path(), pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 10})

logger = logging.getLogger(__name__)


class BaseModel(Model):
    class Meta:
        database = database

class Host_Stats(BaseModel):
    time = DateTimeField(default=datetime.datetime.now)
    boot_time = CharField()
    cpu_usage = FloatField()
    cpu_cores = IntegerField()
    cpu_cur_freq = FloatField()
    cpu_max_freq = FloatField()
    mem_percent = FloatField()
    mem_usage = CharField()
    mem_total = CharField()
    disk_percent = FloatField()
    disk_usage = CharField()
    disk_total = CharField()


class Server_Stats(BaseModel):
    server_id = IntegerField()
    time = DateTimeField(default=datetime.datetime.now)
    server_start_time = CharField()
    cpu_usage = FloatField()
    memory_usage = FloatField()
    max_players = IntegerField()
    online_players = IntegerField()
    players = CharField()
    motd = CharField()
    server_running = BooleanField()
    server_version = CharField()
    world_name = CharField()
    world_size = FloatField()
    server_ip = CharField()
    server_port = IntegerField()

    class Meta:
        table_name = "stats"


class Ftp_Srv(BaseModel):
    port = IntegerField()
    user = CharField()
    password = CharField()


class Backups(BaseModel):
    directories = CharField()
    storage_location = CharField()
    max_backups = IntegerField()

    class Meta:
        table_name = 'backups'


class Users(BaseModel):
    username = CharField(unique=True)
    password = CharField()
    role = CharField()
    enabled = BooleanField(default=True)

    class Meta:
        table_name = 'users'


class Roles(BaseModel):
    name = CharField(unique=True)
    svr_control = BooleanField(default=0)
    svr_console = BooleanField(default=0)
    logs = BooleanField(default=0)
    backups = BooleanField(default=0)
    schedules = BooleanField(default=0)
    config = BooleanField(default=0)
    files = BooleanField(default=0)

    class Meta:
        table_name = "roles"


class Remote(BaseModel):
    command = CharField()
    server_id = IntegerField()
    command_source = CharField(default="Localhost")

    class Meta:
        table_name = "remote"


class MC_settings(BaseModel):
    server_name = CharField(unique=True)
    server_path = CharField()
    server_jar = CharField()
    memory_max = CharField()
    memory_min = CharField()
    additional_args = CharField()
    pre_args = CharField(default='')
    auto_start_server = BooleanField()
    auto_start_delay = IntegerField()
    auto_start_priority = IntegerField()
    crash_detection = BooleanField()
    server_port = IntegerField(default=25565)
    server_ip = CharField(default='127.0.0.1')
    jar_url = CharField(default='')

    class Meta:
        table_name = 'mc_settings'


class Crafty_settings(BaseModel):
    history_interval = IntegerField()
    history_max_age = IntegerField()

    class Meta:
        table_name = 'crafty_settings'


class Webserver(BaseModel):
    port_number = IntegerField()

    class Meta:
        table_name = 'webserver'


class Schedules(BaseModel):
    id = IntegerField(unique=True, primary_key=True)
    enabled = BooleanField()
    action = CharField()
    interval = IntegerField()
    interval_type = CharField()
    start_time = CharField(null=True)
    command = CharField(null=True)
    comment = CharField()

    class Meta:
        table_name = 'schedules'


class History(BaseModel):
    id = IntegerField(unique=True, primary_key=True)
    server_id = IntegerField()
    time = DateTimeField(default=datetime.datetime.now)
    cpu = FloatField()
    memory = FloatField()
    players = IntegerField()

    class Meta:
        table_name = 'history'

class sqlhelper():


    def create_tables(self):
        with database:
            database.create_tables([Users,
                                    MC_settings,
                                    Webserver,
                                    Schedules,
                                    History,
                                    Crafty_settings,
                                    Backups,
                                    Roles,
                                    Remote,
                                    Ftp_Srv,
                                    Server_Stats,
                                    Host_Stats]
                                   )

    def default_settings(self, admin_pass):

        from app.classes.helpers import helper

        Users.insert({
            Users.username: 'Admin',
            Users.password: helper.encode_pass(admin_pass),
            Users.role: 'Admin',
            Users.enabled: True
        }).execute()

        # default crafty_settings
        q = Crafty_settings.insert({
            Crafty_settings.history_interval: 60,
            Crafty_settings.history_max_age: 2,
        })

        result = q.execute()

        # default roles
        perms_insert = [
            {
                Roles.name: 'Admin',
                Roles.svr_control: 1,
                Roles.svr_console: 1,
                Roles.logs: 1,
                Roles.backups: 1,
                Roles.schedules: 1,
                Roles.config: 1,
                Roles.files: 1
            },
            {
                Roles.name: 'Staff',
                Roles.svr_control: 0,
                Roles.svr_console: 0,
                Roles.logs: 1,
                Roles.backups: 1,
                Roles.schedules: 1,
                Roles.config: 0

            },
            {
                Roles.name: 'Backup',
                Roles.svr_control: 0,
                Roles.svr_console: 0,
                Roles.logs: 1,
                Roles.backups: 1,
                Roles.schedules: 0,
                Roles.config: 0
            },
            {
                Roles.name: 'Mod',
                Roles.svr_control: 0,
                Roles.svr_console: 0,
                Roles.logs: 1,
                Roles.backups: 0,
                Roles.schedules: 0,
                Roles.config: 0
            }
        ]

        Roles.insert_many(perms_insert).execute()

        Webserver.insert({
            Webserver.port_number: 8000,
        }).execute()

        Ftp_Srv.insert({
            Ftp_Srv.port: 2121,
            Ftp_Srv.user: 'ftps_user',
            Ftp_Srv.password: helper.random_string_generator(8)
        }).execute()

    # this is our upgrade migration function - any new tables after 2.0 need to have
    # default settings created here if they don't already exits

    def do_database_migrations(self):

        migrator = SqliteMigrator(database)

        mc_cols = database.get_columns("MC_settings")


def get_perms_for_user(user):
    user_data = {}
    user = model_to_dict(Users.get(Users.username == user))
    if user:
        data = model_to_dict(Roles.get(Roles.name == user['role']))
        if data:
            user_data['username'] = user['username']
            user_data['role_name'] = data['name']
            user_data['svr_control'] = data['svr_control']
            user_data['svr_console'] = data['svr_console']
            user_data['logs'] = data['logs']
            user_data['backups'] = data['backups']
            user_data['schedules'] = data['schedules']
            user_data['config'] = data['config']
            user_data['files'] = data['files']

    return user_data


def check_role_permission(username, section):
    user_data = get_perms_for_user(username)

    access = False

    if section in user_data.keys():
        if user_data[section]:
            access = True

    if not access:
        logger.warning('User: {} attempted access to section {} and was denied'.format(username, section))

    return access

peewee = sqlhelper()