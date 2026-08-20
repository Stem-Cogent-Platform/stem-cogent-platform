terraform {
  required_version = ">= 1.11.0, < 2.0.0"

  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = ">= 5.100.0, < 6.0.0"
      configuration_aliases = [aws.dns]
    }
  }
}
