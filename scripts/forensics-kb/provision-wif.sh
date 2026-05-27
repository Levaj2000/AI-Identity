#!/usr/bin/env bash
# Set up Workload Identity Federation between Vercel and GCP so the
# Vercel-hosted /forensics widget can impersonate the forensics-agent-runtime
# service account without a long-lived key.
#
# Idempotent — safe to re-run.

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project-8bbb04f8-fda8-462e-bc2}"
PROJECT_NUMBER="${PROJECT_NUMBER:-210992154660}"
POOL_ID="${POOL_ID:-vercel-pool}"
PROVIDER_ID="${PROVIDER_ID:-vercel}"
VERCEL_TEAM_SLUG="${VERCEL_TEAM_SLUG:-jeff-levas-projects}"
VERCEL_PROJECT_NAME="${VERCEL_PROJECT_NAME:-ai-identity-landing}"
SA_EMAIL="${SA_EMAIL:-forensics-agent-runtime@${PROJECT_ID}.iam.gserviceaccount.com}"

ISSUER_URI="https://oidc.vercel.com/${VERCEL_TEAM_SLUG}"
ALLOWED_AUDIENCE="https://vercel.com/${VERCEL_TEAM_SLUG}"

echo "==> Project:        $PROJECT_ID ($PROJECT_NUMBER)"
echo "==> Pool / Provider $POOL_ID / $PROVIDER_ID"
echo "==> Vercel issuer:  $ISSUER_URI"
echo "==> Default aud:    $ALLOWED_AUDIENCE"
echo "==> SA:             $SA_EMAIL"
echo

echo "==> [1/3] Workload Identity Pool"
if gcloud iam workload-identity-pools describe "$POOL_ID" \
    --project="$PROJECT_ID" --location=global >/dev/null 2>&1; then
  echo "    pool already exists"
else
  gcloud iam workload-identity-pools create "$POOL_ID" \
    --project="$PROJECT_ID" \
    --location=global \
    --display-name="Vercel" \
    --description="Federates Vercel OIDC tokens for marketing site widgets"
fi

echo "==> [2/3] OIDC Provider"
if gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" \
    --project="$PROJECT_ID" --location=global \
    --workload-identity-pool="$POOL_ID" >/dev/null 2>&1; then
  echo "    provider already exists — updating attributes"
  gcloud iam workload-identity-pools providers update-oidc "$PROVIDER_ID" \
    --project="$PROJECT_ID" \
    --location=global \
    --workload-identity-pool="$POOL_ID" \
    --issuer-uri="$ISSUER_URI" \
    --allowed-audiences="$ALLOWED_AUDIENCE" \
    --attribute-mapping="google.subject=assertion.sub,attribute.owner=assertion.owner,attribute.project=assertion.project,attribute.environment=assertion.environment" \
    --attribute-condition="assertion.owner == '${VERCEL_TEAM_SLUG}' && assertion.project == '${VERCEL_PROJECT_NAME}'"
else
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
    --project="$PROJECT_ID" \
    --location=global \
    --workload-identity-pool="$POOL_ID" \
    --display-name="Vercel OIDC" \
    --issuer-uri="$ISSUER_URI" \
    --allowed-audiences="$ALLOWED_AUDIENCE" \
    --attribute-mapping="google.subject=assertion.sub,attribute.owner=assertion.owner,attribute.project=assertion.project,attribute.environment=assertion.environment" \
    --attribute-condition="assertion.owner == '${VERCEL_TEAM_SLUG}' && assertion.project == '${VERCEL_PROJECT_NAME}'"
fi

echo "==> [3/3] SA impersonation binding"
PRINCIPAL_SET="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.project/${VERCEL_PROJECT_NAME}"
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="$PRINCIPAL_SET" \
  --condition=None | tail -3

AUDIENCE="//iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"

cat <<EOF

==> WIF ready.

Set these env vars on Vercel (Production env at minimum):

    VERTEX_PROJECT_ID=project-8bbb04f8-fda8-462e-bc2
    VERTEX_LOCATION=global
    VERTEX_ENGINE_ID=forensics-agent
    GCP_WIF_AUDIENCE=${AUDIENCE}
    GCP_SA_EMAIL=${SA_EMAIL}

Also enable OIDC token issuance in Vercel:
    Project Settings → Security → OIDC Federation → Enable
    (or set the issuance mode to "Team")

Vercel injects VERCEL_OIDC_TOKEN at runtime; the API route reads it.

EOF
