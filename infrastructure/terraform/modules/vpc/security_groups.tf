resource "aws_security_group" "alb" {
  name                   = "${var.resource_prefix}-alb-sg-${var.environment}"
  description            = "Controls public ingress and service egress for the application load balancer."
  vpc_id                 = aws_vpc.this.id
  revoke_rules_on_delete = true

  tags = merge(local.common_tags, {
    Name  = "${var.resource_prefix}-alb-sg-${var.environment}"
    Layer = "edge"
  })
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id

  description = "Public HTTP accepted only for redirect to HTTPS."
  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 80
  to_port     = 80
  ip_protocol = "tcp"

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-alb-http-ingress-${var.environment}"
  })
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id

  description = "Public HTTPS application traffic."
  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 443
  to_port     = 443
  ip_protocol = "tcp"

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-alb-https-ingress-${var.environment}"
  })
}

resource "aws_security_group" "frontend_service" {
  name                   = "${var.resource_prefix}-frontend-service-sg-${var.environment}"
  description            = "Restricts frontend service traffic to the application load balancer."
  vpc_id                 = aws_vpc.this.id
  revoke_rules_on_delete = true

  tags = merge(local.common_tags, {
    Name  = "${var.resource_prefix}-frontend-service-sg-${var.environment}"
    Layer = "application"
  })
}

resource "aws_vpc_security_group_ingress_rule" "frontend_from_alb" {
  security_group_id = aws_security_group.frontend_service.id

  description                  = "Frontend container traffic from the application load balancer."
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 3000
  to_port                      = 3000
  ip_protocol                  = "tcp"

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-frontend-from-alb-${var.environment}"
  })
}

resource "aws_vpc_security_group_egress_rule" "alb_to_frontend" {
  security_group_id = aws_security_group.alb.id

  description                  = "Load balancer traffic to the frontend target group."
  referenced_security_group_id = aws_security_group.frontend_service.id
  from_port                    = 3000
  to_port                      = 3000
  ip_protocol                  = "tcp"

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-alb-to-frontend-${var.environment}"
  })
}

resource "aws_vpc_security_group_egress_rule" "frontend_https" {
  security_group_id = aws_security_group.frontend_service.id

  description = "HTTPS egress for AWS services and server-side application requests."
  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 443
  to_port     = 443
  ip_protocol = "tcp"

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-frontend-https-egress-${var.environment}"
  })
}

resource "aws_security_group" "api_service" {
  name                   = "${var.resource_prefix}-api-service-sg-${var.environment}"
  description            = "Restricts API service ingress to the application load balancer."
  vpc_id                 = aws_vpc.this.id
  revoke_rules_on_delete = true

  tags = merge(local.common_tags, {
    Name  = "${var.resource_prefix}-api-service-sg-${var.environment}"
    Layer = "application"
  })
}

resource "aws_vpc_security_group_ingress_rule" "api_from_alb" {
  security_group_id = aws_security_group.api_service.id

  description                  = "API container traffic from the application load balancer."
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-api-from-alb-${var.environment}"
  })
}

resource "aws_vpc_security_group_egress_rule" "alb_to_api" {
  security_group_id = aws_security_group.alb.id

  description                  = "Load balancer traffic to the API target group."
  referenced_security_group_id = aws_security_group.api_service.id
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-alb-to-api-${var.environment}"
  })
}

resource "aws_vpc_security_group_egress_rule" "api_tcp" {
  security_group_id = aws_security_group.api_service.id

  description = "Application egress to the data layer, AWS services, and external APIs."
  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 0
  to_port     = 65535
  ip_protocol = "tcp"

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-api-tcp-egress-${var.environment}"
  })
}

resource "aws_security_group" "data_layer" {
  name                   = "${var.resource_prefix}-data-layer-sg-${var.environment}"
  description            = "Restricts PostgreSQL and Redis ingress to the application layer."
  vpc_id                 = aws_vpc.this.id
  revoke_rules_on_delete = true

  tags = merge(local.common_tags, {
    Name  = "${var.resource_prefix}-data-layer-sg-${var.environment}"
    Layer = "data"
  })
}

resource "aws_vpc_security_group_ingress_rule" "data_postgresql_from_api" {
  security_group_id = aws_security_group.data_layer.id

  description                  = "PostgreSQL traffic from the API application layer."
  referenced_security_group_id = aws_security_group.api_service.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-postgresql-from-api-${var.environment}"
  })
}

resource "aws_vpc_security_group_ingress_rule" "data_redis_from_api" {
  security_group_id = aws_security_group.data_layer.id

  description                  = "Redis traffic from the API application layer."
  referenced_security_group_id = aws_security_group.api_service.id
  from_port                    = 6379
  to_port                      = 6379
  ip_protocol                  = "tcp"

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-redis-from-api-${var.environment}"
  })
}
