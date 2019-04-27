FROM python:3-slim-stretch
LABEL maintainer="Vladislav Yarmak <vladislav-ex-src@vm-0.com>"

VOLUME [ "/srv/data" ]
COPY . /build
RUN echo deb http://deb.debian.org/debian stretch-backports main \
    >> /etc/apt/sources.list && \
    apt-get update && apt-get install -y -t stretch-backports sqlite3 && \
    apt-get clean && rm -rf /var/cache/apt/archives/* && \
    pip3 install --no-cache-dir /build && \
    rm -rf /build

EXPOSE 8022/tcp
ENTRYPOINT [ "ssh-honeypot" ]
