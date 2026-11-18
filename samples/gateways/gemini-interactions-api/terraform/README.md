# Terraform: A2A bridge infra

Provisions the Cloud Run service, Artifact Registry repo, GCS artifacts
bucket, runtime service account, IAM bindings, and (optionally) a Firestore
database for session continuity. Uses only the `hashicorp/google` provider.

## Feature gates

| Variable | Default | Effect when enabled |
| --- | --- | --- |
| `firestore_database` | `"a2a-bridge"` | Creates a native-mode Firestore DB plus a TTL policy on `bridge_sessions.updated_at`, grants `roles/datastore.user` to the runtime SA, and publishes [`firestore.rules`](firestore.rules) as a deny-all ruleset via firebaserules. Set to `""` to fall back to the in-memory store. |
| `enable_artifact_export` | `false` | Grants `iam.serviceAccountTokenCreator` (signBlob on self plus P4SA impersonation) and sets `UPLOAD_BUCKET` so the bridge can mint V4 signed URLs for sandbox file egress. |

### Security rules

When `firestore_database` is enabled the apply also publishes
[`firestore.rules`](firestore.rules) as a deny-all ruleset (via
`google_firebaserules_ruleset`/`_release`). This is defense-in-depth and
does not affect the bridge, which reaches Firestore through the runtime SA
(`roles/datastore.user`, the Admin/IAM path) and so bypasses Security Rules.

## Apply

```bash
terraform init
terraform apply -var project_id=$PROJECT_ID
```

The Cloud Run service is created with a public placeholder image so the
first apply succeeds before anything is pushed to the new Artifact
Registry repo; `make build deploy` then swaps in the real image, and
`ignore_changes` on `image` keeps Terraform from reverting it.

## GE per-user auth

GE's `serverSideOauth2` flow needs a classic Web-application OAuth 2.0
client (`*.apps.googleusercontent.com`). There is no public API or
Terraform resource for those (the `google_iam_oauth_client` resource
creates a Workforce Identity client that `accounts.google.com` rejects),
so this is a one-time manual step:

1. Cloud Console > APIs & Services > Credentials > Create credentials >
   OAuth client ID > Web application. Add GE's redirect URI:
   `https://vertexaisearch.cloud.google.com/static/oauth/oauth.html`.
2. Pipe the generated client secret into the CLI (do not pass it as an
   argument):

```bash
a2a-bridge create-authorization \
  --name a2a-bridge \
  --oauth-client-id CLIENT_ID.apps.googleusercontent.com \
  --client-secret-stdin <<<"$CLIENT_SECRET"

a2a-bridge register-ge --authorization a2a-bridge ...
```

The DiscoveryEngine `Authorization` resource itself also has no
Terraform support in the `google` provider, which is why it is created
via the CLI rather than here.
