
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND noninteractive

ADD . /srv/app
RUN apt-get -y update && \
    apt-get -y dist-upgrade && \
    apt-get install -y --no-install-recommends rsync ssh python3-pip python3-wheel python3-pkg-resources python3-setuptools python3-dev default-libmysqlclient-dev gcc tzdata build-essential pkg-config && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade -r /srv/app/requirements.txt --break-system-packages

RUN mkdir /srv/app/media && chown daemon /srv/app/media

USER daemon
WORKDIR /srv/app
CMD ["/srv/app/deploy/run-wsgi.sh"]

EXPOSE 8000
