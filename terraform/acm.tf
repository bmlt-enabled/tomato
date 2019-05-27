resource "aws_acm_certificate" "tomato_bmltenabled" {
  domain_name       = "tomato.bmltenabled.org"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "tomato_bmltenabled" {
  certificate_arn         = "${aws_acm_certificate.tomato_bmltenabled.arn}"
  validation_record_fqdns = ["${aws_route53_record.tomato_bmltenabled_validation.fqdn}"]
}

data "aws_acm_certificate" "tomato_na_bmlt" {
  domain      = "tomato.na-bmlt.org"
  statuses    = ["ISSUED"]
  most_recent = true
}
