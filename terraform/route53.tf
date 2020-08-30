data "aws_route53_zone" "bmltenabled" {
  name = "patrickj.org."  # CHANGE tomato.bmltenabled.org.
}

resource "aws_route53_record" "tomato_bmltenabled" {
  zone_id = data.aws_route53_zone.bmltenabled.id
  name    = data.aws_route53_zone.bmltenabled.name
  type    = "A"

  alias {
    name                   = aws_alb.tomato.dns_name
    zone_id                = aws_alb.tomato.zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "tomato_bmltenabled_validation" {
  for_each = {
    for dvo in aws_acm_certificate.tomato_bmltenabled.domain_validation_options : dvo.domain_name => {
      name    = dvo.resource_record_name
      record  = dvo.resource_record_value
      type    = dvo.resource_record_type
      zone_id = data.aws_route53_zone.bmltenabled.zone_id
    }
  }
  name    = each.value.name
  records = [each.value.record]
  type    = each.value.type
  zone_id = each.value.zone_id
  ttl     = 60
}



# CHANGE
resource "aws_route53_record" "bmlt_fargate" {
  zone_id = data.aws_route53_zone.bmltenabled.id
  name    = "tomato.${data.aws_route53_zone.bmltenabled.name}"
  type    = "A"

  alias {
    name                   = aws_alb.tomato.dns_name
    zone_id                = aws_alb.tomato.zone_id
    evaluate_target_health = true
  }
}
