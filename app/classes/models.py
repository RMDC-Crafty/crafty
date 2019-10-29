from peewee import *
import datetime
from app.classes.helpers import helpers

helper = helpers()

# SQLite database using WAL journal mode and 10MB cache.
database = SqliteDatabase(helper.get_db_path(), pragmas={
    'journal_mode': 'wal',
    'cache_size': -1024 * 10})

class BaseModel(Model):
    class Meta:
        database = database

class Users(BaseModel):
    username = CharField(unique=True)
    password = CharField()
    role = CharField()

class MC_settings(BaseModel):
    server_path = CharField()
    server_jar = CharField()
    memory_max = CharField()
    memory_min = CharField()
    additional_args = CharField()
    auto_start_server = BooleanField()
    auto_start_delay = IntegerField()

class Webserver(BaseModel):
    port_number = IntegerField()
    server_name = CharField()

def create_tables():
    with database:
        database.create_tables([Users, MC_settings, Webserver])
