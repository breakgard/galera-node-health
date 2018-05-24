FROM centos:7

#VERSION galera-node-health_tests_main:b05

COPY etc/pki/rpm-gpg/* /etc/pki/rpm-gpg/
COPY etc/yum.repos.d/* /etc/yum.repos.d/
COPY bin/wsrep_sst_donor_test /bin/
RUN yum -y install python36 python36-devel git gcc && yum clean all && python36 -m ensurepip --default-pip \
    && pip3 --no-cache-dir install --upgrade pip

COPY requirements.txt /requirements.txt
RUN pip3 --no-cache-dir install -r /requirements.txt
COPY init.sh /init.sh
#ENTRYPOINT ["/bin/bash"]
CMD ["/init.sh"]
