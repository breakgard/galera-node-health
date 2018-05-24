#!/usr/bin/python3

from galera_node_health import constants

from configparser import ConfigParser
from flask import Flask
from flask import request
import pymysql
import pymysql.constants.ER
import traceback
from werkzeug.contrib.fixers import CGIRootFix
import re


class GaleraNodeHealth(object):

    __supported_mysql_authentication = ('password', 'socket')
    __supported_mysql_connect_method = ('socket', 'tcp')

    __donor_blocking_sst_methods = ('rsync', 'mysqldump', 'rsync_wan')

    __status_sql_template = """select UPPER(variable_name) as v_name, variable_value as v_value
                       from {schema_and_table} 
                      where variable_name IN ('WSREP_READY', 'WSREP_LOCAL_STATE', 'WSREP_CLUSTER_STATUS',
                                               'WSREP_PROVIDER_NAME')"""
    __config_sql_template = """select UPPER(variable_name) as v_name, variable_value as v_value
                        from {schema_and_table}
                       where variable_name IN ('WSREP_REJECT_QUERIES', 'WSREP_SST_DONOR_REJECTS_QUERIES', 
                                               'WSREP_ON', 'WSREP_DESYNC', 'WSREP_OSU_METHOD', 'WSREP_SST_METHOD')"""
    __status_sql = __status_sql_template.format(schema_and_table='performance_schema.global_status')
    __config_sql = __config_sql_template.format(schema_and_table='performance_schema.global_variables')
    __status_sql_pre57 = __status_sql_template.format(schema_and_table='information_schema.global_status')
    __config_sql_pre57 = __config_sql_template.format(schema_and_table='information_schema.global_variables')

    def __init__(self, config_file=None, test_mode=False, print_config=False, root_fix=False):
        self.__maintenance_mode = False
        self.__status_query = self.__status_sql
        self.__config_query = self.__config_sql

        config_reader = ConfigParser(inline_comment_prefixes="#")
        if config_file is None:
            print("WARN: No config file set")
            print("WARN: Running with defaults")
        else:
            try:
                print("Using config file: " + str(config_file))
                with open(config_file, 'r') as config:
                    config_reader.read_file(config)
            except Exception:
                print("Cannot find or access file: " + str(config_file))
                print("Make sure it has proper permissions")
                raise
        self.__checker_port = int(config_reader.get('checker', 'port', fallback=8080))
        self.__checker_address = config_reader.get('checker', 'address', fallback='0.0.0.0')
        self.__checker_only_check_status = config_reader.getboolean('checker', 'only_check_status', fallback=False)
        self.__checker_enable_maint_mode = config_reader.getboolean('checker', 'enable_maint_mode', fallback=True)
        self.__checker_donor_ok = int(config_reader.get('checker', 'donor_ok', fallback=2))
        self.__checker_return_500_instead_of_404 = config_reader.getboolean('checker', 'return_500_instead_of_404',
                                                                            fallback=False)
        self.__mysql_user = config_reader.get('db', 'user', fallback='')
        if self.__mysql_user is None:
            self.__mysql_user = ''
        self.__mysql_auth = config_reader.get('db', 'auth_method', fallback='password')
        if self.__mysql_auth not in self.__supported_mysql_authentication:
            self.__not_supported("mysql_auth", self.__mysql_auth, str(self.__supported_mysql_authentication))

        self.__mysql_socket = config_reader.get('db', 'socket', fallback='/var/lib/mysql/mysql.sock')
        self.__mysql_connect_method = config_reader.get('db', 'connect_method', fallback='socket')
        if self.__mysql_connect_method not in self.__supported_mysql_connect_method:
            self.__not_supported("mysql_connect_method", self.__mysql_connect_method,
                                 str(self.__supported_mysql_connect_method))

        self.__mysql_port = int(config_reader.get('db', 'port', fallback=3306))
        self.__mysql_address = config_reader.get('db', 'address', fallback='127.0.0.1')
        self.__mysql_pass = config_reader.get('db', 'password', fallback='')
        if self.__mysql_pass is None:
            self.__mysql_pass = ''

        if self.__checker_return_500_instead_of_404:
            self.__maintenance_response_code = constants.RETURN_CODE_NOK
        else:
            self.__maintenance_response_code = constants.RETURN_CODE_MAINT
        if print_config:
            self.__print_startup_config()
        if not self.__check_connectivity():
            print("Looks like " + __class__.__name__ + " cannot connect to MySQL via " + self.__mysql_auth)
            print("Make sure the database is online")
            print("See if the database if configured properly for the auth settings in the checker")
            raise Exception("Cannot connect to MySQL when starting up!")

        self.flask_app = Flask(__class__.__name__)
        if root_fix:
            self.flask_app.wsgi_app = CGIRootFix(self.flask_app.wsgi_app)
        self.flask_app.add_url_rule('/health', 'health', self.health)
        if self.__checker_enable_maint_mode:
            self.flask_app.add_url_rule('/maint_on', 'maint_on', self.maintenance_on)
            self.flask_app.add_url_rule('/maint_off', 'maint_off', self.maintenance_off)
        if test_mode:
            self.flask_app.add_url_rule('/shutdown', 'shutdown', self.shutdown_dev)
            self.flask_app.config.from_mapping({"Testing": True})

    def __print_startup_config(self):
        print('###Printing startup config###')
        print('[checker]')
        print('address = ' + str(self.__checker_address))
        print('port = ' + str(self.__checker_port))
        print('enable_maint_mode = ' + str(self.__checker_enable_maint_mode))
        print('donor_ok = ' + str(self.__checker_donor_ok))
        print('return_500_instead_of_404 = ' + str(self.__checker_return_500_instead_of_404))
        print('only_check_status = ' + str(self.__checker_only_check_status))
        print('[db]')
        print('auth = ' + str(self.__mysql_auth))
        print('connect_method = ' + str(self.__mysql_connect_method))
        print('address = ' + str(self.__mysql_address))
        print('port = ' + str(self.__mysql_port))
        print('socket = ' + str(self.__mysql_socket))
        print('user = ' + str(self.__mysql_user))
        print('password = ' + str(self.__mysql_pass))
        print('###End of config###')

    @staticmethod
    def __not_supported(option, value, supported_values):
        print("GaleraHealthChecker does not support " + option + "=" + value)
        print("Supported values for " + option + ": " + supported_values)
        print("Please change it and restart.")
        raise Exception('Unsupported value in ' + option)

    def __check_connectivity(self):
        conn = None
        try:
            if self.__mysql_user == '':
                print('WARN: Using anonymous user to login - check your config.')
            if self.__mysql_auth == 'password' and self.__mysql_pass == '':
                print('WARN: Using empty password - check your config!')
            conn = self.__connect_to_db()
            with conn.cursor() as cur:
                cur.execute('select version() as v from dual;')
                version = cur.fetchone()['v']
                if re.search('MariaDB', version):
                    self.__status_query = self.__status_sql_pre57
                    self.__config_query = self.__config_sql_pre57
                elif re.search('^8.0.', version):
                    self.__status_query = self.__status_sql
                    self.__config_query = self.__config_sql
                elif re.search('^5.7.', version):
                    self.__status_query = self.__status_sql
                    self.__config_query = self.__config_sql
                elif re.search('^5.6.', version):
                    self.__status_query = self.__status_sql_pre57
                    self.__config_query = self.__config_sql_pre57
                elif re.search('^5.5.', version):
                    self.__status_query = self.__status_sql_pre57
                    self.__config_query = self.__config_sql_pre57
                else:
                    self.__status_query = self.__status_sql
                    self.__config_query = self.__config_sql
                cur.execute(self.__status_query)
                cur.execute(self.__config_query)
            return True
        except pymysql.MySQLError:
            traceback.print_exc()
            return False
        finally:
            if conn is not None and conn.open:
                conn.close()

    def __connect_to_db(self):
        if self.__mysql_auth == 'password':
            if self.__mysql_connect_method == 'socket':
                conn = pymysql.connect(unix_socket=self.__mysql_socket, user=self.__mysql_user,
                                       password=self.__mysql_pass, cursorclass=pymysql.cursors.DictCursor)
            elif self.__mysql_connect_method == 'tcp':
                conn = pymysql.connect(host=str(self.__mysql_address), port=int(self.__mysql_port),
                                       user=self.__mysql_user, password=self.__mysql_pass,
                                       cursorclass=pymysql.cursors.DictCursor)
            else:
                raise ValueError(self.__mysql_connect_method + " needs to be of "
                                 + str(self.__supported_mysql_connect_method))
        elif self.__mysql_auth == 'socket':
            conn = pymysql.connect(unix_socket=self.__mysql_socket, user=self.__mysql_user,
                                   cursorclass=pymysql.cursors.DictCursor)
        else:
            raise ValueError(self.__mysql_auth + " needs to be of " + str(self.__supported_mysql_authentication))
        return conn

    def health(self):
        if self.__maintenance_mode:
            return constants.OUTPUT_MAINT_ON, self.__maintenance_response_code
        conn = None
        try:
            conn = self.__connect_to_db()
            with conn.cursor() as cur:
                cur.execute(self.__status_query)
                status = {status_pair['v_name']: status_pair['v_value'] for status_pair in cur.fetchall()}
                cur.execute(self.__config_query)
                config = {config_pair['v_name']: config_pair['v_value'] for config_pair in cur.fetchall()}

                if status['WSREP_PROVIDER_NAME'] != 'Galera' and 'WSREP_LOCAL_STATE' not in status:
                    return constants.OUTPUT_NOT_IN_GALERA_MODE, constants.RETURN_CODE_NOK

                if (not self.__checker_only_check_status and
                    (config['WSREP_DESYNC'] == 'ON' or config['WSREP_REJECT_QUERIES'] != 'NONE'
                     or ('WSREP_ON' in config and config['WSREP_ON'] == 'OFF'))):
                    return constants.OUTPUT_NODE_IN_DESYNC_OR_REJECTS, self.__maintenance_response_code
                elif not self.__checker_only_check_status and config['WSREP_OSU_METHOD'] == 'RSU':
                    return constants.OUTPUT_RSU_METHOD, self.__maintenance_response_code
                elif (int(status['WSREP_LOCAL_STATE']) == 4 and status['WSREP_READY'] == 'ON' and
                        status['WSREP_CLUSTER_STATUS'] == 'Primary'):
                    return constants.OUTPUT_OK, constants.RETURN_CODE_OK
                elif (int(status['WSREP_LOCAL_STATE']) == 2 and status['WSREP_READY'] == 'ON' and
                        status['WSREP_CLUSTER_STATUS'] == 'Primary'):
                    if not self.__checker_only_check_status and self.__checker_donor_ok == 2:
                        if config['WSREP_SST_DONOR_REJECTS_QUERIES'] == 'ON':
                            return constants.OUTPUT_DONOR_REJECTS_QUERIES, self.__maintenance_response_code
                        elif config['WSREP_SST_METHOD'] in self.__donor_blocking_sst_methods:
                            return constants.OUTPUT_DONOR_BLOCKING_SST, \
                                   self.__maintenance_response_code
                        else:
                            return constants.OUTPUT_OK, constants.RETURN_CODE_OK
                    elif self.__checker_donor_ok:
                        return constants.OUTPUT_OK, constants.RETURN_CODE_OK
                    else:
                        return constants.OUTPUT_DONOR_STATE, self.__maintenance_response_code
                else:
                    return constants.OUTPUT_NOK, constants.RETURN_CODE_NOK

        except pymysql.OperationalError as e:
            if e.args[0] == pymysql.constants.ER.ACCESS_DENIED_ERROR:
                raise
            else:
                traceback.print_exc()
                return constants.OUTPUT_NOK, constants.RETURN_CODE_NOK
        except pymysql.MySQLError:
            traceback.print_exc()
            return constants.OUTPUT_NOK, constants.RETURN_CODE_NOK
        finally:
            if conn is not None and conn.open:
                conn.close()

    def maintenance_on(self):
        self.__maintenance_mode = True
        return constants.OUTPUT_SET_MAINT_MODE_ON, constants.RETURN_CODE_OK

    def maintenance_off(self):
        self.__maintenance_mode = False
        return constants.OUTPUT_SET_MAINT_MODE_OFF, constants.RETURN_CODE_OK

    def run(self, debug=False):
        self.flask_app.run(self.__checker_address, self.__checker_port, debug=debug)

    @staticmethod
    def shutdown_dev():
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug (standalone) Server')
        func()
        return 'Shutting down...', 200
