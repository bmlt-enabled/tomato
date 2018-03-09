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

## Deploying with terraform
A terraform configuration is included in this repository. The configuration deploys both the Web Application and the Daemon to a small ECS Cluster in your AWS account. Some familiarity with AWS and Terraform is assumed, but there are a few things you'll need to put into place for the configuration to work.

1. Put your AWS credentials in a profile named "personal". See https://docs.aws.amazon.com/cli/latest/userguide/cli-multiple-profiles.html for information on named profiles.
2. Make sure you have a private key at ~/.ssh/id_rsa. Terraform uses this file as a data source to create a public key used for accessing the ECS instances.
3. Create an ECR repository named "tomato". See https://aws.amazon.com/ecr/getting-started/ for more information.
4. Build the docker image, and push it to the "tomato" repository.

## Local cluster (beta)

*No data is being populated yet*

To test using docker run the following.

```shell
docker-compose up
```

From there you can issue queries to the instance at `http://localhost:8080`, or use the bundled semantic workshop container at `http://localhost:8081/index.php`.  From there you can reference the tomato server as the root `http://tomato:8080/main_server`.
