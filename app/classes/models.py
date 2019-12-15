import os
import json
import datetime
from peewee import *
from playhouse.shortcuts import model_to_dict, dict_to_model
from playhouse.migrate import *
from app.classes.helpers import helpers
import logging

helper = helpers()

# SQLite database using WAL journal mode and 10MB cache.
database = SqliteDatabase(helper.get_db_path(), pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 10})


class BaseModel(Model):
    class Meta:
        database = database


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

    class Meta:
        table_name = "remote"


class MC_settings(BaseModel):
    server_path = CharField()
    server_jar = CharField()
    memory_max = CharField()
    memory_min = CharField()
    additional_args = CharField()
    pre_args = CharField(default='')
    auto_start_server = BooleanField()
    auto_start_delay = IntegerField()
    server_port = IntegerField(default=25565)
    server_ip = CharField(default='127.0.0.1')

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
    time = DateTimeField(default=datetime.datetime.now)
    cpu = FloatField()
    memory = FloatField()
    players = IntegerField()

    class Meta:
        table_name = 'history'

def create_tables():
    with database:
        database.create_tables([Users,
                                MC_settings,
                                Webserver,
                                Schedules,
                                History,
                                Crafty_settings,
                                Backups,
                                Roles,
                                Remote]
                               )

def default_settings(admin_pass):

    # get minecraft settings for the server root
    # mc_data = MC_settings.get()
    # data = model_to_dict(mc_data)
    # directories = [data['server_path'], ]
    # backup_directory = json.dumps(directories)
    #
    # default backup settings
    # q = Backups.insert({
    #     Backups.directories: backup_directory,
    #     Backups.storage_location: os.path.abspath(os.path.join(helper.crafty_root, 'backups')),
    #     Backups.max_backups: 7
    # })

    # result = q.execute()

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

# this is our upgrade migration function - any new tables after 2.0 need to have
# default settings created here if they don't already exits

def do_database_migrations():
    logging.info('Upgrading Database fields as needed')
    create_tables()
    migrator = SqliteMigrator(database)

    roles_cols = database.get_columns('Roles')
    create_files_column = True

    for r in roles_cols:
        if r.name == "files":
            create_files_column = False

    if create_files_column:
        logging.info("Didn't find files column in roles - Creating one")

        # files permission for roles table
        files = BooleanField(default=0)

        # do our migrations
        migrate(
            migrator.add_column("Roles", 'files', files),
        )

        logging.info("Adding files perms to Admin")
        # give admin access to files permission
        Roles.update({
            Roles.files: 1
        }).where(Roles.name == "Admin").execute()


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
        logging.warning('User: {} attempted access to section {} and was denied'.format(username, section))

    return access