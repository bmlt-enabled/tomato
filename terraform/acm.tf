resource "aws_acm_certificate" "tomato_bmltenabled" {
  domain_name       = "tomato.patrickj.org"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "tomato_bmltenabled" {
  certificate_arn         = aws_acm_certificate.tomato_bmltenabled.arn
  validation_record_fqdns = [for record in aws_route53_record.tomato_bmltenabled_validation : record.fqdn]
}

resource "aws_acm_certificate_validation" "tomato_fargate" {
  certificate_arn         = aws_acm_certificate.tomato_bmltenabled.arn
  validation_record_fqdns = [for record in aws_route53_record.tomato_bmltenabled_validation : record.fqdn]
}

# CHANGE
//data "aws_acm_certificate" "tomato_na_bmlt" {
//  domain      = "tomato.na-bmlt.org"
//  statuses    = ["ISSUED"]
//  most_recent = true
//}
