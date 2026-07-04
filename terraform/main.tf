terraform {
  required_version = ">= 1.3.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ==============================================================================
# 1. ARTIFACT REGISTRY
# ==============================================================================
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "ai-sre-demo-repo"
  description   = "Docker repository for AI SRE Agent and Payment Service"
  format        = "DOCKER"
}

# ==============================================================================
# 2. SERVICE ACCOUNTS & IAM
# ==============================================================================

# Service Account for Sample Payment Service
resource "google_service_account" "payment_service_sa" {
  account_id   = "payment-service-sa"
  display_name = "Service Account for Payment Service"
}

# Service Account for AI SRE Agent
resource "google_service_account" "sre_agent_sa" {
  account_id   = "ai-sre-agent-sa"
  display_name = "Service Account for AI SRE Agent"
}

# IAM permissions for the AI SRE Agent
# SRE Agent needs to view monitoring metrics
resource "google_project_iam_member" "agent_monitoring_viewer" {
  project = var.project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.sre_agent_sa.email}"
}

# SRE Agent needs to read Cloud Logging logs
resource "google_project_iam_member" "agent_logging_viewer" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.sre_agent_sa.email}"
}

# SRE Agent needs to view and manage Cloud Run revisions for rollback
resource "google_project_iam_member" "agent_run_admin" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.sre_agent_sa.email}"
}

# SRE Agent needs permission to act as the Service Account of the Cloud Run revision during deploy/update
resource "google_service_account_iam_member" "agent_act_as" {
  service_account_id = google_service_account.payment_service_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.sre_agent_sa.email}"
}

# ==============================================================================
# 3. PUB/SUB & EVENTARC (Alert Ingestion)
# ==============================================================================

# Pub/Sub Topic for monitoring alerts
resource "google_pubsub_topic" "alerts_topic" {
  name = "sre-alerts-topic"
}

# Eventarc trigger routing alerts to the AI SRE agent
resource "google_eventarc_trigger" "alert_trigger" {
  name     = "sre-alert-trigger"
  location = var.region
  
  matching_criteria {
    attribute = "type"
    value     = "google.cloud.pubsub.topic.v1.messagePublished"
  }
  
  destination {
    cloud_run_service {
      service = google_cloud_run_v2_service.sre_agent_service.name
      path    = "/api/trigger_incident"
      region  = var.region
    }
  }

  service_account = google_service_account.sre_agent_sa.email

  depends_on = [
    google_project_iam_member.agent_run_admin
  ]
}

# ==============================================================================
# 4. CLOUD MONITORING ALERT POLICY
# ==============================================================================
resource "google_monitoring_alert_policy" "http_500_alert" {
  display_name = "High HTTP 500 Error Rate on Payment Service"
  combiner     = "OR"
  conditions {
    display_name = "Error Rate Condition"
    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${google_cloud_run_v2_service.payment_service.name}\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class = \"5xx\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5.0 # Trigger if 5xx request count > 5
      
      trigger {
        count = 1
      }
      
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.pubsub_channel.name
  ]
}

resource "google_monitoring_notification_channel" "pubsub_channel" {
  display_name = "Pub/Sub SRE Alert Channel"
  type         = "pubsub"
  labels = {
    topic = google_pubsub_topic.alerts_topic.id
  }
}

# ==============================================================================
# 5. CLOUD RUN SERVICES
# ==============================================================================

# 5.1 Payment Service
resource "google_cloud_run_v2_service" "payment_service" {
  name                = "sample-payment-service"
  location            = var.region
  deletion_protection = false

  template {
    service_account = google_service_account.payment_service_sa.email
    containers {
      image = "gcr.io/cloudrun/hello"
      
      ports {
        container_port = 8080
      }
      
      env {
        name  = "ENABLE_BAD_CONFIG"
        value = "false"
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }
}

# Allow public unauthenticated access to the Payment Service (for demo/load testing)
resource "google_cloud_run_v2_service_iam_member" "payment_service_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.payment_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# 5.2 AI SRE Agent Dashboard Service
resource "google_cloud_run_v2_service" "sre_agent_service" {
  name                = "ai-sre-agent-dashboard"
  location            = var.region
  deletion_protection = false

  template {
    service_account = google_service_account.sre_agent_sa.email
    containers {
      image = "gcr.io/cloudrun/hello"
      
      ports {
        container_port = 8080
      }
      
      env {
        name  = "DEMO_MODE"
        value = "true"
      }
      env {
        name  = "GEMINI_MODEL"
        value = var.gemini_model
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }
}

# Allow public access to the Dashboard UI
resource "google_cloud_run_v2_service_iam_member" "agent_service_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.sre_agent_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
