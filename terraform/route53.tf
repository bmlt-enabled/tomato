resource "aws_route53_record" "tomato_bmltenabled" {
  zone_id         = data.aws_route53_zone.tomato_bmltenabled_org.id
  name            = data.aws_route53_zone.tomato_bmltenabled_org.name
  type            = "A"
  allow_overwrite = true

  alias {
    name                   = data.aws_lb.main.dns_name
    zone_id                = data.aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "tomato_na-bmlt_org" {
  zone_id         = data.aws_route53_zone.na-bmlt_org.id
  name            = "tomato.${data.aws_route53_zone.na-bmlt_org.name}"
  type            = "A"
  allow_overwrite = true

  alias {
    name                   = data.aws_lb.main.dns_name
    zone_id                = data.aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "aggregator_bmltenabled" {
  zone_id         = data.aws_route53_zone.aggregator_bmltenabled_org.id
  name            = data.aws_route53_zone.aggregator_bmltenabled_org.name
  type            = "A"
  allow_overwrite = true

  alias {
    name                   = data.aws_lb.main.dns_name
    zone_id                = data.aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "aggregator_na-bmlt_org" {
  zone_id         = data.aws_route53_zone.na-bmlt_org.id
  name            = "aggregator.${data.aws_route53_zone.na-bmlt_org.name}"
  type            = "A"
  allow_overwrite = true

  alias {
    name                   = data.aws_lb.main.dns_name
    zone_id                = data.aws_lb.main.zone_id
    evaluate_target_health = true
  }
}
