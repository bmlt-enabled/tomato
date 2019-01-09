FROM alpine:3.7

RUN apk add --no-cache \
    python3 \
    python3-dev \
    build-base \
    linux-headers \
    libffi-dev \
    postgresql-dev

RUN apk add --no-cache \
    --repository http://dl-cdn.alpinelinux.org/alpine/edge/main \
    libressl2.7-libcrypto \
    openssl

RUN apk add --no-cache \
    --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \
    gdal-dev \
    geos-dev \
    proj4-dev \
    libspatialite

RUN mkdir /code
WORKDIR /code

ADD requirements.txt /code
RUN pip3 install uwsgi==2.0.17
RUN pip3 install -r requirements.txt

ADD src/tomato /code/tomato
ADD src/manage.py /code
ADD uwsgi.ini /code
RUN DJANGO_SETTINGS_MODULE=tomato.settings.test python3 manage.py test

EXPOSE 8000

CMD [ "uwsgi", "--ini", "/code/uwsgi.ini"]
