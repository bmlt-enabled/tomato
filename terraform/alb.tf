resource "aws_security_group" "ecs_http_load_balancers" {
  vpc_id = "${aws_vpc.main.id}"
  name   = "tomato-lb"

  ingress {
    protocol    = "tcp"
    from_port   = 80
    to_port     = 80
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"

    cidr_blocks = [
      "0.0.0.0/0",
    ]
  }
}

resource "aws_alb" "tomato" {
  name            = "tomato"
  subnets         = ["${aws_subnet.public_a.id}", "${aws_subnet.public_b.id}"]
  security_groups = ["${aws_security_group.ecs_http_load_balancers.id}"]
}

resource "aws_alb_target_group" "tomato" {
  name     = "tomato"
  port     = 80
  protocol = "HTTP"
  vpc_id   = "${aws_vpc.main.id}"

  health_check {
    path    = "/admin/"
    matcher = "302"
  }
}

resource "aws_alb_listener" "tomato" {
  load_balancer_arn = "${aws_alb.tomato.id}"
  port              = 80
  protocol          = "HTTP"

  default_action {
    target_group_arn = "${aws_alb_target_group.tomato.id}"
    type             = "forward"
  }
}
