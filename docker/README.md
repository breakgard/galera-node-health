# Short description:

Health check for a Galera cluster node (MySQL, MariaDB, Percona XtraDB).

# Long description:

This image provides a health check for Galera cluster nodes.
It works by spinning up a gevent server, connecting to the instance and 
checking its current status and variables.
Health check gevent server is behind a lighttpd proxy.
The health check status of the node can be acquired by `GET /health` to the health check port.
It can be set as a http health check in HAProxy.

# Features:

- Supports MySQL, Percona XtraDB and MariaDB
- Connects via tcp/ip or socket
- Support for password or socket authorization
- Standalone and non-Primary detection
- Automatic maintenance mode for the instance based on config variables:
  `'WSREP_REJECT_QUERIES', 'WSREP_SST_DONOR_REJECTS_QUERIES', 'WSREP_ON', 'WSREP_DESYNC', 'WSREP_OSU_METHOD', 'WSREP_SST_METHOD'`
- Donor state detection with maintenance mode if necessary
- Manual maintenance mode via `GET /maint_on` and `GET /maint_off`

# Basic usage:
It is assumed that the Galera node is running on the host.

To start docker using socket auth (recommended - no need to save password in the config):
1. Create OS user for login. <br />`useradd galera-node-health -s /bin/false`  
2. Activate socket authentication plugin in database.
   1. For MariaDB: <br />`MariaDB [(none)]> INSTALL SONAME "auth_socket.so";`
   2. For MySQL and Percona: <br />`mysql> INSTALL PLUGIN auth_socket SONAME "auth_socket.so";`
3. Create user in database.
   1. For MariaDB: <br />`CREATE USER 'galera-node-health'@'localhost' IDENTIFIED VIA 'unix_socket';`
   2. For MySQL and Percona: <br />`CREATE USER 'galera-node-health'@'localhost' IDENTIFIED WITH 'auth_socket';`
4. Run a detached docker image with mounted db socket to `/health_check/sockets/db.sock`,<br />
   uid of created user and exposed proxy port<br />
`docker run -d -v <path_to_db_socket>:/health_check/sockets/db.sock -p <port_on_host>:8888 -u $(id -u galera-node-health) galera-node-health`

If the Galera node runs inside a docker container, 
you will need to share the database socket to the health check,
create the galera-node-health user inside the database container and
run galera-node-health image using the uid of the user created inside the container.
Or just use password authentication via tcp connection.

Best to have a way of limiting the docker logs size for the container.
This is to make sure you don't run out of space, as the health check will log access requests.

# Customization:

You can use a custom health check config by mounting it inside:
`-v <path_to_conf>:/health_check/conf/galera-node-health.cfg`

You can get an example config with descriptions of all options by running:
`docker run galera-node-health galera-node-health --print-example-config`

If you'd like, you can also use a custom lighttpd config for the proxy with:
`-v <path_to_proxy_conf>:/health_check/proxy_conf/lighttpd.conf`

# Environment variables

The docker container accepts the following environment variables (except `DISABLE_PROXY`, those work only with default proxy config):
* `-e DISABLE_PROXY=yes` - Proxy will not start.
   Useful if you already have a http server that could be setup for proxying requests.
   If you use this option, expose the checker port instead of proxy (default: `8080`)
   and change health check bind address (default: `127.0.0.1`) with a custom config.
*  `-e PROXY_PORT=8888` - Proxy will bind on port set here. Default proxy port is `8888`.
   Useful if running the container with --net=host option
*  `-e PROXY_ADDRESS=0.0.0.0` - IP address the proxy will bind to. Default address is `0.0.0.0`.
*  `-e PROXY_ENABLE_LOGS=yes` - This will enable proxy logs.
   Useful for debugging, but the logs could grow in size over time and the container has no mechanism to clean them.
   The logs are stored in container path `/health_check/logs`.
   If you wish to mount it from the host, make sure the galera-node-health user can write to it.
*  `-e PROXY_DISABLE_MAINT=yes` - This disables the maintenance links in the proxy.
   If not disabled in health check config, the links still work when accessed directly on the health check port.
 
# Create your own image!

Example Dockerfile:
```
FROM galera-node-health:<version>
COPY <your_health_check_config> /health_check/conf/galera-node-health.cfg
COPY <your_lighttpd_proxy_config> /health_check/proxy_conf/lighttpd.conf
EXPOSE <proxy_port>
```


# Supported MySQL versions:

- MySQL: 5.7
- Percona XtraDB: 5.7
- MariaDB: 10.2

# Links:

GitHub: `https://github.com/breakgard/galera-node-health/`

## Changelog:

# [0.1.0]
- Initial release
- Supported versions 
  - MySQL: 5.7
  - Percona XtraDB: 5.7
  - MariaDB: 10.2

