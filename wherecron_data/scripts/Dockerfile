FROM python:3-alpine3.6

WORKDIR .
COPY requirements.txt ./

COPY argos.py .

RUN set -ex; \
	apk add --no-cache --virtual .fetch-deps py-mysqldb; \
	pip install --no-cache-dir -r requirements.txt; \
	apk del .fetch-deps

COPY . .

CMD [ "python", "argos.py" ]

