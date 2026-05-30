output "service_url" {
  description = "Cloud Run service URL."
  value       = google_cloud_run_v2_service.bridge.uri
}

output "artifacts_bucket" {
  description = "GCS bucket for agent template seed content and sandbox uploads."
  value       = google_storage_bucket.artifacts.name
}

output "runtime_service_account" {
  description = "Bridge runtime service account email."
  value       = google_service_account.runtime.email
}

output "firestore_database" {
  description = "Firestore database id holding session continuity state."
  value       = one(google_firestore_database.sessions[*].name)
}

