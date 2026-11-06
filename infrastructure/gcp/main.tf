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

# --- Durable delivery: Cloud Pub/Sub inbound queue ---
# User messages are published here by the control plane and consumed by the
# dispatcher, which validates the user/sandbox pairing and delivers to the pod.
# See system_design/12_durable_delivery.md.

variable "controlplane_service_account" {
  type        = string
  description = "Email of the service account the control plane (Cloud Run) runs as; granted publish on the inbound topic. Empty skips the grant."
  default     = ""
}

resource "google_project_service" "pubsub_api" {
  service            = "pubsub.googleapis.com"
  disable_on_destroy = false
}

data "google_project" "current" {}

# Messages that exhausted their delivery attempts land here for inspection/replay.
resource "google_pubsub_topic" "user_messages_dlq" {
  name       = "user-messages-dlq"
  depends_on = [google_project_service.pubsub_api]
}

resource "google_pubsub_subscription" "user_messages_dlq_inspect" {
  name                       = "user-messages-dlq-inspect"
  topic                      = google_pubsub_topic.user_messages_dlq.id
  message_retention_duration = "604800s" # 7 days
  ack_deadline_seconds       = 30
}

resource "google_pubsub_topic" "user_messages" {
  name                       = "user-messages"
  message_retention_duration = "86400s" # topic-level retention enables replay
  depends_on                 = [google_project_service.pubsub_api]
}

resource "google_pubsub_subscription" "user_messages_dispatcher" {
  name  = "user-messages-dispatcher"
  topic = google_pubsub_topic.user_messages.id

  # Ordering key = sandbox name, so one sandbox sees its messages in send order.
  enable_message_ordering = true
  # A sandbox accepting a message is quick (it answers 202 once queued), so a short
  # deadline is enough; the agent turn itself runs after the ack.
  ack_deadline_seconds       = 30
  message_retention_duration = "86400s"

  retry_policy {
    minimum_backoff = "2s"
    maximum_backoff = "60s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.user_messages_dlq.id
    max_delivery_attempts = 10
  }
}

resource "google_service_account" "dispatcher_sa" {
  account_id   = "ostrich-dispatcher"
  display_name = "Ostrich Dispatcher"
}

resource "google_pubsub_subscription_iam_member" "dispatcher_subscriber" {
  subscription = google_pubsub_subscription.user_messages_dispatcher.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_service_account.dispatcher_sa.email}"
}

resource "google_service_account_iam_binding" "dispatcher_workload_identity" {
  service_account_id = google_service_account.dispatcher_sa.name
  role               = "roles/iam.workloadIdentityUser"
  members            = ["serviceAccount:${var.project_id}.svc.id.goog[dispatcher-system/ostrich-dispatcher]"]
  depends_on         = [google_container_cluster.primary]
}

resource "google_pubsub_topic_iam_member" "controlplane_publisher" {
  count  = var.controlplane_service_account == "" ? 0 : 1
  topic  = google_pubsub_topic.user_messages.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${var.controlplane_service_account}"
}

# Pub/Sub's own service agent forwards exhausted messages to the DLQ topic and
# must be able to ack them off the source subscription.
resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  topic  = google_pubsub_topic.user_messages_dlq.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_pubsub_subscription_iam_member" "dlq_source_subscriber" {
  subscription = google_pubsub_subscription.user_messages_dispatcher.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
