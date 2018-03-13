data "aws_route53_zone" "jbraz" {
  name = "jbraz.com."
}

resource "aws_route53_record" "tomato" {
  zone_id = "${data.aws_route53_zone.jbraz.id}"
  name    = "tomato.${data.aws_route53_zone.jbraz.name}"
  type    = "CNAME"
  ttl     = "300"
  records = ["${aws_alb.tomato.dns_name}"]
}
