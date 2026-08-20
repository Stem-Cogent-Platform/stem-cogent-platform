mock_provider "aws" {
  mock_data "aws_region" {
    defaults = {
      name = "eu-west-1"
    }
  }

  mock_data "aws_iam_policy_document" {
    defaults = {
      json = jsonencode({
        Version   = "2012-10-17"
        Statement = []
      })
    }
  }
}

variables {
  environment      = "staging"
  enable_flow_logs = false
}

run "creates_complete_private_aws_service_access" {
  # A mocked apply is required because subnet and route-table IDs are computed
  # values; no real AWS API calls are made by the mock provider.
  command = apply

  assert {
    condition     = length(aws_vpc_endpoint.interface) == 10
    error_message = "All ten required AWS PrivateLink interface services must have endpoints."
  }

  assert {
    condition = toset([for endpoint in aws_vpc_endpoint.interface : endpoint.service_name]) == toset([
      "com.amazonaws.eu-west-1.sqs",
      "com.amazonaws.eu-west-1.secretsmanager",
      "com.amazonaws.eu-west-1.kms",
      "com.amazonaws.eu-west-1.ecr.api",
      "com.amazonaws.eu-west-1.ecr.dkr",
      "com.amazonaws.eu-west-1.logs",
      "com.amazonaws.eu-west-1.monitoring",
      "com.amazonaws.eu-west-1.xray",
      "com.amazonaws.eu-west-1.kinesis-streams",
      "com.amazonaws.eu-west-1.sns",
    ])
    error_message = "The interface endpoint service set must match the traced architecture requirements."
  }

  assert {
    condition     = alltrue([for endpoint in aws_vpc_endpoint.interface : endpoint.vpc_endpoint_type == "Interface" && endpoint.private_dns_enabled])
    error_message = "Every PrivateLink service must use an interface endpoint with private DNS."
  }

  assert {
    condition     = alltrue([for endpoint in aws_vpc_endpoint.interface : length(endpoint.subnet_ids) == 2])
    error_message = "Every interface endpoint must be highly available across both private-app subnets."
  }

  assert {
    condition     = aws_vpc_endpoint.s3.vpc_endpoint_type == "Gateway"
    error_message = "S3 must use a gateway endpoint."
  }

  assert {
    condition     = length(aws_vpc_endpoint.s3.route_table_ids) == 4
    error_message = "The S3 endpoint must update both private-app and both private-data route tables."
  }

  assert {
    condition     = length(aws_vpc_security_group_ingress_rule.vpc_endpoints_https) == 2
    error_message = "Endpoint HTTPS ingress must be limited to the two private-app CIDRs."
  }
}
