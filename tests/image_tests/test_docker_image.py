import pytest
import requests
import subprocess
import time


def setup_module():
    with open('health_bind_any.cfg', 'r') as input_file:
        with open('/tmp/tests_shared/health_bind_any.cfg', 'w') as output_file:
            output_file.write(input_file.read())


def get_user_id():
    return subprocess.run(['id', '-u', 'galera-node-health'], stdout=subprocess.PIPE).stdout.decode('ascii').strip()


@pytest.fixture(params=[[]])
def prepare_container(request):
    optional_args = request.param
    launch_args = ['docker', 'run', '-d', '-v', '/tmp/tests_shared/socks/mysql.sock:/health_check/sockets/db.sock',
                   '-u', get_user_id()] + optional_args + ['galera-node-health:latest']
    print("Launching galera-node-health with args: " + str(launch_args))
    container = subprocess.run(launch_args, stdout=subprocess.PIPE).stdout.decode('ascii').strip()
    print("galera-node-health container id: " + container)
    time.sleep(1)
    try:
        print("Getting IP of galera-node-health container")
        result = subprocess.run(['docker', 'inspect', '-f',
                                 '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}', container],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        container_ip = result.stdout.decode('ascii').strip()
        print("Container IP: " + container_ip)
        if container_ip != '':
            if 'PROXY_ENABLE_LOGS=yes' in optional_args:
                yield container
            else:
                yield container_ip
        else:
            if result.stderr:
                err = result.stderr.decode('ascii')
            else:
                err = ''
            raise Exception("Something went wrong with getting IP or launching container: " + err)
    except Exception:
        raise
    finally:
        print("Killing galera-node-health container ID: " + container)
        subprocess.run(['docker', 'kill', container])
        print("Printing container logs")
        subprocess.run(['docker', 'logs', container])
        print("Removing galera-node-health container ID: " + container)
        subprocess.run(['docker', 'rm', container])


def test_happy_path(prepare_container):
    r = requests.get(url='http://'+prepare_container+':8888/health', timeout=2)
    assert r.status_code == 200


def test_wrong_endpoint(prepare_container):
    try:
        r = requests.get(url='http://'+prepare_container+':8888/healtha', timeout=2)
        status_code = r.status_code
    except Exception:
        status_code = 500
    assert status_code != 200


def test_wrong_endpoint2(prepare_container):
    try:
        r = requests.get(url='http://'+prepare_container+':8888/health/health', timeout=2)
        status_code = r.status_code
    except Exception:
        status_code = 500
    assert status_code != 200


@pytest.mark.parametrize('prepare_container',
                         [['-e', 'DISABLE_PROXY=yes', '-v',
                           '/tmp/tests_shared/health_bind_any.cfg:/health_check/conf/galera-node-health.cfg']],
                         indirect=True)
def test_disable_proxy(prepare_container):
    try:
        r = requests.get(url='http://'+prepare_container+':8888/health', timeout=2)
        status_code = r.status_code
    except Exception:
        status_code = 500
    assert status_code != 200
    r = requests.get(url='http://'+prepare_container+':8080/health', timeout=2)
    assert r.status_code == 200


@pytest.mark.parametrize('prepare_container', [['-e', 'PROXY_PORT=7777']], indirect=True)
def test_proxy_port(prepare_container):
    r = requests.get(url='http://'+prepare_container+':7777/health', timeout=2)
    assert r.status_code == 200


@pytest.mark.parametrize('prepare_container',
                         [['-e', 'PROXY_ADDRESS=127.0.0.1', '-v',
                           '/tmp/tests_shared/health_bind_any.cfg:/health_check/conf/galera-node-health.cfg']],
                         indirect=True)
def test_proxy_address(prepare_container):
    try:
        r = requests.get(url='http://'+prepare_container+':8888/health', timeout=2)
        status_code = r.status_code
    except Exception:
        status_code = 500
    assert status_code != 200
    r = requests.get(url='http://'+prepare_container+':8080/health', timeout=2)
    assert r.status_code == 200


def test_maint(prepare_container):
    r = requests.get(url='http://'+prepare_container+':8888/maint_on', timeout=2)
    assert r.status_code == 200
    r = requests.get(url='http://'+prepare_container+':8888/health', timeout=2)
    assert r.status_code == 404
    r = requests.get(url='http://'+prepare_container+':8888/maint_off', timeout=2)
    assert r.status_code == 200
    r = requests.get(url='http://'+prepare_container+':8888/health', timeout=2)
    assert r.status_code == 200


@pytest.mark.parametrize('prepare_container', [['-e', 'PROXY_DISABLE_MAINT=yes']], indirect=True)
def test_disable_maint(prepare_container):
    r = requests.get(url='http://'+prepare_container+':8888/maint_on', timeout=2)
    assert r.status_code != 200
    r = requests.get(url='http://'+prepare_container+':8888/maint_off', timeout=2)
    assert r.status_code != 200


@pytest.mark.parametrize('prepare_container', [['-e', 'PROXY_ENABLE_LOGS=yes']], indirect=True)
def test_enable_logs(prepare_container):
    r = subprocess.run(['docker', 'exec', prepare_container, 'ls', '/health_check/logs'], stdout=subprocess.PIPE)
    assert r.stdout.decode('ascii').strip() != ''

