# IAM Role for ECS Service interaction with load balancer
resource "aws_iam_role" "tomato_lb" {
  name = "tomato-lb"

  assume_role_policy = <<EOF
{
  "Version": "2008-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

}

resource "aws_iam_role_policy" "tomato_lb" {
  name = aws_iam_role.tomato_lb.name
  role = aws_iam_role.tomato_lb.name

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "elasticloadbalancing:DeregisterInstancesFromLoadBalancer",
        "elasticloadbalancing:DeregisterTargets",
        "elasticloadbalancing:Describe*",
        "elasticloadbalancing:RegisterInstancesWithLoadBalancer",
        "elasticloadbalancing:RegisterTargets"
      ],
      "Resource": "*"
    }
  ]
}
EOF

}

resource "aws_ecs_task_definition" "webapp" {
  family                   = "tomato-webapp"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.tomato_lb.arn
  task_role_arn            = aws_iam_role.tomato_lb.arn

  container_definitions = <<EOF
[
  {
    "cpu": ${var.cpu},
    "memory": ${var.memory},
    "image": "${aws_ecr_repository.tomato.repository_url}:latest",
    "volumesFrom": [],
    "extraHosts": null,
    "dnsServers": null,
    "disableNetworking": null,
    "networkMode": "awsvpc",
    "dnsSearchDomains": null,
    "portMappings": [
      {
        "hostPort": 8000,
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
      },
      {
        "name": "GOOGLE_MAPS_API_KEY",
        "value": "AIzaSyD4BPAvDHL4CiRcFORdoUCpqwVuVz1F9r8"
      },
      {
        "name": "SECRET_KEY",
        "value": "${var.secret_key}"
      }
    ],
    "workingDirectory": "/code",
    "readonlyRootFilesystem": null,
    "command": [
      "sh",
      "-c",
      "python3 manage.py initialize && uwsgi --ini /code/uwsgi.ini"
    ],
    "user": null,
    "dockerLabels": null,
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "${aws_cloudwatch_log_group.tomato_webapp.name}",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "webapp"
      }
    },
    "privileged": null,
    "memoryReservation": 512,
    "linuxParameters": {
      "initProcessEnabled": true
    }
  }
]
EOF

}


resource "aws_ecs_task_definition" "tomato_root_server_import" {
  family                   = "tomato-root-server-import"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.tomato_lb.arn
  task_role_arn            = aws_iam_role.tomato_lb.arn
  container_definitions    = <<EOF
[
  {
    "cpu": ${var.cpu},
    "memory": ${var.memory},
    "image": "${aws_ecr_repository.tomato.repository_url}:latest",
    "name": "tomato-fargate",
    "networkMode": "awsvpc",
    "workingDirectory": "/code",
    "command": [
      "sh",
      "-c",
      "python3 manage.py initialize && python3 manage.py import_root_servers"
    ],
    "portMappings": [
      {
        "containerPort": 8000,
        "hostPort": 8000
      }
    ],
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
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "${aws_cloudwatch_log_group.tomato_root_server_import.name}",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "daemon"
      }
    },
    "linuxParameters": {
      "initProcessEnabled": true
    }
  }
]
EOF

}

resource "aws_ecs_service" "webapp" {
  name                               = "webapp"
  cluster                            = aws_ecs_cluster.main.id
  desired_count                      = 2
  task_definition                    = aws_ecs_task_definition.webapp.arn
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 50

  load_balancer {
    target_group_arn = aws_alb_target_group.tomato.id
    container_name   = "tomato"
    container_port   = 8000
  }

  network_configuration {
    security_groups  = [aws_security_group.cluster.id]
    subnets          = [aws_subnet.public_a.id, aws_subnet.public_b.id]
    assign_public_ip = true
  }

  depends_on = [
    aws_iam_role_policy.tomato_lb,
    aws_alb_listener.tomato_https,
  ]
}
