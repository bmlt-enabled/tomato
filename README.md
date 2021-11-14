# tomato

Tomato aggregates meetings from multiple BMLT Root Servers and provides query access to those meetings through a clone of BMLT's Semantic API.

## Components
Tomato consists of two components, the Web Application and the Daemon.

### Web Application
Hosts our clone of the BMLT Semantic API and the Django Admin Console.

### Daemon
Loop that updates the database from the BMLT Root Servers on a timer.

`python3 manage.py import_root_servers`

## Configuration

### Database
Tomato requires a PostgreSQL database with PostGIS installed, and the user must be a superuser so that it can enable the postgis extension when running the initial migrations. The database connection information is configured using environment variables.

### Django Secret Key
A default SECRET_KEY has been provided, but this should be swapped out by using the `SECRET_KEY` environment variable in production. Using the default SECRET_KEY in production is _very, very bad_.

https://docs.djangoproject.com/en/2.0/ref/settings/#std:setting-SECRET_KEY

###  Environment Variables

| Name | Description |
| :--- | :---------- |
| RDS_NAME | PostgreSQL Database Name |
| RDS_USER | PostgreSQL Database User |
| RDS_PASSWORD | PostgreSQL Password |
| RDS_HOST | PostgreSQL Hostname |
| RDS_PORT | PostgreSQL Port |
| SECRET_KEY | Secret key used for Django crypto things |
| GOOGLE_MAPS_API_KEY | Google Maps API Key |

### Start a dev db
```
docker run -d \
  --name tomato \
  -e POSTGRES_PASSWORD=tomato \
  -e POSTGRES_USER=tomato \
  -e POSTGRES_DB=tomato \
  -p 5432:5432 \
  postgis/postgis
```

## Local cluster (beta)

*No data is being populated yet*

To test using docker run the following.

```shell
docker-compose up
```

From there you can issue queries to the instance at `http://localhost:8000/main_server`, or use the bundled semantic workshop container at `http://localhost:8001/index.php`.
