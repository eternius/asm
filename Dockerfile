FROM python:3.6-slim-stretch

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
	git \
	gcc \
	g++ \
	libmariadbclient-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/arcus/service

RUN mkdir -p /opt/arcus/conf
COPY . /opt/arcus/service

RUN pip3 install -r requirements.txt

VOLUME /opt/arcus/conf/config.yml

CMD ["python3", "asm.py"]