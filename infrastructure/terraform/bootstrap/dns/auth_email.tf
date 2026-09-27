# Shared Resend authentication domain for staging and production.
# Keep these records in the authoritative DNS state, not in both app states.
import {
  to = aws_route53_record.login_email_dkim
  id = "Z049652226HBJOQNSBONC_resend._domainkey.login.stem-cogent.com_TXT"
}

import {
  to = aws_route53_record.email_dmarc
  id = "Z049652226HBJOQNSBONC__dmarc.stem-cogent.com_TXT"
}

resource "aws_route53_record" "login_email_dkim" {
  zone_id = aws_route53_zone.public.zone_id
  name    = "resend._domainkey.login.${var.domain_name}"
  type    = "TXT"
  ttl     = 300
  records = ["p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDinzcETyxlTH+bfFjUtV9waMwTd8bsuHbEeaAUBVJ5lvrLN3svh0R55mbI4BvM9Ur3qI11ao1i4UrpJ0asPTum+bPrJXpDcEM6Jq7qggAfCdyfSIBUwqAhaY/o6epL+DgaJGXp4h1tZfd5iAmTGjY2JM4MdUtP1DDlzwQRvhJYTQIDAQAB"]
}

resource "aws_route53_record" "email_dmarc" {
  zone_id = aws_route53_zone.public.zone_id
  name    = "_dmarc.${var.domain_name}"
  type    = "TXT"
  ttl     = 300
  records = ["v=DMARC1; p=none;"]
}

import {
  to = aws_route53_record.login_email_send
  id = "Z049652226HBJOQNSBONC_send.login.stem-cogent.com_MX"
}

import {
  to = aws_route53_record.login_email_return_path
  id = "Z049652226HBJOQNSBONC_rsend.login.stem-cogent.com_CNAME"
}

resource "aws_route53_record" "login_email_send" {
  zone_id = aws_route53_zone.public.zone_id
  name    = "send.login.${var.domain_name}"
  type    = "MX"
  ttl     = 300
  records = ["10 feedback-smtp.eu-west-1.amazonses.com"]
}

resource "aws_route53_record" "login_email_return_path" {
  zone_id = aws_route53_zone.public.zone_id
  name    = "rsend.login.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300
  records = ["send.forge.rmta.net"]
}

import {
  to = aws_route53_record.login_email_spf
  id = "Z049652226HBJOQNSBONC_send.login.stem-cogent.com_TXT"
}

resource "aws_route53_record" "login_email_spf" {
  zone_id = aws_route53_zone.public.zone_id
  name    = "send.login.${var.domain_name}"
  type    = "TXT"
  ttl     = 300
  records = ["v=spf1 include:amazonses.com ~all"]
}
