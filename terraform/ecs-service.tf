data "aws_ecr_repository" "tomato" {
  name = "tomato"
}

resource "aws_cloudwatch_log_group" "tomato" {
  name              = "tomato"
  retention_in_days = 7
}

# RDS
resource "aws_security_group" "tomato_rds" {
  name   = "tomato-rds"
  vpc_id = "${aws_vpc.main.id}"

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["${aws_subnet.public_a.cidr_block}", "${aws_subnet.public_b.cidr_block}"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_subnet_group" "tomato" {
  name       = "tomato"
  subnet_ids = ["${aws_subnet.public_a.id}", "${aws_subnet.public_b.id}"]
}

resource "aws_db_instance" "tomato" {
  identifier        = "tomato"
  allocated_storage = 100
  engine            = "postgres"
  engine_version    = "9.5.4"
  instance_class    = "db.t2.small"

  name     = "tomato"
  username = "tomato"
  password = "${var.rds_password}"
  port     = 5432

  apply_immediately      = true
  publicly_accessible    = true
  vpc_security_group_ids = ["${aws_security_group.tomato_rds.id}"]
  db_subnet_group_name   = "${aws_db_subnet_group.tomato.name}"

  skip_final_snapshot = true
}

resource "aws_ecs_task_definition" "webapp" {
  family = "tomato-webapp"

  container_definitions = <<EOF
[
  {
    "volumesFrom": [],
    "memory": 768,
    "extraHosts": null,
    "dnsServers": null,
    "disableNetworking": null,
    "dnsSearchDomains": null,
    "portMappings": [
      {
        "hostPort": 80,
        "containerPort": 8000,
        "protocol": "tcp"
      }
    ],
    "hostname": null,
    "essential": true,
    "entryPoint": null,
    "mountPoints": [],
    "name": "tomato",
    "ulimits": null,
    "dockerSecurityOptions": null,
    "environment": [
      {
        "name": "RDS_HOST",
        "value": "${aws_db_instance.tomato.address}"
      },
      {
        "name": "RDS_NAME",
        "value": "${aws_db_instance.tomato.name}"
      },
      {
        "name": "RDS_USER",
        "value": "${aws_db_instance.tomato.username}"
      },
      {
        "name": "RDS_PASSWORD",
        "value": "${aws_db_instance.tomato.password}"
      },
      {
        "name": "RDS_PORT",
        "value": "${aws_db_instance.tomato.port}"
      }
    ],
    "links": [],
    "workingDirectory": "/code",
    "readonlyRootFilesystem": null,
    "image": "${data.aws_ecr_repository.tomato.repository_url}:latest",
    "command": [
      "sh",
      "-c",
      "python3 manage.py initialize && uwsgi --master --http 0.0.0.0:8000 --module tomato.wsgi --processes 32"
    ],
    "user": null,
    "dockerLabels": null,
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "${aws_cloudwatch_log_group.tomato.name}",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "webapp"
      }
    },
    "cpu": 750,
    "privileged": null,
    "memoryReservation": null
  }
]
EOF
}

resource "aws_ecs_task_definition" "daemon" {
  family = "tomato-daemon"

  container_definitions = <<EOF
[
  {
    "volumesFrom": [],
    "memory": 768,
    "extraHosts": null,
    "dnsServers": null,
    "disableNetworking": null,
    "dnsSearchDomains": null,
    "portMappings": [],
    "hostname": null,
    "essential": true,
    "entryPoint": null,
    "mountPoints": [],
    "name": "tomato",
    "ulimits": null,
    "dockerSecurityOptions": null,
    "environment": [
      {
        "name": "RDS_HOST",
        "value": "${aws_db_instance.tomato.address}"
      },
      {
        "name": "RDS_NAME",
        "value": "${aws_db_instance.tomato.name}"
      },
      {
        "name": "RDS_USER",
        "value": "${aws_db_instance.tomato.username}"
      },
      {
        "name": "RDS_PASSWORD",
        "value": "${aws_db_instance.tomato.password}"
      },
      {
        "name": "RDS_PORT",
        "value": "${aws_db_instance.tomato.port}"
      }
    ],
    "links": [],
    "workingDirectory": "/code",
    "readonlyRootFilesystem": null,
    "image": "${data.aws_ecr_repository.tomato.repository_url}:latest",
    "command": [
      "sh",
      "-c",
      "python3 manage.py initialize && python3 manage.py update_meetings"
    ],
    "user": null,
    "dockerLabels": null,
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "${aws_cloudwatch_log_group.tomato.name}",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "daemon"
      }
    },
    "cpu": 750,
    "privileged": null,
    "memoryReservation": null
  }
]
EOF
}

resource "aws_ecs_service" "webapp" {
  name            = "webapp"
  cluster         = "${aws_ecs_cluster.main.id}"
  desired_count   = 1
  task_definition = "${aws_ecs_task_definition.webapp.arn}"
}

resource "aws_ecs_service" "daemon" {
  name            = "daemon"
  cluster         = "${aws_ecs_cluster.main.id}"
  desired_count   = 1
  task_definition = "${aws_ecs_task_definition.daemon.arn}"
}
