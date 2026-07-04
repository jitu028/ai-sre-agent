output "artifact_registry_repo" {
  value       = google_artifact_registry_repository.repo.id
  description = "Artifact Registry Repository URL for container builds."
}

output "payment_service_url" {
  value       = google_cloud_run_v2_service.payment_service.uri
  description = "Public URL of the Sample Payment Service."
}

output "sre_agent_dashboard_url" {
  value       = google_cloud_run_v2_service.sre_agent_service.uri
  description = "Public URL of the AI SRE Agent Dashboard Operations Center."
}

output "pubsub_alert_topic" {
  value       = google_pubsub_topic.alerts_topic.id
  description = "Pub/Sub alert ingestion topic ID."
}
