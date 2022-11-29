data "archive_file" "sms_lambda" {
  type        = "zip"
  source_file = "sms-alerts.py"
  output_path = "sms-alerts.zip"
}

resource "aws_lambda_function" "sms_lambda" {
  filename                       = data.archive_file.sms_lambda.output_path
  function_name                  = "sms-alerts"
  role                           = aws_iam_role.sms_lambda_iam_role.arn
  description                    = "Send SMS from SNS"
  handler                        = "sms-alerts.lambda_handler"
  source_code_hash               = data.archive_file.sms_lambda.output_base64sha256
  runtime                        = "python3.9"
  layers                         = ["arn:aws:lambda:us-east-1:766033189774:layer:twilio:1"]
  memory_size                    = 128
  timeout                        = 60
  reserved_concurrent_executions = 2

  environment {
    variables = {
      ACCOUNT_SID   = "cool"
      ACCOUNT_TOKEN = "story"
      TO_NUMBERS    = "bra"
      FROM_NUMBER   = "not"
    }
  }

  lifecycle {
    ignore_changes = [environment.0.variables]
  }
}

resource "aws_cloudwatch_log_group" "sms_lambda" {
  name              = "/aws/lambda/sms-alerts"
  retention_in_days = 30
}

resource "aws_lambda_permission" "sms_sns" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sms_lambda.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.lb_hosts.arn
}


resource "aws_sns_topic_subscription" "sms_lambda" {
  topic_arn = aws_sns_topic.lb_hosts.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.sms_lambda.arn
}

data "aws_iam_policy_document" "sms_lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "sms_lambda_policy_document" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "${aws_cloudwatch_log_group.sms_lambda.arn}:*"
    ]
  }
}

resource "aws_iam_policy" "sms_lambda_action_role_policy" {
  name   = "sms-lambda-iam-role-policy"
  policy = data.aws_iam_policy_document.sms_lambda_policy_document.json
}

resource "aws_iam_role" "sms_lambda_iam_role" {
  name                = "sms-lambda-role"
  description         = "Lambda role for sms"
  assume_role_policy  = data.aws_iam_policy_document.sms_lambda_assume_role.json
  managed_policy_arns = [aws_iam_policy.sms_lambda_action_role_policy.arn]
}
