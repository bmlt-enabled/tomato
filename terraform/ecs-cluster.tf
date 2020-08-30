resource "aws_ecs_cluster" "main" {
  name = "tomato"
}

resource "aws_security_group" "cluster" {
  description = "controls direct access to cluster container instances"
  vpc_id      = aws_vpc.main.id
  name        = aws_ecs_cluster.main.name

  ingress {
    protocol  = "tcp"
    from_port = 8000
    to_port   = 8000

    security_groups = [
      aws_security_group.ecs_http_load_balancers.id,
    ]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
