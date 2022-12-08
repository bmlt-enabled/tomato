resource "aws_lb_target_group" "aggregator" {
  name                 = "aggregator"
  port                 = 8000
  protocol             = "HTTP"
  vpc_id               = data.aws_vpc.main.id
  deregistration_delay = 5

  health_check {
    path    = "/"
    matcher = "200"
  }
}

resource "aws_alb_listener_rule" "aggregator" {
  listener_arn = data.aws_lb_listener.main_443.arn

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.aggregator.arn
  }

  condition {
    host_header {
      values = [data.aws_route53_zone.tomato_bmltenabled_org.name]
    }
  }
}
