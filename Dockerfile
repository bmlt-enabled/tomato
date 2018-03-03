FROM alpine:3.7

RUN apk add --no-cache \
    python3 \
    python3-dev \
    build-base \
    linux-headers \
    libffi-dev \
    postgresql-dev

RUN mkdir /code
WORKDIR /code
ADD src/tomato /code/tomato
ADD src/manage.py /code
ADD requirements.txt /code

RUN pip3 install uwsgi==2.0.15
RUN pip3 install -r requirements.txt

EXPOSE 8080

CMD [ "uwsgi", "--master", \
    "--http", "0.0.0.0:8080", \
    "--module", "tomato.wsgi", \
    "--processes", "32" ]
