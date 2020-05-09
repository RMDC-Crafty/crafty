import os
import json
import datetime
from peewee import DateTimeField, CharField, FloatField, Model, IntegerField, BooleanField, SqliteDatabase, AutoField
from playhouse.shortcuts import model_to_dict, dict_to_model
from playhouse.migrate import *
from app.classes.helpers import helper
import logging

# SQLite database using WAL journal mode and 10MB cache.
# Note: runs on import
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


class Command_Webhooks(BaseModel):
    id = AutoField()
    name = CharField(max_length=64, unique=True)
    method = CharField(default="POST")
    url = CharField(unique=True)
    on_command = CharField()
    send_data = BooleanField(default=True)


class Event_Webhooks(BaseModel):
    id = AutoField()
    name = CharField(max_length=64, unique=True)
    method = CharField(default="POST")
    url = CharField(unique=True)
    on_event = CharField()
    send_data = BooleanField(default=True)


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
    server_id = IntegerField()

    class Meta:
        table_name = 'backups'


class Users(BaseModel):
    username = CharField(unique=True)
    password = CharField()
    api_token = CharField(max_length=32, unique=True)
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
    api_access = BooleanField(default=0)

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
    java_path = CharField()
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
    language = CharField(default='en_EN')

    class Meta:
        table_name = 'crafty_settings'


class Webserver(BaseModel):
    port_number = IntegerField()

    class Meta:
        table_name = 'webserver'


class Schedules(BaseModel):
    id = IntegerField(unique=True, primary_key=True)
    server_id = IntegerField()
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
                                    Host_Stats,
                                    Event_Webhooks,
                                    Command_Webhooks]
                                   )

    def default_settings(self, admin_pass, admin_token):

        from app.classes.helpers import helper

        Users.insert({
            Users.username: 'Admin',
            Users.password: helper.encode_pass(admin_pass),
            Users.role: 'Admin',
            Users.api_token: admin_token,
            Users.enabled: True
        }).execute()

        # default crafty_settings
        q = Crafty_settings.insert({
            Crafty_settings.history_interval: 60,
            Crafty_settings.history_max_age: 2,
            Crafty_settings.language: "en_EN"
        })

        q.execute()

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
                Roles.files: 1,
                Roles.api_access: 1
            },
            {
                Roles.name: 'Staff',
                Roles.svr_control: 0,
                Roles.svr_console: 0,
                Roles.logs: 1,
                Roles.backups: 1,
                Roles.schedules: 1,
                Roles.config: 0,
                Roles.api_access: 0

            },
            {
                Roles.name: 'Backup',
                Roles.svr_control: 0,
                Roles.svr_console: 0,
                Roles.logs: 1,
                Roles.backups: 1,
                Roles.schedules: 0,
                Roles.config: 0,
                Roles.api_access: 0
            },
            {
                Roles.name: 'Mod',
                Roles.svr_control: 0,
                Roles.svr_console: 0,
                Roles.logs: 1,
                Roles.backups: 0,
                Roles.schedules: 0,
                Roles.config: 0,
                Roles.api_access: 0
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

    # this is our upgrade migration function
    # default settings created here if they don't already exits

    def do_database_migrations(self):
        migrator = SqliteMigrator(database)
        language = CharField(default='en_EN')

        # grab all the columns in the crafty settings table
        crafty_settings = database.get_columns("crafty_settings")

        has_lang = False

        # loop through columns and see if we have a language column
        for setting in crafty_settings:
            if setting.name == "language":
                has_lang = True

        # if we don't have a lang column, let's add one
        if not has_lang:
            migrate(
                migrator.add_column('crafty_settings', 'language', language)
            )

            # let's update the row with our default lang
            Crafty_settings.update({
                Crafty_settings.language: "en_EN"
            }).where(Crafty_settings.id == 1).execute()

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
            user_data['api_access'] = data['api_access']

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
