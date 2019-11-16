from sys import platform
from . import *

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
        'TEST': {'NAME': 'testdb.sqlite3'},
    },
}


def in_docker():
    if os.path.exists('/proc/self/cgroup'):
        with open('/proc/self/cgroup', 'r') as procfile:
            for line in procfile:
                fields = line.strip().split('/')
                if fields[1] == 'docker':
                    return True
    return False


if platform == "darwin":
    SPATIALITE_LIBRARY_PATH = '/usr/local/lib/mod_spatialite.dylib'
