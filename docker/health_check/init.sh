#!/bin/bash
set -e

CHECK_CONF_PATH='/health_check/conf/galera-node-health.cfg'
PROXY_CONF_PATH='/health_check/proxy_conf/lighttpd.conf'

function create_default_checker_config() {
    echo '[checker]' > "${CHECK_CONF_PATH}"
    echo 'address=127.0.0.1' >> "${CHECK_CONF_PATH}"
    echo 'port=8080' >> "${CHECK_CONF_PATH}"
    echo '[db]' >> "${CHECK_CONF_PATH}"
    echo 'auth_method=socket' >> "${CHECK_CONF_PATH}"
    echo 'socket=/health_check/sockets/db.sock' >> "${CHECK_CONF_PATH}"
    echo 'user=galera-node-health' >> "${CHECK_CONF_PATH}"
}

echo "Starting galera-node-health"
echo "See README for custom options"

if [ -f "$CHECK_CONF_PATH" ] && [ -s "$CHECK_CONF_PATH" ];
then
    echo "Config file found"
else
    echo "Config file not found at '${CHECK_CONF_PATH}'"
    echo "Creating default one"
    create_default_checker_config
    echo "-------"
    cat ${CHECK_CONF_PATH}
    echo "-------"
fi

if [ "$DISABLE_PROXY" != "yes" ];
then
    if [ -w "$PROXY_CONF_PATH" ];
    then
        echo "Parsing config file for checker port for proxy"
        #CHECKER_PORT=`crudini --get "$CHECK_CONF_PATH" checker port`
        CHECKER_PORT=`python3 "/health_check/get_checker_port.py" "${CHECK_CONF_PATH}"`
        sed -i "s/<CHECKER_PORT>/${CHECKER_PORT}/g" "${PROXY_CONF_PATH}"
        if [ -z "$PROXY_PORT" ];
        then
            PROXY_PORT=8888
        fi
        if [ -z "$PROXY_ADDRESS" ];
        then
            PROXY_ADDRESS=0.0.0.0
        fi
        echo "Proxy port: ${PROXY_PORT}"
        echo "Proxy bind address: ${PROXY_ADDRESS}"
        sed -i "s/<PROXY_PORT>/${PROXY_PORT}/g" "${PROXY_CONF_PATH}"
        sed -i "s/<PROXY_ADDRESS>/${PROXY_ADDRESS}/g" "${PROXY_CONF_PATH}"

        if [ "$PROXY_ENABLE_LOGS" == "yes" ];
        then
            echo "Enabling proxy logs"
            echo 'include "lighttpd_logs.conf"' >> "${PROXY_CONF_PATH}"
        fi

        if [ "$PROXY_DISABLE_MAINT" == "yes" ];
        then
            echo "Disabling maint links in proxy"
            sed -i "s/^.*\/maint_on.*//g" "${PROXY_CONF_PATH}"
            sed -i "s/^.*\/maint_off.*//g" "${PROXY_CONF_PATH}"
        fi
    else
        echo "It seems that '${PROXY_CONF_PATH}' is not writable"
        echo "Using it as is"
    fi
    echo "Starting proxy"
    lighttpd -f "${PROXY_CONF_PATH}"
fi
echo "Starting health check"
galera-node-health -f "${CHECK_CONF_PATH}" --docker-logs-fix
