FROM centos:7

#VERSION galera-node-health_image_tests:b01

COPY etc/yum.repos.d/* /etc/yum.repos.d/
COPY etc/pki/rpm-gpg/* /etc/pki/rpm-gpg/

RUN yum -y install --enablerepo='mariadb-10.2' docker-ce MariaDB-server python36 git && yum clean all && \
    python36 -m ensurepip --default-pip && pip3 --no-cache-dir install --upgrade pip && \
    pip3 --no-cache-dir install pytest requests

RUN mkdir -p /tmp/tests_shared/socks && chmod 777 /tmp/tests_shared/socks
RUN useradd galera-node-health
VOLUME ["/tmp/tests_shared"]
COPY init.sh /init.sh
CMD ["/init.sh"]