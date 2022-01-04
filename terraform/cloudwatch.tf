resource "aws_cloudwatch_log_group" "tomato_webapp" {
  name              = "tomato-webapp"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "tomato_root_server_import" {
  name              = "tomato-root-server-import"
  retention_in_days = 7
}

### Running the root server import
resource "aws_cloudwatch_event_rule" "root_server_import" {
  name                = "tomato-root-server-import"
  description         = "Kicks off root server import every 4 hours"
  schedule_expression = "rate(4 hours)"
}

data "aws_iam_policy_document" "ecs_events" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "ecs_events_run_task_with_any_role" {
  statement {
    effect    = "Allow"
    actions   = ["iam:PassRole"]
    resources = ["*"]
  }

  statement {
    effect    = "Allow"
    actions   = ["ecs:RunTask"]
    resources = [aws_ecs_task_definition.tomato_root_server_import.arn]
  }
}

resource "aws_iam_role" "ecs_events" {
  name               = "ecs-events"
  assume_role_policy = data.aws_iam_policy_document.ecs_events.json
}

resource "aws_iam_role_policy" "ecs_events_run_task_with_any_role" {
  name   = "ecs-events-run-task-with-any-role"
  role   = aws_iam_role.ecs_events.id
  policy = data.aws_iam_policy_document.ecs_events_run_task_with_any_role.json
}

resource "aws_cloudwatch_event_target" "root_server_import" {
  target_id = "tomato-root-server-import"
  arn       = aws_ecs_cluster.main.arn
  rule      = aws_cloudwatch_event_rule.root_server_import.name
  role_arn  = aws_iam_role.ecs_events.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.tomato_root_server_import.arn
  }
}

### Bounching ecs instances
//resource "aws_cloudwatch_event_rule" "refresh_ecs_instances" {
//  name                = "tomato-refresh-ecs-instances"
//  description         = "Refreshes all ecs instances every 3 days"
//  schedule_expression = "rate(3 days)"
//}
//
//resource "aws_cloudwatch_event_target" "refresh_ecs_instances" {
//  rule      = aws_cloudwatch_event_rule.refresh_ecs_instances.name
//  target_id = "lambda"
//  arn       = aws_lambda_function.refresh_ecs_instances.arn
//}


resource "aws_cloudwatch_metric_alarm" "lb_hosts" {
  alarm_name          = "tomato-alb-unhealthy-hosts"
  alarm_description   = "healthy hosts less than 2 for an hour"
  actions_enabled     = true
  comparison_operator = "LessThanThreshold"
  datapoints_to_alarm = 1
  evaluation_periods  = 1
  period              = 60
  threshold           = 2
  statistic           = "Average"
  treat_missing_data  = "missing"
  metric_name         = "HealthyHostCount"
  namespace           = "AWS/ApplicationELB"

  dimensions = {
    "LoadBalancer" = aws_alb.tomato.arn_suffix
    "TargetGroup"  = aws_alb_target_group.tomato.arn_suffix
  }

  alarm_actions             = [aws_sns_topic.lb_hosts.arn]
  ok_actions                = [aws_sns_topic.lb_hosts.arn]
  insufficient_data_actions = []

  tags = {
    Name = "tomato"
  }
}

resource "aws_sns_topic" "lb_hosts" {
  name = "tomato-alb-healthy-host"

  tags = {
    Name = "tomato"
  }
}
