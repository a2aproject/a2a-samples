locals {
  vertex_project_id     = coalesce(var.vertex_project_id, var.project_id)
  vertex_project_number = coalesce(var.vertex_project_number, data.google_project.this.number)
  vertex_p4sa           = "serviceAccount:service-${local.vertex_project_number}@gcp-sa-aiplatform.iam.gserviceaccount.com"
  extra_p4sas = {
    for s in var.extra_vertex_p4sa_suffixes :
    s => "serviceAccount:service-${local.vertex_project_number}@gcp-sa-${s}.iam.gserviceaccount.com"
  }
  firestore_enabled = var.firestore_database != ""
  required_apis = toset(concat(
    [
      "run.googleapis.com",
      "artifactregistry.googleapis.com",
      "aiplatform.googleapis.com",
      "discoveryengine.googleapis.com",
      "storage.googleapis.com",
      "cloudbuild.googleapis.com",
      "iam.googleapis.com",
      "iamcredentials.googleapis.com",
      "secretmanager.googleapis.com",
    ],
    local.firestore_enabled ? ["firestore.googleapis.com", "firebaserules.googleapis.com"] : [],
  ))
}

data "google_project" "this" {
  project_id = var.project_id
}

resource "google_project_service" "required" {
  for_each = local.required_apis

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "bridge" {
  project       = var.project_id
  location      = var.region
  repository_id = var.service_name
  format        = "DOCKER"

  depends_on = [google_project_service.required]
}

resource "google_storage_bucket" "artifacts" {
  project                     = var.project_id
  name                        = "${var.project_id}-${var.service_name}"
  location                    = "US"
  uniform_bucket_level_access = true

  depends_on = [google_project_service.required]
}

resource "google_storage_bucket_iam_member" "runtime_artifacts_admin" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectAdmin"
  member = google_service_account.runtime.member
}

resource "google_storage_bucket_iam_member" "p4sa_object_admin" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectAdmin"
  member = local.vertex_p4sa
}

resource "google_storage_bucket_iam_member" "extra_p4sa_object_admin" {
  for_each = local.extra_p4sas

  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectAdmin"
  member = each.value
}

resource "google_storage_bucket_iam_member" "extra_p4sa_bucket_reader" {
  for_each = local.extra_p4sas

  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.legacyBucketReader"
  member = each.value
}

resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = var.service_name
  display_name = "A2A bridge Cloud Run runtime"
}

resource "google_project_iam_member" "runtime_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = google_service_account.runtime.member
}

# signBlob on self lets the runtime mint V4 signed URLs without a key file.
resource "google_service_account_iam_member" "runtime_self_sign" {
  count = var.enable_artifact_export ? 1 : 0

  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = google_service_account.runtime.member
}

resource "google_service_account_iam_member" "p4sa_impersonate_runtime" {
  count = var.enable_artifact_export ? 1 : 0

  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = local.vertex_p4sa
}

resource "google_service_account_iam_member" "extra_p4sa_impersonate_runtime" {
  for_each = var.enable_artifact_export ? local.extra_p4sas : {}

  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = each.value
}

resource "google_firestore_database" "sessions" {
  count = local.firestore_enabled ? 1 : 0

  project     = var.project_id
  name        = var.firestore_database
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.required]
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_firestore_field" "session_ttl" {
  count = local.firestore_enabled ? 1 : 0

  project    = var.project_id
  database   = google_firestore_database.sessions[0].name
  collection = "bridge_sessions"
  field      = "updated_at"

  ttl_config {}
}

resource "google_project_iam_member" "runtime_firestore_user" {
  count = local.firestore_enabled ? 1 : 0

  project = var.project_id
  role    = "roles/datastore.user"
  member  = google_service_account.runtime.member
}

# Deny-all rules are defense in depth: the bridge uses the Admin/IAM path
# (roles/datastore.user), which bypasses Security Rules, so this does not
# affect it. See terraform/firestore.rules.
resource "google_firebaserules_ruleset" "firestore" {
  count = local.firestore_enabled ? 1 : 0

  project = var.project_id

  source {
    files {
      name    = "firestore.rules"
      content = file("${path.module}/firestore.rules")
    }
  }

  depends_on = [google_firestore_database.sessions]
}

resource "google_firebaserules_release" "firestore" {
  count = local.firestore_enabled ? 1 : 0

  project      = var.project_id
  name         = "cloud.firestore/${var.firestore_database}"
  ruleset_name = google_firebaserules_ruleset.firestore[0].name

  depends_on = [google_firestore_database.sessions]
}

resource "google_cloud_run_v2_service" "bridge" {
  project             = var.project_id
  name                = var.service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.runtime.email
    timeout         = "3600s"

    scaling {
      min_instance_count = 1
      # Single instance: session turns are serialized by a process-local lock.
      max_instance_count = 1
    }

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello" # replaced by `make deploy`

      ports {
        container_port = 8080
      }

      env {
        name  = "PROJECT_ID"
        value = local.vertex_project_id
      }
      env {
        name  = "LOCATION"
        value = "global"
      }
      env {
        name  = "VERTEX_ENDPOINT"
        value = var.vertex_endpoint
      }
      env {
        name  = "ENV_SCOPE"
        value = var.env_scope
      }
      dynamic "env" {
        for_each = local.firestore_enabled ? [1] : []
        content {
          name  = "FIRESTORE_DATABASE"
          value = google_firestore_database.sessions[0].name
        }
      }
      dynamic "env" {
        for_each = var.enable_artifact_export ? [1] : []
        content {
          name  = "UPLOAD_BUCKET"
          value = google_storage_bucket.artifacts.name
        }
      }
    }
  }

  depends_on = [
    google_project_service.required,
    google_artifact_registry_repository.bridge,
  ]
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      template[0].containers[0].env,
    ]
  }
}

resource "google_cloud_run_v2_service_iam_member" "ge_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.bridge.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-discoveryengine.iam.gserviceaccount.com"
}

