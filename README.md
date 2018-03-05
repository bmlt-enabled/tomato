# tomato

Tomato aggregates meetings from multiple BMLT Root Servers and provides queryable access to those meetings through a clone of BMLT's semantic API.

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
