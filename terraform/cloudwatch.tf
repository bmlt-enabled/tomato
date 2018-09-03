resource "aws_cloudwatch_log_group" "tomato_webapp" {
  name              = "tomato-webapp"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "tomato_daemon" {
  name              = "tomato-daemon"
  retention_in_days = 7
}

resource "aws_cloudwatch_metric_alarm" "root_server_sync" {
  alarm_name          = "root-server-sync-stuck"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "RootServerSynchronizationCount"
  namespace           = "Tomato"
  period              = "18000"
  threshold           = "1"
  statistic           = "Sum"
  alarm_description   = "Monitors root server synchronizations"
  treat_missing_data  = "breaching"

  ok_actions                = ["${aws_sns_topic.alarms.arn}"]
  alarm_actions             = ["${aws_sns_topic.alarms.arn}"]
  insufficient_data_actions = ["${aws_sns_topic.alarms.arn}"]
}

resource "aws_cloudwatch_log_metric_filter" "root_server_sync" {
  name           = "daemon-retrieving-root-servers-filter"
  pattern        = "retrieving root servers"
  log_group_name = "${aws_cloudwatch_log_group.tomato_daemon.name}"

  metric_transformation {
    name      = "RootServerSynchronizationCount"
    namespace = "Tomato"
    value     = "1"
  }

  depends_on = ["aws_cloudwatch_metric_alarm.root_server_sync"]
}