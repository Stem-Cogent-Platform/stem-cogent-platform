resource "aws_acm_certificate" "this" {
  domain_name               = var.frontend_hostname
  subject_alternative_names = [var.api_hostname]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-public-${var.environment}"
  })
}

resource "aws_route53_record" "certificate_validation" {
  provider = aws.dns

  # Instance keys come from input hostnames, not apply-time ACM attributes, so
  # a fresh environment can produce one complete plan without -target passes.
  for_each = toset([var.api_hostname, var.frontend_hostname])

  allow_overwrite = true
  zone_id         = data.aws_route53_zone.public.zone_id
  name = one([
    for option in aws_acm_certificate.this.domain_validation_options :
    option.resource_record_name if option.domain_name == each.key
  ])
  type = one([
    for option in aws_acm_certificate.this.domain_validation_options :
    option.resource_record_type if option.domain_name == each.key
  ])
  ttl = 60
  records = [one([
    for option in aws_acm_certificate.this.domain_validation_options :
    option.resource_record_value if option.domain_name == each.key
  ])]
}

resource "aws_acm_certificate_validation" "this" {
  certificate_arn = aws_acm_certificate.this.arn
  validation_record_fqdns = [
    for record in aws_route53_record.certificate_validation : record.fqdn
  ]
}
