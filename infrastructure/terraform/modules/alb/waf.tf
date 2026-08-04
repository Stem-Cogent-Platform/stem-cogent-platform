locals {
  managed_waf_rules = {
    common = {
      name     = "AWSManagedRulesCommonRuleSet"
      priority = 10
    }
    known_bad_inputs = {
      name     = "AWSManagedRulesKnownBadInputsRuleSet"
      priority = 20
    }
    sql_injection = {
      name     = "AWSManagedRulesSQLiRuleSet"
      priority = 30
    }
    ip_reputation = {
      name     = "AWSManagedRulesAmazonIpReputationList"
      priority = 40
    }
  }
}

resource "aws_wafv2_web_acl" "this" {
  name        = "${var.resource_prefix}-alb-${var.environment}"
  description = "Managed threat protection and per-IP rate limiting for the Stem Cogent public ALB."
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  dynamic "rule" {
    for_each = local.managed_waf_rules

    content {
      name     = rule.value.name
      priority = rule.value.priority

      override_action {
        none {}
      }

      statement {
        managed_rule_group_statement {
          name        = rule.value.name
          vendor_name = "AWS"
        }
      }

      visibility_config {
        cloudwatch_metrics_enabled = true
        metric_name                = "${var.resource_prefix}-${rule.key}-${var.environment}"
        sampled_requests_enabled   = true
      }
    }
  }

  rule {
    name     = "RateLimitPerIp"
    priority = 50

    action {
      block {}
    }

    statement {
      rate_based_statement {
        aggregate_key_type = "IP"
        limit              = 2000
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.resource_prefix}-rate-limit-${var.environment}"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.resource_prefix}-alb-web-acl-${var.environment}"
    sampled_requests_enabled   = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-alb-${var.environment}"
  })
}

resource "aws_wafv2_web_acl_association" "this" {
  resource_arn = aws_lb.this.arn
  web_acl_arn  = aws_wafv2_web_acl.this.arn
}
