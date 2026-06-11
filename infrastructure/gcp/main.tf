# GCP Infrastructure Configuration

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  type        = string
  description = "The GCP project ID to deploy to"
}

variable "region" {
  type        = string
  description = "The default GCP region for resources"
  default     = "us-central1"
}

# Example placeholder resource: Google Cloud Run service
# resource "google_cloud_run_service" "ostrich_service" {
#   name     = "ostrich-app"
#   location = var.region
#
#   template {
#     spec {
#       containers {
#         image = "gcr.io/${var.project_id}/ostrich-app:latest"
#       }
#     }
#   }
# }
