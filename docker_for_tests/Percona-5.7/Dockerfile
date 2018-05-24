FROM galera-node-health_tests_main:latest

#VERSION galera-node-health_tests_percona_5_7:b01

RUN yum -y install --enablerepo='percona-release-x86_64' Percona-Server-shared-57 && \
    yum -y install --enablerepo='percona-release-x86_64' Percona-XtraDB-Cluster-full-57 && yum clean all
RUN ln -s /usr/lib64/galera3 /usr/lib64/galera
