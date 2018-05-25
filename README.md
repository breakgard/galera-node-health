# galera-node-health

**Health check for a Galera cluster node (MySQL, MariaDB, Percona XtraDB)**

This project provides a health check for Galera cluster nodes.
It works by spinning up a gevent server, connecting to the instance and 
checking its current status and variables.<br />
The health check status of the node can be acquired by `GET /health` to the health check port.<br />
It can be set as a http health check in HAProxy.

### Features:

- Supports MySQL, Percona XtraDB and MariaDB
- Connects via tcp/ip or socket
- Support for password or socket authorization
- Standalone and non-Primary detection
- Automatic maintenance mode for the instance based on config variables:
  `'WSREP_REJECT_QUERIES', 'WSREP_SST_DONOR_REJECTS_QUERIES', 'WSREP_ON', 'WSREP_DESYNC', 'WSREP_OSU_METHOD', 'WSREP_SST_METHOD'`
- Donor state detection with maintenance mode if necessary
- Manual maintenance mode via `GET /maint_on` and `GET /maint_off`

## Basic usage:

You can start the health check using `galera-health-node`. It will run using default configuration. <br />
To launch the check with a custom config you can use `galera-health-node -f <path_to_your_config>`. <br />
You can use `galera-health-node --print-example-config` to see an example config.<br />
Use `galera-health-node --help` to see all startup options.

### Recommended basic config:

To start the check using socket auth, which does not require saving passwords in the config:

1. Create OS user on the Galera node. Example `useradd galera-node-health -s /bin/false`
2. Activate socket authentication plugin in database by connecting to the database and running:
   1. For MariaDB `MariaDB [(none)]> INSTALL SONAME "auth_socket.so";`
   2. For MySQL and Percona: `mysql> INSTALL PLUGIN auth_socket SONAME "auth_socket.so";`
3. Create health check user in the database:
   1. For MariaDB: `CREATE USER 'galera-node-health'@'localhost' IDENTIFIED VIA 'unix_socket';`
   2. For MySQL and Percona: `CREATE USER 'galera-node-health'@'localhost' IDENTIFIED WITH 'auth_socket';`
4. Set the options below in the config file (create new file if needed).
5. Launch the health check: `galera-node-health -f <path_to_config_file>`

```
[db]
auth_method=socket
socket=<path_to_db_socket>
user=galera-node-health
```

### HAproxy config example

The health check will work with the following HAproxy backend check configuration.
```
backend galera-example
    balance     roundrobin
    mode tcp
    option httpchk GET /health HTTP/1.0
    http-check disable-on-404
    http-check expect status 200
    default-server inter 3s fall 3 rise 2
    server galera1 <IP>:<PORT> check port <health_check_port>
    server galera2 <IP>:<PORT> check port <health_check_port>
    server galera3 <IP>:<PORT> check port <health_check_port>
```

### Docker image:

See https://hub.docker.com/r/breakgard/galera-node-health/

## Supported MySQL versions:

- MySQL: 5.7
- Percona XtraDB: 5.7
- MariaDB: 10.2

## Changelog:

### [0.1.0]
- Initial release
- Supported versions 
  - MySQL: 5.7
  - Percona XtraDB: 5.7
  - MariaDB: 10.2
