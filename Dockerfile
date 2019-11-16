FROM ubuntu:18.04

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install -y \
  python3 \
  python3-pip \
  python3-dev \
  libgdal-dev \
  libspatialite-dev \
  libsqlite3-mod-spatialite \
  libgeos++-dev \
  libproj-dev

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
