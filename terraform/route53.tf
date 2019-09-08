data "aws_route53_zone" "bmltenabled" {
  name = "bmltenabled.org."
}

resource "aws_route53_record" "tomato_bmltenabled" {
  zone_id = data.aws_route53_zone.bmltenabled.id
  name    = "tomato.${data.aws_route53_zone.bmltenabled.name}"
  type    = "CNAME"
  ttl     = "300"
  records = [aws_alb.tomato.dns_name]
}

resource "aws_route53_record" "tomato_bmltenabled_validation" {
  name    = aws_acm_certificate.tomato_bmltenabled.domain_validation_options[0].resource_record_name
  type    = aws_acm_certificate.tomato_bmltenabled.domain_validation_options[0].resource_record_type
  zone_id = data.aws_route53_zone.bmltenabled.zone_id
  records = [aws_acm_certificate.tomato_bmltenabled.domain_validation_options[0].resource_record_value]
  ttl     = 60
}

