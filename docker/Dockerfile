FROM alpine:3.7

LABEL maintainer="breakgard.git@gmail.com"
LABEL version="0.1.0"

#VERSION galera-node-health:0.1.0
RUN mkdir -p /health_check /health_check/www /health_check/logs /health_check/sockets /health_check/proxy_conf /health_check/conf

COPY health_check/init.sh health_check/get_checker_port.py /health_check/
COPY health_check/proxy_conf/* /health_check/proxy_conf/
#COPY health_check/www/* /health_check/www/
RUN chmod 777 /health_check/conf /health_check/proxy_conf /health_check/logs && chmod 666 /health_check/proxy_conf/*

#src directory is copied with build_script, because docker does not support symlinks outside of build context
COPY src /src
RUN apk --no-cache add bash lighttpd python3 python3-dev libc-dev gcc && python3 -m ensurepip --default-pip \
    && pip3 --no-cache-dir install --upgrade pip && pip3 --no-cache-dir install /src \
    && apk --no-cache del python3-dev libc-dev gcc
CMD ["/health_check/init.sh"]