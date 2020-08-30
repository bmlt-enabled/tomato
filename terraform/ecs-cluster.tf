resource "aws_ecs_cluster" "main" {
  name = "tomato"
}

resource "aws_iam_role" "cluster_instance" {
  name = aws_ecs_cluster.main.name

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
  role       = aws_iam_role.cluster_instance.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_role_policy_attachment" "attach_ecr_policy" {
  role       = aws_iam_role.cluster_instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

data "aws_iam_policy_document" "cluster_instance" {
  statement {
    effect    = "Allow"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams"]
    resources = ["arn:aws:logs:*:*:*"]
  }
}

resource "aws_iam_role_policy" "cluster_instance" {
  name   = aws_iam_role.cluster_instance.name
  role   = aws_iam_role.cluster_instance.name
  policy = data.aws_iam_policy_document.cluster_instance.json
}

resource "aws_iam_instance_profile" "cluster" {
  name = aws_ecs_cluster.main.name
  role = aws_iam_role.cluster_instance.name
}

resource "aws_security_group" "cluster" {
  description = "controls direct access to cluster container instances"
  vpc_id      = aws_vpc.main.id
  name        = aws_ecs_cluster.main.name

  ingress {
    protocol  = "tcp"
    from_port = 32768
    to_port   = 61000

    security_groups = [
      aws_security_group.ecs_http_load_balancers.id,
    ]
  }

  //  ingress {
  //    protocol    = "tcp"
  //    from_port   = 22
  //    to_port     = 22
  //    cidr_blocks = ["0.0.0.0/0"]
  //  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "template_file" "user_data" {
  template = file("${path.module}/templates/user_data.sh")

  vars = {
    ecs_config        = "echo '' > /etc/ecs/ecs.config"
    ecs_logging       = "[\"json-file\",\"awslogs\"]"
    cluster_name      = aws_ecs_cluster.main.name
    cloudwatch_prefix = "tomato"
  }
}
