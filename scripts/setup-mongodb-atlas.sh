#!/usr/bin/env bash
# setup-mongodb-atlas.sh — wire MongoDB Atlas into the GKE cluster.
#
# Run this AFTER you've:
#   1. Applied the $500 startup credit on cloud.mongodb.com
#   2. Provisioned the M10 cluster `mandate-cluster-prod` in GCP us-east1
#   3. Created a database user (Atlas UI: Security → Database Access)
#   4. Captured the SRV connection string from Atlas UI:
#        Database → Connect → Drivers → mongodb+srv://...
#
# Usage:
#   export MONGODB_URI='mongodb+srv://USER:PASS@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority'
#   ./scripts/setup-mongodb-atlas.sh

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-project-8bbb04f8-fda8-462e-bc2}"
SECRET_NAME="ai-identity-MONGODB_URI"
SERVICE_ACCOUNT="ai-identity-forensic-signer@${PROJECT_ID}.iam.gserviceaccount.com"

if [[ -z "${MONGODB_URI:-}" ]]; then
  echo "ERROR: MONGODB_URI is not set."
  echo "Export it first: export MONGODB_URI='mongodb+srv://...'"
  exit 1
fi

echo "▶ Verifying gcloud auth..."
gcloud auth print-access-token >/dev/null

echo "▶ Setting project context to ${PROJECT_ID}..."
gcloud config set project "${PROJECT_ID}"

# ── Create or update the secret ──────────────────────────────────────────
if gcloud secrets describe "${SECRET_NAME}" >/dev/null 2>&1; then
  echo "▶ Secret ${SECRET_NAME} exists — adding new version..."
  printf '%s' "${MONGODB_URI}" | gcloud secrets versions add "${SECRET_NAME}" --data-file=-
else
  echo "▶ Creating secret ${SECRET_NAME}..."
  printf '%s' "${MONGODB_URI}" | gcloud secrets create "${SECRET_NAME}" \
    --replication-policy="automatic" \
    --data-file=-
fi

# ── Grant secretAccessor to the workload SA ──────────────────────────────
echo "▶ Granting secretmanager.secretAccessor to ${SERVICE_ACCOUNT}..."
gcloud secrets add-iam-policy-binding "${SECRET_NAME}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"

echo ""
echo "✅ MONGODB_URI is in Secret Manager and accessible to the mandate service."
echo ""
echo "Next steps:"
echo "  1. Build & push the mandate image:"
echo "     docker build -f Dockerfile.mandate -t us-east1-docker.pkg.dev/${PROJECT_ID}/ai-identity/mandate:latest ."
echo "     docker push us-east1-docker.pkg.dev/${PROJECT_ID}/ai-identity/mandate:latest"
echo ""
echo "  2. Apply the k8s manifests:"
echo "     kubectl apply -f k8s/secretproviderclass.yaml"
echo "     kubectl apply -f k8s/mandate-deployment.yaml"
echo "     kubectl apply -f k8s/mandate-service.yaml"
echo ""
echo "  3. Tail the logs:"
echo "     kubectl logs -f -n ai-identity -l app=mandate"
