resource "aws_athena_database" "tomato_webapp_alb_logs" {
  name   = "tomato_webapp_alb_logs"
  bucket = "${aws_s3_bucket.tomato_webapp_alb_logs_athena.bucket}"
}

resource "aws_s3_bucket" "tomato_webapp_alb_logs_athena" {
  bucket_prefix = "tomato-webapp-alb-logs-athena-"
}

resource "aws_s3_bucket" "tomato_webapp_alb_logs" {
  bucket_prefix = "tomato-webapp-alb-logs-"
}

resource "aws_s3_bucket_policy" "tomato_webapp_alb_logs" {
  bucket = "${aws_s3_bucket.tomato_webapp_alb_logs.id}"
  policy = <<EOF
{
  "Id": "Policy1521565569242",
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Stmt1521565353380",
      "Action": "s3:PutObject",
      "Effect": "Allow",
      "Resource": "${aws_s3_bucket.tomato_webapp_alb_logs.arn}/*",
      "Principal": {
        "AWS": "arn:aws:iam::127311923021:root"
      }
    }
  ]
}
EOF
}

resource "aws_security_group" "ecs_http_load_balancers" {
  vpc_id = "${aws_vpc.main.id}"
  name   = "tomato-lb"

  ingress {
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"

    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_alb" "tomato" {
  name            = "tomato"
  subnets         = ["${aws_subnet.public_a.id}", "${aws_subnet.public_b.id}"]
  security_groups = ["${aws_security_group.ecs_http_load_balancers.id}"]

  access_logs {
    bucket = "${aws_s3_bucket.tomato_webapp_alb_logs.bucket}"
    enabled = true
  }

  tags {
    Name = "tomato"
  }
}

resource "aws_alb_target_group" "tomato" {
  name     = "tomato"
  port     = 80
  protocol = "HTTP"
  vpc_id   = "${aws_vpc.main.id}"

  deregistration_delay = 60

  health_check {
    path    = "/ping/"
    matcher = "200"
  }
}

resource "aws_alb_listener" "tomato_https" {
  load_balancer_arn = "${aws_alb.tomato.id}"
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = "${aws_acm_certificate.tomato_bmltenabled.arn}"

  default_action {
    target_group_arn = "${aws_alb_target_group.tomato.id}"
    type             = "forward"
  }
}

resource "aws_alb_listener_certificate" "tomato_bmlt_cert" {
  listener_arn    = "${aws_alb_listener.tomato_https.arn}"
  certificate_arn = "${data.aws_acm_certificate.tomato_na_bmlt.arn}"
}
