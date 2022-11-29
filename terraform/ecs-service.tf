# IAM Role for ECS Service interaction with load balancer
resource "aws_iam_role" "tomato_lb" {
  name = "tomato-lb"

  assume_role_policy = jsonencode({
    Version = "2008-10-17"
    Statement = [
      {
        Sid    = ""
        Effect = "Allow"
        Principal = {
          Service = "ecs.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

}

resource "aws_iam_role_policy" "tomato_lb" {
  name = aws_iam_role.tomato_lb.name
  role = aws_iam_role.tomato_lb.name

  policy = jsonencode(
    {
      Version = "2012-10-17",
      Statement = [
        {
          Effect = "Allow"
          Action = [
            "ec2:Describe*",
            "elasticloadbalancing:DeregisterInstancesFromLoadBalancer",
            "elasticloadbalancing:DeregisterTargets",
            "elasticloadbalancing:Describe*",
            "elasticloadbalancing:RegisterInstancesWithLoadBalancer",
            "elasticloadbalancing:RegisterTargets"
          ]
          Resource = "*"
        }
      ]
  })
}

data "aws_iam_role" "ecs_task_role" {
  name = "ecs-exec-task-role"
}

resource "aws_ecs_task_definition" "webapp" {
  family        = "tomato-webapp"
  task_role_arn = data.aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode(
    [
      {
        volumesFrom       = []
        extraHosts        = null
        dnsServers        = null
        disableNetworking = null
        dnsSearchDomains  = null
        portMappings = [
          {
            hostPort      = 0
            containerPort = 8000
            protocol      = "tcp"
          }
        ]
        hostname              = null
        essential             = true
        entryPoint            = null
        mountPoints           = []
        name                  = "tomato"
        ulimits               = null
        dockerSecurityOptions = null
        environment = [
          {
            name  = "RDS_HOST"
            value = aws_db_instance.tomato.address
          },
          {
            name  = "RDS_NAME"
            value = aws_db_instance.tomato.db_name
          },
          {
            name  = "RDS_USER"
            value = aws_db_instance.tomato.username
          },
          {
            name  = "RDS_PASSWORD"
            value = aws_db_instance.tomato.password
          },
          {
            name  = "RDS_PORT"
            value = tostring(aws_db_instance.tomato.port)
          },
          {
            name  = "GOOGLE_MAPS_API_KEY"
            value = "AIzaSyD4BPAvDHL4CiRcFORdoUCpqwVuVz1F9r8"
          },
          {
            name  = "SECRET_KEY"
            value = var.secret_key
          }
        ]
        workingDirectory       = "/code"
        readonlyRootFilesystem = null
        image                  = "${aws_ecr_repository.tomato.repository_url}:latest"
        command = [
          "sh",
          "-c",
          "python3 manage.py initialize && uwsgi --ini /code/uwsgi.ini"
        ]
        user         = null
        dockerLabels = null
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            awslogs-group         = aws_cloudwatch_log_group.tomato_webapp.name
            awslogs-region        = "us-east-1"
            awslogs-stream-prefix = "webapp"
          }
        }
        cpu               = 700
        privileged        = null
        memoryReservation = 512
        linuxParameters = {
          initProcessEnabled = true
        }
      }
  ])

}

//resource "aws_ecs_task_definition" "webapp" {
//  family = "tomato-webapp"
//
//  container_definitions = <<EOF
//[
//  {
//    "volumesFrom": [],
//    "extraHosts": null,
//    "dnsServers": null,
//    "disableNetworking": null,
//    "dnsSearchDomains": null,
//    "portMappings": [
//      {
//        "hostPort": 0,
//        "containerPort": 8000,
//        "protocol": "tcp"
//      }
//    ],
//    "hostname": null,
//    "essential": true,
//    "entryPoint": null,
//    "mountPoints": [],
//    "name": "tomato",
//    "ulimits": null,
//    "dockerSecurityOptions": null,
//    "environment": [
//      {
//        "name": "RDS_HOST",
//        "value": "${aws_db_instance.tomato.address}"
//      },
//      {
//        "name": "RDS_NAME",
//        "value": "${aws_db_instance.tomato.name}"
//      },
//      {
//        "name": "RDS_USER",
//        "value": "${aws_db_instance.tomato.username}"
//      },
//      {
//        "name": "RDS_PASSWORD",
//        "value": "${aws_db_instance.tomato.password}"
//      },
//      {
//        "name": "RDS_PORT",
//        "value": "${aws_db_instance.tomato.port}"
//      },
//      {
//        "name": "GOOGLE_MAPS_API_KEY",
//        "value": "AIzaSyD4BPAvDHL4CiRcFORdoUCpqwVuVz1F9r8"
//      },
//      {
//        "name": "SECRET_KEY",
//        "value": "${var.secret_key}"
//      },
//      {
//        "name": "CACHE_FORMATS",
//        "value": "1"
//      },
//      {
//        "name": "REDIS_LOCATION",
//        "value": "redis://redis:6379"
//      }
//    ],
//    "links": ["redis"],
//    "workingDirectory": "/code",
//    "readonlyRootFilesystem": null,
//    "image": "${aws_ecr_repository.tomato.repository_url}:latest",
//    "command": [
//      "sh",
//      "-c",
//      "python3 manage.py initialize && uwsgi --ini /code/uwsgi.ini"
//    ],
//    "user": null,
//    "dockerLabels": null,
//    "logConfiguration": {
//      "logDriver": "awslogs",
//      "options": {
//        "awslogs-group": "${aws_cloudwatch_log_group.tomato_webapp.name}",
//        "awslogs-region": "us-east-1",
//        "awslogs-stream-prefix": "webapp"
//      }
//    },
//    "cpu": 700,
//    "privileged": null,
//    "memoryReservation": 512,
//    "linuxParameters": {
//      "initProcessEnabled": true
//    }
//  },
//  {
//    "name": "redis",
//    "volumesFrom": [],
//    "extraHosts": null,
//    "dnsServers": null,
//    "disableNetworking": null,
//    "dnsSearchDomains": null,
//    "portMappings": [
//      {
//        "containerPort": 6379,
//        "protocol": "tcp"
//      }
//    ],
//    "hostname": null,
//    "essential": true,
//    "entryPoint": ["docker-entrypoint.sh"],
//    "mountPoints": [],
//    "ulimits": null,
//    "dockerSecurityOptions": null,
//    "environment": [],
//    "links": [],
//    "workingDirectory": "/data",
//    "readonlyRootFilesystem": null,
//    "image": "redis:6.0.5",
//    "command": ["redis-server"],
//    "user": null,
//    "dockerLabels": null,
//    "logConfiguration": {
//      "logDriver": "awslogs",
//      "options": {
//        "awslogs-group": "${aws_cloudwatch_log_group.tomato_webapp.name}",
//        "awslogs-region": "us-east-1",
//        "awslogs-stream-prefix": "redis"
//      }
//    },
//    "memoryReservation": 128,
//    "privileged": null,
//    "linuxParameters": {
//      "initProcessEnabled": true
//    }
//  }
//]
//EOF
//
//}

resource "aws_ecs_task_definition" "tomato_root_server_import" {
  family        = "tomato-root-server-import"
  task_role_arn = data.aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode(
    [
      {
        volumesFrom           = []
        extraHosts            = null
        dnsServers            = null
        disableNetworking     = null
        dnsSearchDomains      = null
        portMappings          = []
        hostname              = null
        essential             = true
        entryPoint            = null
        mountPoints           = []
        name                  = "tomato"
        ulimits               = null
        dockerSecurityOptions = null
        environment = [
          {
            name  = "RDS_HOST",
            value = aws_db_instance.tomato.address
          },
          {
            name  = "RDS_NAME",
            value = aws_db_instance.tomato.db_name
          },
          {
            name  = "RDS_USER",
            value = aws_db_instance.tomato.username
          },
          {
            name  = "RDS_PASSWORD",
            value = aws_db_instance.tomato.password
          },
          {
            name  = "RDS_PORT",
            value = tostring(aws_db_instance.tomato.port)
          }
        ]
        links                  = []
        workingDirectory       = "/code"
        readonlyRootFilesystem = null
        image                  = "${aws_ecr_repository.tomato.repository_url}:latest"
        command = [
          "sh",
          "-c",
          "python3 manage.py initialize && python3 manage.py import_root_servers"
        ]
        user         = null
        dockerLabels = null
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            awslogs-group         = aws_cloudwatch_log_group.tomato_root_server_import.name
            awslogs-region        = "us-east-1"
            awslogs-stream-prefix = "daemon"
          }
        }
        cpu               = 256
        privileged        = null
        memoryReservation = 256
        linuxParameters = {
          initProcessEnabled = true
        }
      }
  ])
}

resource "aws_ecs_service" "webapp" {
  name                               = "webapp"
  cluster                            = aws_ecs_cluster.main.id
  desired_count                      = 2
  iam_role                           = aws_iam_role.tomato_lb.name
  task_definition                    = aws_ecs_task_definition.webapp.arn
  enable_execute_command             = true
  deployment_minimum_healthy_percent = 50

  load_balancer {
    target_group_arn = aws_alb_target_group.tomato.id
    container_name   = "tomato"
    container_port   = 8000
  }

  ordered_placement_strategy {
    type  = "spread"
    field = "attribute:ecs.availability-zone"
  }

  depends_on = [
    aws_iam_role_policy.tomato_lb,
    aws_alb_listener.tomato_https,
  ]
}
