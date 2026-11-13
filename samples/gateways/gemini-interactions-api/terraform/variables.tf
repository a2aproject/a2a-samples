variable "project_id" {
  description = "GCP project hosting Cloud Run, the bucket, and Artifact Registry."
  type        = string
}

variable "region" {
  description = "Region for Cloud Run and Artifact Registry."
  type        = string
  default     = "us-central1"
}

variable "vertex_endpoint" {
  description = "Vertex Interactions API endpoint."
  type        = string
  default     = "https://aiplatform.googleapis.com"
}

variable "vertex_project_id" {
  description = "Project hosting the Vertex agent. Defaults to project_id."
  type        = string
  default     = null
}

variable "vertex_project_number" {
  description = "Project number for vertex_project_id (P4SA grants). Defaults to project_id's number."
  type        = string
  default     = null
}

variable "extra_vertex_p4sa_suffixes" {
  description = "Additional gcp-sa-* suffixes that need bucket and impersonation access (e.g. pre-prod P4SAs)."
  type        = list(string)
  default     = []
}

variable "service_name" {
  description = "Cloud Run service name."
  type        = string
  default     = "a2a-bridge"
}

variable "env_scope" {
  description = "Sandbox reuse scope: 'context' (per chat) or 'user'."
  type        = string
  default     = "context"
}

variable "firestore_database" {
  description = "Firestore database id for session continuity. Empty disables persistence (in-memory store)."
  type        = string
  default     = "a2a-bridge"
}

variable "firestore_location" {
  description = "Firestore database location id."
  type        = string
  default     = "nam5"
}

variable "enable_artifact_export" {
  description = "Grant signBlob/impersonation roles and set UPLOAD_BUCKET so the bridge can mint signed upload/download URLs for sandbox file egress."
  type        = bool
  default     = false
}

