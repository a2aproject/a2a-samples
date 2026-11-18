# Artifact export

Use this when the user needs to download a file you produced in the sandbox.

Each user message includes an `[artifact-export]` block with a one-time signed
upload URL and a matching download link.

1. If exporting multiple files, `tar czf out.tgz <files>` first.
2. Upload: `curl -fsS -X PUT -T <path> '<signed PUT url>'`
3. Print the provided download link on its own line.

Do **not** use `gsutil`; the sandbox has no GCP credentials.
