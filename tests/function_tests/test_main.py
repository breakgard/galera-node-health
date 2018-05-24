from galera_node_health import GaleraNodeHealth
from galera_node_health import scripts
import threading
from time import sleep
import requests
import pymysql
from configparser import ConfigParser
import os
import subprocess
import tempfile
import pytest
import py
import re
import traceback
import psutil
from enum import Enum

# ----globals---- #
mysql_process = None  # Used for easier control (starting up, shutting down) of mysql instance used for tests


sql_reset_config = """set global wsrep_reject_queries = 'OFF';
                              set global wsrep_sst_donor_reject_queries = 'OFF';
                              set global wsrep_on = 'ON';
                              set global wsrep_desync = 1;
                              set global wsrep_osu_method = 'TOI';
                              set global wsrep_sst_method = 'xtrabackup-v2';"""
sql_check_state_pre57 = """select variable_value
                           from information_schema.global_status
                          where variable_name = 'wsrep_local_state';"""
sql_check_state = """select variable_value
                           from performance_schema.global_status
                          where variable_name = 'wsrep_local_state';"""
sql_check=None     # this will be selected based on the running version of mysql
# ----end of globals---- #


class MysqlVersions(Enum):
    MARIA_DB = 1
    PERCONA_CLUSTER_5_7 = 2
    PERCONA_CLUSTER = 3
    MYSQL_CLUSTER_5_7 = 4
    MYSQL_CLUSTER = 5
    MYSQL_CLUSTER_8_0 = 6


def connect_to_db():
    return pymysql.Connect(unix_socket=db_socket, user=db_user, cursorclass=pymysql.cursors.DictCursor)


def get_health():
    return requests.get('http://localhost:'+str(app_port)+'/health', timeout=2)


def get_mysql_version():
    print("Getting version of installed mysql")
    version = subprocess.run(['mysqld', '--version'], stdout=subprocess.PIPE)
    if version.returncode != 0:
        raise Exception("Cannot check version of installed mysql")
    version_string = str(version.stdout)
    print('Version string: ' + version_string)
    if re.search('MariaDB', version_string):
        v = MysqlVersions.MARIA_DB
    elif re.search('Percona XtraDB', version_string):
        if re.search('5.7.', version_string):
            v = MysqlVersions.PERCONA_CLUSTER_5_7
        else:
            v = MysqlVersions.PERCONA_CLUSTER
    elif re.search('MySQL', version_string):
        if re.search('8.0.', version_string):
            v = MysqlVersions.MYSQL_CLUSTER_8_0
        elif re.search('5.7.', version_string):
            v = MysqlVersions.MYSQL_CLUSTER_5_7
        else:
            v = MysqlVersions.MYSQL_CLUSTER
    else:
        raise NotImplementedError('Tests do not support ' + version_string)
    print("Found version: " + str(v))
    return v


def mysql_install_db(version):
    print("Installing DB datafiles for " + str(version))
    if version == MysqlVersions.MARIA_DB:
        return subprocess.run(["mysql_install_db", "--defaults-file=mysql_configs/mysql_test.cnf",
                              "--datadir="+db_datadir])
    elif version == MysqlVersions.PERCONA_CLUSTER_5_7:
            return subprocess.run(["mysql_install_db", "--defaults-file=mysql_configs/mysql_test.cnf",
                                   "--datadir="+db_datadir, '--insecure'])
    elif version == MysqlVersions.PERCONA_CLUSTER:
            return subprocess.run(["mysql_install_db", "--defaults-file=mysql_configs/mysql_test.cnf",
                                   "--datadir="+db_datadir])
    elif version == MysqlVersions.MYSQL_CLUSTER_8_0:
        return subprocess.run(["mysql_install_db", "--defaults-file=mysql_configs/mysql_test.cnf",
                               "--datadir="+db_datadir, '--insecure'])
    elif version == MysqlVersions.MYSQL_CLUSTER_5_7:
        return subprocess.run(["mysql_install_db", "--defaults-file=mysql_configs/mysql_test.cnf",
                               "--datadir="+db_datadir, '--insecure'])
    elif version == MysqlVersions.MYSQL_CLUSTER:
        return subprocess.run(["mysql_install_db", "--defaults-file=mysql_configs/mysql_test.cnf",
                               "--datadir="+db_datadir])
    else:
        raise NotImplementedError('mysql_install_db does not support ' + str(version))


def change_sql_for_version(version):
    #global sql_check_db
    global sql_check
    if version == MysqlVersions.PERCONA_CLUSTER or version == MysqlVersions.MARIA_DB or version == MysqlVersions.MYSQL_CLUSTER:
        #sql_check_db = sql_check_db_pre57
        print(str(version) + " is using old status tables")
        sql_check = sql_check_state_pre57
    else:
        print(str(version) + " is using new status tables")
        sql_check = sql_check_state


@pytest.fixture(scope="session", autouse=True)
def create_db():
    global db_datadir
    global db_socket
    global db_pidfile
    global db_user
    global db_logfile

    py_datadir = py.path.local(tempfile.mkdtemp())
    db_datadir = str(py_datadir)
    db_socket = str(db_datadir) + '/mysql.sock'
    db_pidfile = str(db_datadir) + '/mysql.pid'
    db_logfile = str(db_datadir) + '/mysql_log.err'
    db_user = "root"
    print("----------------Installing test DB-----------------")
    version = get_mysql_version()
    result = mysql_install_db(version)
    if result.returncode != 0:
        raise Exception("Cannot install database with: " + str(result.args))
    change_sql_for_version(version)
    start_db()
    with connect_to_db() as cur:
        if version == MysqlVersions.MARIA_DB:
            cur.execute("""INSTALL SONAME "auth_socket.so";""")
            cur.execute("""CREATE USER IF NOT EXISTS "{checker_test_user}_password"@"localhost" 
                            IDENTIFIED BY 
                            "{checker_test_user}_password";""".format(checker_test_user=os.environ["USER"]))
            cur.execute("""CREATE USER IF NOT EXISTS "{checker_test_user}"@"localhost" 
                            IDENTIFIED via "unix_socket";""".format(checker_test_user=os.environ["USER"]))
        else:
            cur.execute("""INSTALL PLUGIN auth_socket SONAME "auth_socket.so";""")
            cur.execute("""CREATE USER IF NOT EXISTS "{checker_test_user}_password"@"localhost" 
                            IDENTIFIED BY 
                            "{checker_test_user}_password";""".format(checker_test_user=os.environ["USER"]))
            cur.execute("""CREATE USER IF NOT EXISTS "{checker_test_user}"@"localhost" 
                            IDENTIFIED with "auth_socket";""".format(checker_test_user=os.environ["USER"]))
        #else:
        #    raise NotImplementedError('Tests do not support this version of mysql!')

    shutdown_db()
    print("----------------Test DB installed-----------------")
    yield "create_db"
    print("----------------Removing test DB------------------")
    shutdown_db()
    py_datadir.remove()
    print("----------------Test DB removed-------------------")


def shutdown_db():
    global mysql_process
    print("Shutting down test DB - checking if DB is alive")
    if mysql_process is not None and mysql_process.poll() is None:
        print("Test DB is alive")
        print("Killing DB children processes if any")
        for child in psutil.Process(mysql_process.pid).children(recursive=True):
            child.kill()
        print("Killing main db process")
        mysql_process.kill()
        mysql_process.wait()
        print("Test DB is now down")
        print("Printing db errlog")
        try:
            with open(db_logfile, 'r') as f:
                print(f.read())
            py.path.local(db_logfile).remove()
        except Exception:
            pass
        try:
            py.path.local(db_datadir + '/grastate.dat').remove()
        except Exception:
            pass
        try:
            py.path.local(db_datadir + '/galera.cache').remove()
        except Exception:
            pass
        try:
            py.path.local(db_datadir + '/multi-master.info').remove()
        except Exception:
            pass
    else:
        print("Test db already down - not doing anything")


#def shutdown_db():
#    print("Shutting down test DB - checking if DB is alive")
#    result = subprocess.run(["mysqladmin", "--user=root", "--socket="+db_socket, "ping"])
#    if result.returncode == 0:
#        print("Test DB alive - checking if donor")
#        with connect_to_db() as cur:
#            cur.execute(sql_check_state)
#            state = cur.fetchall()
#            if len(state) > 0 and int(state[0]['variable_value']) == 2:
#                donor_mode = True
#            else:
#                donor_mode = False
#        if donor_mode:
#            print("Donor mode active on test DB - killing for speed!")
#            with open(db_pidfile, 'r') as pid:
#                os.kill(int(pid.readline()), 9)
#        else:
#            print("Test db not in donor mode - shutting down normally")
#            result = subprocess.run(["mysqladmin", "--user=root", "--socket="+db_socket, "shutdown"])
#            if result.returncode != 0:
#                raise Exception("Error shutting down db on socket: " + db_socket)
#        print("Test DB is now down")
#    else:
#        print("Test db already down - not doing anything")
#    return


def start_db(with_galera=True):
    global mysql_process
    shutdown_db()
    mysql_startup_args = ["mysqld", "--defaults-file=mysql_configs/mysql_test.cnf", "--datadir="+db_datadir,
                          "--socket="+db_socket, "--pid-file="+db_pidfile, '--user='+os.environ['USER'],
                          "--log-error="+db_logfile]
    if with_galera:
        mysql_startup_args.append("--wsrep_new_cluster")
        mysql_startup_args.append("--wsrep_on=ON")
    else:
        mysql_startup_args.append("--wsrep_on=OFF")
        mysql_startup_args.append("--wsrep_provider=")

    print("Starting test DB")
    mysql_process = subprocess.Popen(mysql_startup_args)
    i = 0
    db_started = False
    while i < 30:
        try:
            print("Checking if DB in synced state")
            with connect_to_db() as cur:
                db_started = True
                if with_galera:
                    cur.execute(sql_check)
                    state = cur.fetchone()['variable_value']
                    if int(state) == 4:
                        print("DB in synced state: " + str(state))
                        break
                    else:
                        print("DB not in synced state: " + str(state))
                else:
                    break
        except pymysql.MySQLError:
            traceback.print_exc()
        i += 1
        sleep(1)
    if i >= 30:
        try:
            with open(db_logfile, "r") as f:
                print(f.read())
            py.path.local(db_logfile).remove()
        except Exception:
            pass
        if db_started and with_galera:
            raise Exception("DB started but is not in synced state after startup with args: " + str(mysql_startup_args))
        else:
            raise Exception("Cannot connect to db after startup with args: " + str(mysql_startup_args))
    print("Test DB is now up")


def put_db_in_donor_mode():
    # this commands puts db in donor state
    print("Starting garb to put db in donor mode using wsrep_sst_donor_test script")
    db_garb = subprocess.Popen(["garbd", "-o", "gmcast.listen_addr=tcp://127.0.0.1:33330", "-g", "my_wsrep_cluster",
                                "-a", "gcomm://127.0.0.1:45670", "--sst", "donor_test", "--donor", "db01"])
    # wait until db is in donor state
    i = 0
    while i < 20:
        try:
            print("Checking if DB in donor state")
            with connect_to_db() as cur:
                cur.execute(sql_check)
                if int(cur.fetchone()['variable_value']) == 2:
                    print('OK')
                    break
        except pymysql.MySQLError:
            traceback.print_exc()
        sleep(1)
        i += 1
    print("Killing garb as it is no longer needed")
    db_garb.kill()
    db_garb.wait()
    try:
        py.path.local('gvwstate.dat').remove()
    except Exception:
        pass
    if i >= 20:
        raise Exception("Database is still not in donor mode after " + str(i) + " seconds after launching garb")
    print("Database in donor state")


def setup_module():
    global app_port
    print("Getting basic test config")
    config_reader = ConfigParser(inline_comment_prefixes="#")
    config_reader.read('test_config.cfg')
    app_port = config_reader.get("tests", "app_port")
    # check if wsrep_sst_donor_test script is available in /bin - this is required for donor tests
    if not os.path.isfile('/bin/wsrep_sst_donor_test'):
        raise Exception('/bin/wsrep_sst_donor_test does not exist')
    print("Basic test config OK")
    # check if local db is active and runs galera


def teardown_module():
    pass


def basic_checker_config_for_auth():
    config_writer = ConfigParser()
    config_writer.add_section("checker")
    config_writer.add_section("db")
    config_writer.set("checker", "address", '127.0.0.1')
    config_writer.set("checker", "port", app_port)
    return config_writer


def basic_checker_config():
    config_writer = ConfigParser()
    config_writer.add_section("checker")
    config_writer.add_section("db")
    config_writer.set("checker", "address", '127.0.0.1')
    config_writer.set("checker", "port", app_port)
    config_writer.set("db", "auth", "socket")
    config_writer.set("db", "user", os.environ["USER"])
    config_writer.set("db", "socket", db_socket)
    return config_writer


def prepare_config_file(config_writer):
    temp_file = tempfile.mkstemp(text=True)
    with open(temp_file[1], "w") as cfg:
        config_writer.write(cfg)
    return py.path.local(temp_file[1])


def start_checker(cfg_file_path):
    global app_thread
    global galera_health_checker
    print("Starting checker")
    try:
        galera_health_checker = GaleraNodeHealth(str(cfg_file_path), test_mode=True)
    except Exception:
        raise
    finally:
        cfg_file_path.remove()
    app_thread = threading.Thread(target=galera_health_checker.run)
    app_thread.start()
    sleep(1)
    i = 0
    while i < 5:
        try:
            get_health()
            break
        except Exception:
            pass
        i += 1
    if i >= 5:
        raise Exception("Too long waiting for checker to start")
    print("Checker is now up")


def shutdown_checker():
    global app_thread
    global galera_health_checker
    global app_port
    print("Shutting down checker")
    requests.get("http://localhost:" + str(app_port) + "/shutdown", timeout=2)
    app_thread.join()
    del galera_health_checker
    print("Checker is now down")


def start_maint():
    print("Entering maintenance mode")
    resp = requests.get("http://localhost:" + str(app_port) + "/maint_on", timeout=2)
    if resp.status_code != 200:
        raise Exception("Request to enter maintenance mode failed!")
    print("Checker is now in maintenance mode")


def stop_maint():
    print("Leaving maintenance mode")
    resp = requests.get("http://localhost:" + str(app_port) + "/maint_off", timeout=2)
    if resp.status_code != 200:
        raise Exception("Request to leave maintenance mode failed!")
    print("Checker is now in regular mode")


#fixtures

@pytest.fixture(scope="function", autouse=True)
def handle_db():
    start_db()
    yield "handle_db"
    shutdown_db()


@pytest.fixture(scope="function")
def start_checker_default():
    start_checker(prepare_config_file(basic_checker_config()))
    yield "start_checker_default"
    shutdown_checker()


@pytest.fixture(scope="function")
def start_checker_auth_password_socket():
    config = basic_checker_config_for_auth()
    config.set("db", "auth", "password")
    config.set("db", "user", os.environ["USER"] + "_password")
    config.set("db", "password", os.environ["USER"] + "_password")
    config.set("db", "connect_method", "socket")
    config.set("db", "socket", db_socket)
    start_checker(prepare_config_file(config))
    yield "start_checker_auth_password_socket"
    shutdown_checker()


@pytest.fixture(scope="function")
def start_checker_auth_password_tcp():
    config = basic_checker_config_for_auth()
    config.set("db", "auth", "password")
    config.set("db", "connect_method", "tcp")
    config.set("db", "user", os.environ["USER"] + "_password")
    config.set("db", "password", os.environ["USER"] + "_password")
    config.set("db", "address", "127.0.0.1")
    config.set("db", "port", "33060")
    start_checker(prepare_config_file(config))
    yield "start_checker_auth_password_socket"
    shutdown_checker()


@pytest.fixture(scope="function")
def start_checker_default_donor_up():
    config = basic_checker_config()
    config.set("checker", "donor_ok", "1")
    start_checker(prepare_config_file(config))
    yield "start_checker_default_donor_up"
    shutdown_checker()


@pytest.fixture(scope="function")
def start_checker_default_donor_down():
    config = basic_checker_config()
    config.set("checker", "donor_ok", "0")
    start_checker(prepare_config_file(config))
    yield "start_checker_default_donor_down"
    shutdown_checker()


@pytest.fixture(scope="function")
def start_checker_no_maintenance():
    config = basic_checker_config()
    config.set("checker", "enable_maint_mode", "0")
    start_checker(prepare_config_file(config))
    yield "start_checker_no_maintenance"
    shutdown_checker()


@pytest.fixture(scope="function")
def start_checker_only_check_status():
    config = basic_checker_config()
    config.set("checker", "only_check_status", "1")
    start_checker(prepare_config_file(config))
    yield "start_checker_only_check_status"
    shutdown_checker()


@pytest.fixture(scope="function")
def start_checker_only_check_status_donor_nok():
    config = basic_checker_config()
    config.set("checker", "only_check_status", "1")
    config.set("checker", "donor_ok", "0")
    start_checker(prepare_config_file(config))
    yield "start_checker_only_check_status_donor_nok"
    shutdown_checker()


@pytest.fixture(scope="function")
def start_checker_return_500_instead_of_404():
    config = basic_checker_config()
    config.set("checker", "return_500_instead_of_404", "1")
    start_checker(prepare_config_file(config))
    yield "start_checker_return_500_instead_of_404"
    shutdown_checker()


@pytest.fixture(scope="function")
def start_checker_return_500_instead_of_404_donor_nok():
    config = basic_checker_config()
    config.set("checker", "return_500_instead_of_404", "1")
    config.set("checker", "donor_ok", "0")
    start_checker(prepare_config_file(config))
    yield "start_checker_return_500_instead_of_404_donor_nok"
    shutdown_checker()


@pytest.fixture(scope="function")
def start_checker_return_500_instead_of_404_donor_nok_only_check_status():
    config = basic_checker_config()
    config.set("checker", "return_500_instead_of_404", "1")
    config.set("checker", "only_check_status", "1")
    config.set("checker", "donor_ok", "0")
    start_checker(prepare_config_file(config))
    yield "start_checker_return_500_instead_of_404_donor_nok_only_check_status"
    shutdown_checker()


#default tests


def test_happy_path(start_checker_default):
    resp = get_health()
    assert resp.text == "OK", resp.status_code == 200


def test_auth_password_socket(start_checker_auth_password_socket):
    resp = get_health()
    assert resp.text == "OK", resp.status_code == 200


def test_auth_password_tcp(start_checker_auth_password_tcp):
    resp = get_health()
    assert resp.text == "OK", resp.status_code == 200


def test_node_down(start_checker_default):
    shutdown_db()
    resp = get_health()
    assert resp.text == "NOK", resp.status_code == 500


def test_node_not_in_galera_mode(start_checker_default):
    shutdown_db()
    start_db(with_galera=False)
    resp = get_health()
    assert resp.text == "Node not started in Galera mode!", resp.status_code == 500


def test_node_down_then_up(start_checker_default):
    shutdown_db()
    sleep(5)
    start_db()
    resp = get_health()
    assert resp.text == "OK", resp.status_code == 200


def test_node_maintenance_on(start_checker_default):
    start_maint()
    sleep(1)
    resp = get_health()
    assert resp.text == "Manual maintenance mode: ON", resp.status_code == 404


def test_node_maintenance_off(start_checker_default):
    start_maint()
    sleep(1)
    stop_maint()
    sleep(1)
    resp = get_health()
    assert resp.text == "OK", resp.status_code == 200


def test_no_maintenance(start_checker_no_maintenance):
    try:
        start_maint()
    except Exception:
        pass
    resp = get_health()
    assert resp.text == "OK", resp.status_code == 200


# donor tests


def test_donor_auto(start_checker_default):
    put_db_in_donor_mode()
    resp = get_health()
    # because of sst_method set to xtrabackup-v2, donor should be safe for queries
    assert resp.text == "OK", resp.status_code == 200


def test_donor_always_up(start_checker_default_donor_up):
    put_db_in_donor_mode()
    with connect_to_db() as cur:
        cur.execute("set global wsrep_sst_method='rsync';")    # just in case
    resp = get_health()
    assert resp.text == "OK", resp.status_code == 200


def test_donor_always_down(start_checker_default_donor_down):
    put_db_in_donor_mode()
    resp = get_health()
    assert resp.text == "Donor state", resp.status_code == 404


#config tests


def test_node_rejects_queries(start_checker_default):
    try:
        with connect_to_db() as cur:
            cur.execute("set global wsrep_reject_queries='ALL';")
    except pymysql.MySQLError:
        pass
    resp = get_health()
    assert resp.text == 'Node is in desync and/or rejects queries', resp.status_code == 404


def test_node_rejects_queries_kill(start_checker_default):
    try:
        with connect_to_db() as cur:
            cur.execute("set global wsrep_reject_queries='ALL_KILL';")
    except pymysql.MySQLError:
        pass
    resp = get_health()
    assert resp.text == 'Node is in desync and/or rejects queries', resp.status_code == 404


def test_node_is_in_desync(start_checker_default):
    with connect_to_db() as cur:
        cur.execute("set global wsrep_desync=1;")
    resp = get_health()
    assert resp.text == 'Node is in desync and/or rejects queries', resp.status_code == 404


def test_node_has_wsrep_off(start_checker_default):
    try:
        with connect_to_db() as cur:
            cur.execute("set global wsrep_on='OFF';")
    except pymysql.MySQLError:
        try:
            with connect_to_db() as cur:
                cur.execute("set wsrep_on='OFF';")
            print('DB does not support global wsrep_on')
            return
        except pymysql.MySQLError:
            raise
    resp = get_health()
    assert resp.text == 'Node is in desync and/or rejects queries', resp.status_code == 404


def test_donor_rejects_queries(start_checker_default):
    put_db_in_donor_mode()
    with connect_to_db() as cur:
        cur.execute("set global wsrep_sst_donor_rejects_queries='ON';")
    resp = get_health()
    assert resp.text == 'Donor rejects queries', resp.status_code == 404


def test_node_has_rsu_set(start_checker_default):
    with connect_to_db() as cur:
        cur.execute("set global wsrep_osu_method='RSU';")
    resp = get_health()
    assert resp.text == 'Node is in RSU mode', resp.status_code == 404


def test_cluster_uses_rsync_sst(start_checker_default):
    with connect_to_db() as cur:
        cur.execute("set global wsrep_sst_method='rsync';")
    resp = get_health()
    assert resp.text == 'OK', resp.status_code == 200
    put_db_in_donor_mode()
    sleep(1)
    resp = get_health()
    assert resp.text == 'Cluster is using blocking sst method and node is in donor state', resp.status_code == 404


def test_cluster_uses_mysqldump_sst(start_checker_default):
    with connect_to_db() as cur:
        cur.execute("set global wsrep_sst_method='mysqldump';")
    resp = get_health()
    assert resp.text == 'OK', resp.status_code == 200
    put_db_in_donor_mode()
    sleep(1)
    resp = get_health()
    assert resp.text == 'Cluster is using blocking sst method and node is in donor state', resp.status_code == 404


# only_check_status = 1


def test_node_rejects_queries_only_status(start_checker_only_check_status):
    try:
        with connect_to_db() as cur:
            cur.execute("set global wsrep_reject_queries='ALL';")
    except pymysql.MySQLError:
        pass
    resp = get_health()
    assert resp.text == 'OK', resp.status_code == 200


def test_node_is_in_desync_only_status(start_checker_only_check_status):
    with connect_to_db() as cur:
        cur.execute("set global wsrep_desync=1;")
    resp = get_health()
    assert resp.text == 'OK', resp.status_code == 200


def test_node_has_wsrep_off_only_status(start_checker_only_check_status):
    try:
        with connect_to_db() as cur:
            cur.execute("set global wsrep_on='OFF';")
    except pymysql.MySQLError:
        try:
            with connect_to_db() as cur:
                cur.execute("set wsrep_on='OFF';")
            print('DB does not support global wsrep_on')
            return
        except pymysql.MySQLError:
            raise
    resp = get_health()
    assert resp.text == 'OK', resp.status_code == 200


def test_donor_rejects_queries_only_status(start_checker_only_check_status):
    put_db_in_donor_mode()
    with connect_to_db() as cur:
        cur.execute("set global wsrep_sst_donor_rejects_queries='ON';")
    resp = get_health()
    assert resp.text == 'OK', resp.status_code == 200


def test_node_has_rsu_set_only_status(start_checker_only_check_status):
    with connect_to_db() as cur:
        cur.execute("set global wsrep_osu_method='RSU';")
    resp = get_health()
    assert resp.text == 'OK', resp.status_code == 200


def test_cluster_uses_rsync_sst_only_status(start_checker_only_check_status):
    with connect_to_db() as cur:
        cur.execute("set global wsrep_sst_method='rsync';")
    resp = get_health()
    assert resp.text == 'OK', resp.status_code == 200
    put_db_in_donor_mode()
    sleep(1)
    resp = get_health()
    assert resp.text == 'OK', resp.status_code == 200


def test_cluster_uses_mysqldump_sst_only_status(start_checker_only_check_status):
    with connect_to_db() as cur:
        cur.execute("set global wsrep_sst_method='mysqldump';")
    resp = get_health()
    assert resp.text == 'OK', resp.status_code == 200
    put_db_in_donor_mode()
    sleep(1)
    resp = get_health()
    assert resp.text == 'OK', resp.status_code == 200


# only_check_status = 1 and donor_ok = 0


def test_node_is_in_desync_donor_nok(start_checker_only_check_status_donor_nok):
    with connect_to_db() as cur:
        cur.execute("set global wsrep_desync=1;")
    resp = get_health()
    assert resp.text == 'Donor state', resp.status_code == 404


def test_donor_rejects_queries_donor_nok(start_checker_only_check_status_donor_nok):
    put_db_in_donor_mode()
    with connect_to_db() as cur:
        cur.execute("set global wsrep_sst_donor_rejects_queries='ON';")
    resp = get_health()
    assert resp.text == 'Donor state', resp.status_code == 404


# returns_500_instead_of_404 = 1


def test_node_has_rsu_set_500(start_checker_return_500_instead_of_404):
    with connect_to_db() as cur:
        cur.execute("set global wsrep_osu_method='RSU';")
    resp = get_health()
    assert resp.text == 'Node is in RSU mode', resp.status_code == 500


def test_cluster_uses_rsync_sst_500(start_checker_return_500_instead_of_404):
    with connect_to_db() as cur:
        cur.execute("set global wsrep_sst_method='rsync';")
    resp = get_health()
    assert resp.text == 'OK', resp.status_code == 200
    put_db_in_donor_mode()
    sleep(1)
    resp = get_health()
    assert resp.text == 'Cluster is using blocking sst method and node is in donor state', resp.status_code == 500


def test_cluster_uses_mysqldump_sst_500(start_checker_return_500_instead_of_404):
    with connect_to_db() as cur:
        cur.execute("set global wsrep_sst_method='mysqldump';")
    resp = get_health()
    assert resp.text == 'OK', resp.status_code == 200
    put_db_in_donor_mode()
    sleep(1)
    resp = get_health()
    assert resp.text == 'Cluster is using blocking sst method and node is in donor state', resp.status_code == 500


def test_node_rejects_queries_500(start_checker_return_500_instead_of_404):
    try:
        with connect_to_db() as cur:
            cur.execute("set global wsrep_reject_queries='ALL';")
    except pymysql.MySQLError:
        pass
    resp = get_health()
    assert resp.text == 'Node is in desync and/or rejects queries', resp.status_code == 500


def test_node_is_in_desync_500(start_checker_return_500_instead_of_404):
    with connect_to_db() as cur:
        cur.execute("set global wsrep_desync=1;")
    resp = get_health()
    assert resp.text == 'Node is in desync and/or rejects queries', resp.status_code == 500


def test_node_has_wsrep_off_500(start_checker_return_500_instead_of_404):
    try:
        with connect_to_db() as cur:
            cur.execute("set global wsrep_on='OFF';")
    except pymysql.MySQLError:
        try:
            with connect_to_db() as cur:
                cur.execute("set wsrep_on='OFF';")
            print('DB does not support global wsrep_on')
            return
        except pymysql.MySQLError:
            raise
    resp = get_health()
    assert resp.text == 'Node is in desync and/or rejects queries', resp.status_code == 500


def test_donor_rejects_queries_500(start_checker_return_500_instead_of_404):
    put_db_in_donor_mode()
    with connect_to_db() as cur:
        cur.execute("set global wsrep_sst_donor_rejects_queries='ON';")
    resp = get_health()
    assert resp.text == 'Donor rejects queries', resp.status_code == 500


# only_check_status = 1 and donor_ok = 0 and return_500_instead_of_404 = 1


def test_node_is_in_desync_donor_nok_500(start_checker_return_500_instead_of_404_donor_nok_only_check_status):
    with connect_to_db() as cur:
        cur.execute("set global wsrep_desync=1;")
    resp = get_health()
    assert resp.text == 'Donor state', resp.status_code == 500


def test_donor_rejects_queries_donor_nok_500(start_checker_return_500_instead_of_404_donor_nok_only_check_status):
    put_db_in_donor_mode()
    with connect_to_db() as cur:
        cur.execute("set global wsrep_sst_donor_rejects_queries='ON';")
    resp = get_health()
    assert resp.text == 'Donor state', resp.status_code == 500


# script tests


def test_main_script_example_config():
    assert scripts.main('--print-example-config') != ''


#def test_create_fcgi():
#    assert scripts.create_fcgi() != ''
