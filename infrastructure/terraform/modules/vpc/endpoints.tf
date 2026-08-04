data "aws_region" "current" {}

locals {
  # SC-DOC-008 Section 7.4 expands the logical ECR and CloudWatch entries into
  # their actual AWS PrivateLink services. Kinesis Streams is required by
  # SC-DOC-004 Section 13.2 for pipeline trend and analytics events.
  interface_endpoint_services = {
    sqs             = "com.amazonaws.${data.aws_region.current.name}.sqs"
    secretsmanager  = "com.amazonaws.${data.aws_region.current.name}.secretsmanager"
    kms             = "com.amazonaws.${data.aws_region.current.name}.kms"
    ecr_api         = "com.amazonaws.${data.aws_region.current.name}.ecr.api"
    ecr_dkr         = "com.amazonaws.${data.aws_region.current.name}.ecr.dkr"
    logs            = "com.amazonaws.${data.aws_region.current.name}.logs"
    monitoring      = "com.amazonaws.${data.aws_region.current.name}.monitoring"
    xray            = "com.amazonaws.${data.aws_region.current.name}.xray"
    kinesis_streams = "com.amazonaws.${data.aws_region.current.name}.kinesis-streams"
    sns             = "com.amazonaws.${data.aws_region.current.name}.sns"
  }
}

resource "aws_security_group" "vpc_endpoints" {
  name                   = "${var.resource_prefix}-vpc-endpoints-sg-${var.environment}"
  description            = "Accepts private HTTPS traffic from ECS application subnets to AWS interface endpoints."
  vpc_id                 = aws_vpc.this.id
  revoke_rules_on_delete = true

  tags = merge(local.common_tags, {
    Name  = "${var.resource_prefix}-vpc-endpoints-sg-${var.environment}"
    Layer = "network"
  })
}

resource "aws_vpc_security_group_ingress_rule" "vpc_endpoints_https" {
  for_each = toset(var.private_app_subnet_cidrs)

  security_group_id = aws_security_group.vpc_endpoints.id

  description = "TLS from the private application subnet ${each.value}."
  cidr_ipv4   = each.value
  from_port   = 443
  to_port     = 443
  ip_protocol = "tcp"

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-endpoint-https-${replace(each.value, "/", "-")}-${var.environment}"
  })
}

resource "aws_vpc_endpoint" "interface" {
  for_each = local.interface_endpoint_services

  vpc_id              = aws_vpc.this.id
  service_name        = each.value
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = [for availability_zone in var.availability_zones : aws_subnet.private_app[availability_zone].id]
  security_group_ids  = [aws_security_group.vpc_endpoints.id]

  tags = merge(local.common_tags, {
    Name    = "${var.resource_prefix}-${replace(each.key, "_", "-")}-endpoint-${var.environment}"
    Service = each.key
  })
}

# S3 is a gateway endpoint. Associate every private route table so private-app
# workloads and future private-data recovery/maintenance workflows never need
# NAT or an Internet Gateway to reach S3.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids = concat(
    [for availability_zone in var.availability_zones : aws_route_table.private_app[availability_zone].id],
    [for availability_zone in var.availability_zones : aws_route_table.private_data[availability_zone].id],
  )

  tags = merge(local.common_tags, {
    Name    = "${var.resource_prefix}-s3-endpoint-${var.environment}"
    Service = "s3"
  })
}
