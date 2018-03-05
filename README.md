# tomato

Tomato aggregates meetings from multiple BMLT Root Servers and provides query access to those meetings through a clone of BMLT's Semantic API.

## Components
Tomato consists of two components: the Web Application and the Daemon

### Web Application
Hosts our clone of the BMLT Semantic API and the Django Admin Console.

### Daemon
In its current state, this is not really a daemon. It's just a command that updates the meetings database from the configured BMLT root servers, and then exits. The intent is to eventually make it a proper daemon by giving it a `while True` loop, running the synchronization logic on a timer to keep things up to date.

`python3 manage.py update_meetings`

## Configuration

### Database
Tomato requires a PostgreSQL database with PostGIS installed, and the user must be a superuser so that it can enable the postgis extension when running the initial migrations. The database connection information is configured using environment variables.

### Django Secret Key
A default SECRET_KEY has been provided, but this should be swapped out by using the `SECRET_KEY` environment variable in production. Using the default SECRET_KEY in production is _very, very bad_.

https://docs.djangoproject.com/en/2.0/ref/settings/#std:setting-SECRET_KEY

### BMLT Root Servers
The list of BMLT servers is configured in the django settings file:
```
ROOT_SERVERS = [
    'http://bmlt.ncregion-na.org/main_server/',
    'http://crna.org/main_server/',
    'http://www.alnwfl.org/main_server/',
    'http://naflorida.org/bmlt_server/',
    'http://www.grscnabmlt.tk/main_server/',
]
```

###  Environment Variables

| Name | Description |
| :--- | :---------- |
| RDS_NAME | PostgreSQL Database Name |
| RDS_USER | PostgreSQL Database User |
| PASSWORD | PostgreSQL Password |
| RDS_HOST | PostgreSQL Hostname |
| RDS_PORT | PostgreSQL Port |
| SECRET_KEY | Secret key used for Django crypto things |
