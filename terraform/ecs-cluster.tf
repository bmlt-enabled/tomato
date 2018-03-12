resource "aws_cloudwatch_log_group" "ecs" {
  name = "tomato/ecs-agent"
}

resource "aws_ecs_cluster" "main" {
  name = "tomato"
}

resource "aws_iam_role" "cluster_instance" {
  name = "${aws_ecs_cluster.main.name}"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "attach_ecs_policy" {
  role       = "${aws_iam_role.cluster_instance.name}"
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_role_policy_attachment" "attach_ecr_policy" {
  role       = "${aws_iam_role.cluster_instance.name}"
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy" "allow_logging_policy" {
  name = "${aws_iam_role.cluster_instance.name}"
  role = "${aws_iam_role.cluster_instance.name}"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "allowLoggingToCloudWatch",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": [
        "${aws_cloudwatch_log_group.ecs.arn}"
      ]
    }
  ]
}
EOF
}

resource "aws_iam_instance_profile" "cluster" {
  name = "${aws_ecs_cluster.main.name}"
  role = "${aws_iam_role.cluster_instance.name}"
}

resource "aws_autoscaling_group" "cluster" {
  name                 = "${aws_ecs_cluster.main.name}"
  vpc_zone_identifier  = ["${aws_subnet.public_a.id}"]
  min_size             = 2
  max_size             = 2
  desired_capacity     = 2
  launch_configuration = "${aws_launch_configuration.cluster.name}"

  tags = [
    {
      key                 = "application"
      value               = "tomato"
      propagate_at_launch = true
    },
    {
      key                 = "environment"
      value               = "production"
      propagate_at_launch = true
    },
  ]
}

resource "aws_security_group" "cluster" {
  description = "controls direct access to cluster container instances"
  vpc_id      = "${aws_vpc.main.id}"
  name        = "${aws_ecs_cluster.main.name}"

  ingress {
    protocol  = "tcp"
    from_port = 32768
    to_port   = 61000

    security_groups = [
      "${aws_security_group.ecs_http_load_balancers.id}",
    ]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_launch_configuration" "cluster" {
  security_groups             = ["${aws_security_group.cluster.id}"]
  key_name                    = "${aws_key_pair.main.key_name}"
  image_id                    = "ami-a7a242da"
  instance_type               = "t2.micro"
  iam_instance_profile        = "${aws_iam_instance_profile.cluster.name}"
  associate_public_ip_address = false

  user_data = <<EOF
#!/bin/bash
echo ECS_CLUSTER=${aws_ecs_cluster.main.name} >> /etc/ecs/ecs.config
echo ECS_LOGLEVEL=info >> /etc/ecs/ecs.config
echo REGION=us-east-1 >> /etc/ecs/ecs.config
EOF

  lifecycle {
    create_before_destroy = true
  }
}
