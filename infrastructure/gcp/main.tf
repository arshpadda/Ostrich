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

# Enable required GCP APIs
resource "google_project_service" "artifactregistry_api" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "container_api" {
  service            = "container.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "redis_api" {
  service            = "redis.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "compute_api" {
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

# Artifact Registry to store Docker images
resource "google_artifact_registry_repository" "ostrich_repo" {
  provider      = google
  location      = var.region
  repository_id = "ostrich-repo"
  description   = "Docker repository for Ostrich images"
  format        = "DOCKER"

  depends_on = [
    google_project_service.artifactregistry_api
  ]
}

# --- Phase 2: Networking & Redis ---

resource "google_project_service" "servicenetworking_api" {
  service            = "servicenetworking.googleapis.com"
  disable_on_destroy = false
}

# VPC Network
resource "google_compute_network" "main_vpc" {
  name                    = "ostrich-vpc"
  auto_create_subnetworks = true
  depends_on = [
    google_project_service.compute_api
  ]
}

# Allocate an IP range for Private Services Access
resource "google_compute_global_address" "private_ip_alloc" {
  name          = "ostrich-redis-peering-alloc"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main_vpc.id
}

# Create a private connection
resource "google_service_networking_connection" "default" {
  network                 = google_compute_network.main_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_alloc.name]

  depends_on = [
    google_project_service.servicenetworking_api
  ]
}

# Memorystore for Redis
resource "google_redis_instance" "cache" {
  name           = "ostrich-redis"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region

  authorized_network = google_compute_network.main_vpc.id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  depends_on = [
    google_service_networking_connection.default,
    google_project_service.redis_api
  ]
}

# --- Phase 3: GKE & Workload Identity ---

# GKE Autopilot Cluster
resource "google_container_cluster" "primary" {
  name     = "ostrich-cluster"
  location = var.region

  # Enable Autopilot
  enable_autopilot = true

  network = google_compute_network.main_vpc.id

  ip_allocation_policy {
  }
}

# GCP Service Account for the Sandbox Agent
resource "google_service_account" "sandbox_sa" {
  account_id   = "sandbox-agent-sa"
  display_name = "Sandbox Agent Service Account"
}

# Give the Sandbox SA permissions to upload to GCS
resource "google_storage_bucket_iam_member" "sandbox_gcs_access" {
  bucket = "ostrich-agent-workspaces"
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.sandbox_sa.email}"
}

# Workload Identity Binding
resource "google_service_account_iam_binding" "workload_identity_binding" {
  service_account_id = google_service_account.sandbox_sa.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[sandbox-chat/sandbox-agent-sa]",
  ]
  depends_on = [google_container_cluster.primary]
}
