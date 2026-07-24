#!/bin/bash
#
# Fix IAM Permissions for Service Accounts
# This script grants the necessary IAM permissions to deploy Cloud Run services
#

set -e

PROJECT_ID="${PROJECT_ID:-}"
USER_EMAIL="${USER_EMAIL:-}"

echo "=========================================="
echo "Fixing IAM Permissions for Deployment"
echo "=========================================="
echo ""
echo "Project: $PROJECT_ID"
echo "User: $USER_EMAIL"
echo ""

# List of service accounts that failed
SERVICE_ACCOUNTS=(
	"copywriter-sa"
	"designer-sa"
	"critic-sa"
	"project-manager-sa"
)

echo "This script will grant you the 'iam.serviceAccountUser' role"
echo "on the following service accounts:"
echo ""
for sa in "${SERVICE_ACCOUNTS[@]}"; do
	echo "  - ${sa}@${PROJECT_ID}.iam.gserviceaccount.com"
done
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
	echo "Aborted."
	exit 1
fi

echo ""
echo "Granting permissions..."
echo ""

SUCCESS_COUNT=0
FAIL_COUNT=0

for sa in "${SERVICE_ACCOUNTS[@]}"; do
	SA_EMAIL="${sa}@${PROJECT_ID}.iam.gserviceaccount.com"
	echo "→ Granting iam.serviceAccountUser on $SA_EMAIL..."

	if gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
		--member="user:$USER_EMAIL" \
		--role="roles/iam.serviceAccountUser" \
		--project="$PROJECT_ID" >/dev/null 2>&1; then
		echo "  ✓ Success"
		((SUCCESS_COUNT++))
	else
		echo "  ✗ Failed (service account may not exist yet)"
		((FAIL_COUNT++))
	fi
done

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo "  ✓ Success: $SUCCESS_COUNT"
echo "  ✗ Failed: $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -gt 0 ]; then
	echo "Note: Failed service accounts may not exist yet."
	echo "They will be created during deployment."
	echo ""
fi

echo "You can now retry the deployment with:"
echo "  cd agents/deploy"
echo "  ./deploy_complete_system.sh"
echo ""
