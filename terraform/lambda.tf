data "archive_file" "aggregator_lambda" {
  type        = "zip"
  source_file = "aggregator_lambda.py"
  output_path = "aggregator_lambda.zip"
}

resource "aws_lambda_function" "aggregator_lambda" {
  filename                       = "aggregator_lambda.zip"
  function_name                  = "AggregatorStoppedTask"
  role                           = aws_iam_role.aggregator_lambda.arn
  handler                        = "aggregator_lambda.lambda_handler"
  source_code_hash               = data.archive_file.aggregator_lambda.output_base64sha256
  runtime                        = "python3.11"
  memory_size                    = 128
  timeout                        = 30
  reserved_concurrent_executions = 1

  environment {
    variables = {
      SNS_TOPIC = aws_sns_topic.lb_hosts.arn
    }
  }
}

resource "aws_lambda_permission" "aggregator_allow_cloudwatch" {
  statement_id  = "AggregatorAllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.aggregator_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.aggregator_ecs_state.arn
}

resource "aws_iam_role" "aggregator_lambda" {
  name = "aggregator_lambda_iam_role"
  assume_role_policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [
        {
          Action = "sts:AssumeRole"
          Principal = {
            Service = "lambda.amazonaws.com"
          }
          Effect = "Allow"
        }
      ]
  })
}

resource "aws_iam_policy" "aggregator_lambda" {
  name = "aggregator_lambda_iam_policy"
  policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [
        {
          Effect = "Allow"
          Action = [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ]
          Resource = "*"
        },
        {
          Effect = "Allow"
          Action = [
            "sns:Publish"
          ]
          Resource = aws_sns_topic.lb_hosts.arn
        }
      ]
  })
}

resource "aws_iam_role_policy_attachment" "aggregator_lambda" {
  role       = aws_iam_role.aggregator_lambda.name
  policy_arn = aws_iam_policy.aggregator_lambda.arn
}
