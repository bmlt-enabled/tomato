from . import *

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
        'NAME': 'testdb.sqlite3',
    }
}


def in_docker():
    with open('/proc/self/cgroup', 'r') as procfile:
        for line in procfile:
            fields = line.strip().split('/')
            if fields[1] == 'docker':
                return True


if in_docker():
    SPATIALITE_LIBRARY_PATH = '/usr/lib/mod_spatialite.so.7'
