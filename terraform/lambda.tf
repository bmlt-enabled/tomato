//resource "aws_lambda_function" "refresh_ecs_instances" {
//  function_name    = "tomato-refresh-ecs-instances"
//  filename         = "refresh_ecs_instances.zip"
//  handler          = "refresh_ecs_instances.handle"
//  runtime          = "python3.8"
//  role             = aws_iam_role.refresh_ecs_instances.arn
//  source_code_hash = data.archive_file.refresh_ecs_instances.output_base64sha256
//
//  tags = {
//    Name = "tomato-refresh-ecs-instances"
//  }
//}
//
//resource "aws_lambda_permission" "refresh_ecs_instances_cloudwatch_event_rule" {
//  statement_id  = "AllowExecutionFromCloudWatch"
//  action        = "lambda:InvokeFunction"
//  function_name = aws_lambda_function.refresh_ecs_instances.function_name
//  principal     = "events.amazonaws.com"
//  source_arn    = aws_cloudwatch_event_rule.refresh_ecs_instances.arn
//}
//
//data "archive_file" "refresh_ecs_instances" {
//  type        = "zip"
//  source_file = "refresh_ecs_instances.py"
//  output_path = "refresh_ecs_instances.zip"
//}
//
//data "aws_iam_policy_document" "lambda_assume_rule_policy" {
//  statement {
//    actions = ["sts:AssumeRole"]
//
//    principals {
//      type        = "Service"
//      identifiers = ["lambda.amazonaws.com"]
//    }
//  }
//}
//
//resource "aws_iam_role" "refresh_ecs_instances" {
//  name               = "tomato-refresh-ecs-instances"
//  assume_role_policy = data.aws_iam_policy_document.lambda_assume_rule_policy.json
//}
//
//data "aws_iam_policy_document" "refresh_ecs_instances" {
//  statement {
//    effect    = "Allow"
//    actions   = ["autoscaling:StartInstanceRefresh"]
//    resources = [aws_autoscaling_group.cluster.arn]
//  }
//}
//
//resource "aws_iam_role_policy" "refresh_ecs_instances" {
//  name   = aws_iam_role.refresh_ecs_instances.name
//  role   = aws_iam_role.refresh_ecs_instances.name
//  policy = data.aws_iam_policy_document.refresh_ecs_instances.json
//}
//
//resource "aws_iam_role_policy_attachment" "refresh_ecs_instances" {
//  role       = aws_iam_role.refresh_ecs_instances.name
//  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
//}
