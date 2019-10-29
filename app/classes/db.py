import sqlite3

from sqlite3 import Error

class db_wrapper:

    def __init__(self, db_file):
        self.dbfile = db_file
        self.connection = None
        self.create_connection()

    def convert_to_dict(row):
        return dict(row)

    def create_connection(self):
        """ create a database connection to a SQLite database """
        try:
            self.connection = sqlite3.connect(self.dbfile)
            self.connection.row_factory = sqlite3.Row
        except Error as e:
            print(e)

    def create_table(self, table_sql):
        """ create a table from the create_table_sql statement
        :param conn: Connection object
        :param create_table_sql: a CREATE TABLE statement
        :return:
        """
        try:
            c = self.connection.cursor()
            c.execute(table_sql)
        except Error as e:
            print(e)

    def create_new_db(self):
        sql_create_users_table = '''CREATE TABLE IF NOT EXISTS`users` (
            `uid`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            `uname`	TEXT NOT NULL UNIQUE,
            `pass`	TEXT NOT NULL,
            `role`	TEXT NOT NULL
        );'''

        sql_create_mcserver_table = '''
        CREATE TABLE `mc_server` (
            `server_path`	TEXT NOT NULL,
            `server_jar`	TEXT NOT NULL,
            `memory_max`	INTEGER NOT NULL,
            `memory_min`	INTEGER NOT NULL,
            `additional_args`	TEXT NOT NULL,
            `auto_start_server`	INTEGER NOT NULL,
            `auto_start_delay`	INTEGER NOT NULL
        );

        '''

        sql_create_web_table = '''
        CREATE TABLE `webserver` (
            `port_number`	INTEGER NOT NULL,
            `server_name`	INTEGER NOT NULL
        );
        '''

        sql_create_backup_table = '''
                CREATE TABLE `backups` (
                    `auto_backup`	INTEGER NOT NULL,
                    `backup_path`	TEXT NOT NULL,
                    `backup_interval`	INTEGER NOT NULL,
                    `backup_interval_type`	TEXT NOT NULL
                );
                '''

        self.create_table(sql_create_users_table)
        self.create_table(sql_create_mcserver_table)
        self.create_table(sql_create_web_table)
        self.create_table(sql_create_backup_table)

    def run_sql(self, sql):
        cur = self.connection.cursor()
        cur.execute(sql)
        rows = cur.fetchall()

        results = []
        if len(rows) >= 1:
            for r in rows:
                results.append(dict(r))
            return results
        else:
            return False

    def run_sql_first_row(self, sql):
        results = self.run_sql(sql)
        if results:
            if len(results) >= 1:
                return dict(results[0])
            else:
                return False
        else:
            return False

    # mc server settings save
    def save_settings(self, mc_settings):
        sql = '''
        INSERT INTO `mc_server` 
        (server_path, server_jar, memory_max, memory_min, additional_args, auto_start_server, auto_start_delay) 
        VALUES(?,?,?,?,?,?,?)
        '''
        cur = self.connection.cursor()
        cur.execute(sql, mc_settings)
        self.connection.commit()
        return cur.lastrowid

    def get_mc_settings(self):
        sql = "SELECT * FROM `mc_server`"
        return self.run_sql_first_row(sql)

    # create a user
    def create_user(self, user_data):
        sql = '''
                INSERT INTO `users` 
                (uname, pass, role) 
                VALUES(?,?,?)
                '''
        cur = self.connection.cursor()
        cur.execute(sql, user_data)
        self.connection.commit()
        return cur.lastrowid

    # save the webserver settings
    def save_webserver_settings(self, settings):
        sql = '''
                INSERT INTO `webserver` 
                (port_number, server_name) 
                VALUES(?,?)
                '''
        cur = self.connection.cursor()
        cur.execute(sql, settings)
        self.connection.commit()
        return cur.lastrowid

    def get_user_data(self, username):
        sql = "SELECT * FROM  `users` WHERE uname = '{}' ".format(username)
        userdata = self.run_sql_first_row(sql)
        return userdata



