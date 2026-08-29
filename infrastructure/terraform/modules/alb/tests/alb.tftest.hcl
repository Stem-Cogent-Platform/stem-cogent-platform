mock_provider "aws" {
  mock_data "aws_partition" {
    defaults = {
      partition = "aws"
    }
  }

  mock_data "aws_route53_zone" {
    defaults = {
      zone_id = "Z0123456789ABCDEF"
      name    = "stem-cogent.com."
    }
  }

  mock_data "aws_iam_policy_document" {
    defaults = {
      json = jsonencode({ Version = "2012-10-17", Statement = [] })
    }
  }

  mock_resource "aws_acm_certificate" {
    defaults = {
      arn = "arn:aws:acm:eu-west-1:123456789012:certificate/01234567-89ab-cdef-0123-456789abcdef"
      domain_validation_options = [
        {
          domain_name           = "app.staging.stem-cogent.com"
          resource_record_name  = "_frontend.stem-cogent.com"
          resource_record_type  = "CNAME"
          resource_record_value = "_frontend.acm-validations.aws"
        },
        {
          domain_name           = "api.staging.stem-cogent.com"
          resource_record_name  = "_api.stem-cogent.com"
          resource_record_type  = "CNAME"
          resource_record_value = "_api.acm-validations.aws"
        },
        {
          domain_name           = "stem-cogent.com"
          resource_record_name  = "_apex.stem-cogent.com"
          resource_record_type  = "CNAME"
          resource_record_value = "_apex.acm-validations.aws"
        },
        {
          domain_name           = "www.stem-cogent.com"
          resource_record_name  = "_www.stem-cogent.com"
          resource_record_type  = "CNAME"
          resource_record_value = "_www.acm-validations.aws"
        },
      ]
    }
  }

  mock_resource "aws_acm_certificate_validation" {
    defaults = {
      certificate_arn = "arn:aws:acm:eu-west-1:123456789012:certificate/01234567-89ab-cdef-0123-456789abcdef"
    }
  }

  mock_resource "aws_lb" {
    defaults = {
      arn      = "arn:aws:elasticloadbalancing:eu-west-1:123456789012:loadbalancer/app/sc-alb-staging/abc"
      dns_name = "sc-alb-staging.eu-west-1.elb.amazonaws.com"
      zone_id  = "Z32O12XQLNTSW2"
    }
  }
}

mock_provider "aws" {
  alias = "dns"

  mock_data "aws_route53_zone" {
    defaults = {
      zone_id = "Z0123456789ABCDEF"
      name    = "stem-cogent.com."
    }
  }
}

variables {
  aws_account_id    = "123456789012"
  environment       = "staging"
  vpc_id            = "vpc-0123456789abcdef0"
  public_subnet_ids = ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"]
  security_group_id = "sg-0123456789abcdef0"
  hosted_zone_name  = "stem-cogent.com"
  api_hostname      = "api.staging.stem-cogent.com"
  frontend_hostname = "app.staging.stem-cogent.com"
  frontend_redirect_hostnames = [
    "stem-cogent.com",
    "www.stem-cogent.com",
  ]
}

run "creates_tls_only_application_routing" {
  command = plan

  assert {
    condition = (
      one(aws_lb_listener.http.default_action).type == "redirect" &&
      one(one(aws_lb_listener.http.default_action).redirect).protocol == "HTTPS" &&
      one(one(aws_lb_listener.http.default_action).redirect).status_code == "HTTP_301"
    )
    error_message = "The plaintext listener must only redirect to HTTPS."
  }

  assert {
    condition = (
      aws_lb_listener.https.protocol == "HTTPS" &&
      aws_lb_listener.https.ssl_policy == "ELBSecurityPolicy-TLS13-1-2-2021-06" &&
      one(aws_lb_listener.https.default_action).type == "fixed-response"
    )
    error_message = "The TLS listener must use the approved policy and reject unknown hosts."
  }

  assert {
    condition = (
      one(one(one(aws_lb_listener_rule.api.condition).host_header).values) == "api.staging.stem-cogent.com" &&
      one(one(one(aws_lb_listener_rule.frontend.condition).host_header).values) == "app.staging.stem-cogent.com"
    )
    error_message = "Only the canonical API and frontend hostnames may forward to containers."
  }

  assert {
    condition = (
      toset(aws_acm_certificate.this.subject_alternative_names) ==
      toset(["api.staging.stem-cogent.com", "stem-cogent.com", "www.stem-cogent.com"]) &&
      toset(keys(aws_route53_record.frontend_redirect)) ==
      toset(["stem-cogent.com", "www.stem-cogent.com"]) &&
      aws_route53_record.frontend.allow_overwrite &&
      alltrue([for record in aws_route53_record.frontend_redirect : record.allow_overwrite])
    )
    error_message = "Frontend aliases must be covered by TLS and safely reconcile canonical-host migrations."
  }

  assert {
    condition = (
      toset(one(one(one(aws_lb_listener_rule.frontend_redirect).condition).host_header).values) ==
      toset(["stem-cogent.com", "www.stem-cogent.com"]) &&
      one(one(one(aws_lb_listener_rule.frontend_redirect).action).redirect).host ==
      "app.staging.stem-cogent.com" &&
      one(one(one(aws_lb_listener_rule.frontend_redirect).action).redirect).status_code ==
      "HTTP_301"
    )
    error_message = "Frontend aliases must permanently redirect to the canonical application hostname."
  }
}

run "creates_healthy_ip_target_groups" {
  command = plan

  assert {
    condition = (
      aws_lb_target_group.api.target_type == "ip" &&
      one(aws_lb_target_group.api.health_check).path == "/health/live" &&
      aws_lb_target_group.frontend.target_type == "ip" &&
      one(aws_lb_target_group.frontend.health_check).path == "/"
    )
    error_message = "Fargate target groups must use IP targets and explicit health-check paths."
  }
}

run "protects_and_observes_the_public_edge" {
  command = plan

  assert {
    condition     = length(aws_wafv2_web_acl.this.rule) == 5
    error_message = "The ALB must have four AWS managed protections and one rate-limit rule."
  }

  assert {
    condition = (
      one(aws_lb.this.access_logs).enabled &&
      aws_s3_bucket_public_access_block.access_logs.restrict_public_buckets
    )
    error_message = "ALB access logging must be enabled to a fully private bucket."
  }
}
