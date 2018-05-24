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
