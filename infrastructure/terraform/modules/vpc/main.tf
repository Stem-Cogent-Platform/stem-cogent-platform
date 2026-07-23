locals {
  networks_by_az = {
    for index, availability_zone in var.availability_zones : availability_zone => {
      label             = substr(availability_zone, -1, 1)
      public_cidr       = var.public_subnet_cidrs[index]
      private_app_cidr  = var.private_app_subnet_cidrs[index]
      private_data_cidr = var.private_data_subnet_cidrs[index]
    }
  }

  common_tags = merge(
    {
      Environment = var.environment
      ManagedBy   = "terraform"
      Project     = var.project_name
    },
    var.tags
  )

  all_subnet_cidrs = concat(
    var.public_subnet_cidrs,
    var.private_app_subnet_cidrs,
    var.private_data_subnet_cidrs
  )
}

check "subnet_cidrs_are_unique" {
  assert {
    condition     = length(distinct(local.all_subnet_cidrs)) == length(local.all_subnet_cidrs)
    error_message = "Every public, private-app, and private-data subnet must use a unique CIDR block."
  }
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  instance_tenancy     = "default"

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-vpc-${var.environment}"
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-igw-${var.environment}"
  })
}

resource "aws_subnet" "public" {
  for_each = local.networks_by_az

  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.key
  cidr_block              = each.value.public_cidr
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-subnet-public-${each.value.label}-${var.environment}"
    Tier = "public"
  })
}

resource "aws_subnet" "private_app" {
  for_each = local.networks_by_az

  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.key
  cidr_block              = each.value.private_app_cidr
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-subnet-private-app-${each.value.label}-${var.environment}"
    Tier = "private-app"
  })
}

resource "aws_subnet" "private_data" {
  for_each = local.networks_by_az

  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.key
  cidr_block              = each.value.private_data_cidr
  map_public_ip_on_launch = false

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-subnet-private-data-${each.value.label}-${var.environment}"
    Tier = "private-data"
  })
}

resource "aws_eip" "nat" {
  for_each = local.networks_by_az

  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-nat-eip-${each.value.label}-${var.environment}"
  })
}

resource "aws_nat_gateway" "this" {
  for_each = local.networks_by_az

  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = aws_subnet.public[each.key].id

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-nat-${each.value.label}-${var.environment}"
  })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-rt-public-${var.environment}"
    Tier = "public"
  })
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  for_each = local.networks_by_az

  subnet_id      = aws_subnet.public[each.key].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private_app" {
  for_each = local.networks_by_az

  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-rt-private-app-${each.value.label}-${var.environment}"
    Tier = "private-app"
  })
}

resource "aws_route" "private_app_internet" {
  for_each = local.networks_by_az

  route_table_id         = aws_route_table.private_app[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this[each.key].id
}

resource "aws_route_table_association" "private_app" {
  for_each = local.networks_by_az

  subnet_id      = aws_subnet.private_app[each.key].id
  route_table_id = aws_route_table.private_app[each.key].id
}

resource "aws_route_table" "private_data" {
  for_each = local.networks_by_az

  vpc_id = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-rt-private-data-${each.value.label}-${var.environment}"
    Tier = "private-data"
  })
}

resource "aws_route_table_association" "private_data" {
  for_each = local.networks_by_az

  subnet_id      = aws_subnet.private_data[each.key].id
  route_table_id = aws_route_table.private_data[each.key].id
}
