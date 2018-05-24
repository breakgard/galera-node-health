#!/bin/bash
set -e

if [ ! -d '/tmp/tests_shared/socks' ];
then
    mkdir /tmp/tests_shared/socks
fi
echo "Installing tmp mysql database"
if [ `id -u` -eq 0 ];
then
    USER_OPT='--user=root'
else
    USER_OPT=''
fi
mysql_install_db --defaults-file=mysql_docker_test.cnf ${USER_OPT} --datadir=/tmp/test_mysql
echo "Starting mysql"
mysqld --defaults-file=mysql_docker_test.cnf ${USER_OPT} --socket=/tmp/tests_shared/socks/mysql.sock \
        --log-error=/tmp/test_mysql/mysql.err --datadir=/tmp/test_mysql --wsrep_on=ON --wsrep_new_cluster &
sleep 5

cat /tmp/test_mysql/mysql.err

echo "Preparing mysql for tests"
echo "INSTALL SONAME 'auth_socket.so'" | mysql -uroot --socket=/tmp/tests_shared/socks/mysql.sock
echo "CREATE USER 'galera-node-health'@'localhost' IDENTIFIED VIA 'unix_socket'" | mysql -uroot --socket=/tmp/tests_shared/socks/mysql.sock
echo "MySQL prepared"