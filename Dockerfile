FROM python:3.6-slim-stretch

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
	git \
	gcc \
	g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/st3

COPY . /opt/st3

RUN pip3 install -r requirements.txt
