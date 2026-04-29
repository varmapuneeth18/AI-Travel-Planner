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
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

resource "google_storage_bucket" "logs" {
  name                        = "${var.project_id}-travel-planner-logs"
  location                    = var.region
  uniform_bucket_level_access = true
}

resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

resource "google_cloud_run_v2_service" "api" {
  name     = "travel-planner-api"
  location = var.region

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      image = "gcr.io/${var.project_id}/travel-planner-api"
      env {
        name  = "LOGS_DIR"
        value = "/app/logs"
      }
      env {
        name  = "ENABLE_RAG"
        value = "true"
      }
    }
  }
}
