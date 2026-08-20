resource "aws_route53_record" "api" {
  provider = aws.dns

  zone_id = data.aws_route53_zone.public.zone_id
  name    = var.api_hostname
  type    = "A"

  alias {
    name                   = aws_lb.this.dns_name
    zone_id                = aws_lb.this.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "frontend" {
  provider = aws.dns

  zone_id = data.aws_route53_zone.public.zone_id
  name    = var.frontend_hostname
  type    = "A"

  alias {
    name                   = aws_lb.this.dns_name
    zone_id                = aws_lb.this.zone_id
    evaluate_target_health = true
  }
}
