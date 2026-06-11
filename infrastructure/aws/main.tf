# AWS Infrastructure Configuration

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type        = string
  description = "The default AWS region for resources"
  default     = "us-east-1"
}

# Example placeholder resource: AWS ECS service / Runner
# resource "aws_ecs_cluster" "ostrich_cluster" {
#   name = "ostrich-cluster"
# }
