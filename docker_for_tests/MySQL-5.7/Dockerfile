FROM galera-node-health_tests_main:latest

#VERSION galera-node-health_tests_mysql_5_7:b01

RUN yum -y install --enablerepo='galera-mysql57' --enablerepo='galera' mysql-wsrep-5.7 galera-3 && yum clean all
RUN ln -s /usr/lib64/galera-3 /usr/lib64/galera
