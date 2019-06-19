FROM python:3.6-slim-stretch

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
	git \
	gcc \
	g++ \
	libmariadbclient-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/arcus

COPY . /opt/arcus

RUN pip3 install -r requirements.txt

RUN python3 ./asm/utils/nlp/nltk.py

CMD ["python3", "asm.py"]