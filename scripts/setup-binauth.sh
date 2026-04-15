#!/usr/bin/env bash
# Provision Binary Authorization: APIs, KMS signing key, Container Analysis
# Note, attestor, IAM bindings for the deploy pipeline, and the cluster-level
# evaluation mode. Does NOT apply the policy — that's a separate step with
# `gcloud container binauthz policy import binauth-policy.yaml`.
#
# Idempotent — safe to re-run. Only takes actions needed to reach the target
# state.
#
# Usage:
#   scripts/setup-binauth.sh [PROJECT_ID]

set -euo pipefail

PROJECT_ID="${1:-project-8bbb04f8-fda8-462e-bc2}"
REGION=us-east1
CLUSTER=ai-identity
KEYRING=binauth
KEY=attestor-key
NOTE_ID=ai-identity-attestor-note
ATTESTOR=ai-identity-attestor
GITHUB_SA="github-actions@${PROJECT_ID}.iam.gserviceaccount.com"

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
BINAUTH_AGENT="service-${PROJECT_NUMBER}@gcp-sa-binaryauthorization.iam.gserviceaccount.com"

echo "→ project:  $PROJECT_ID ($PROJECT_NUMBER)"
echo "→ cluster:  $CLUSTER ($REGION)"
echo "→ attestor: $ATTESTOR (KMS key: $REGION/$KEYRING/$KEY)"
echo

# ---- 1. Enable APIs -------------------------------------------------------
echo "• ensuring required APIs enabled"
gcloud services enable \
  binaryauthorization.googleapis.com \
  cloudkms.googleapis.com \
  containeranalysis.googleapis.com \
  --project="$PROJECT_ID" >/dev/null
echo "✓ APIs enabled"

# Trigger creation of the Binary Authorization service agent, which we'll
# grant note access to further down. Describing the policy is an idempotent
# no-op that also forces the agent to be provisioned on first run.
gcloud container binauthz policy export --project="$PROJECT_ID" >/dev/null 2>&1 || true

# ---- 2. KMS keyring + asymmetric signing key ------------------------------
echo "• ensuring KMS keyring + signing key"
gcloud kms keyrings describe "$KEYRING" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1 \
  || gcloud kms keyrings create "$KEYRING" --location="$REGION" --project="$PROJECT_ID" >/dev/null
gcloud kms keys describe "$KEY" --location="$REGION" --keyring="$KEYRING" --project="$PROJECT_ID" >/dev/null 2>&1 \
  || gcloud kms keys create "$KEY" --location="$REGION" --keyring="$KEYRING" \
       --purpose=asymmetric-signing --default-algorithm=ec-sign-p256-sha256 \
       --protection-level=software --project="$PROJECT_ID" >/dev/null
echo "✓ KMS key: projects/$PROJECT_ID/locations/$REGION/keyRings/$KEYRING/cryptoKeys/$KEY"

# ---- 3. Container Analysis Note -------------------------------------------
echo "• ensuring Container Analysis Note $NOTE_ID"
TOKEN=$(gcloud auth print-access-token)
http_code=$(curl -sS -o /dev/null -w '%{http_code}' \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-goog-user-project: $PROJECT_ID" \
  "https://containeranalysis.googleapis.com/v1/projects/${PROJECT_ID}/notes/${NOTE_ID}")
if [[ "$http_code" == "200" ]]; then
  echo "✓ note exists"
else
  curl -sS -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -H "x-goog-user-project: $PROJECT_ID" \
    "https://containeranalysis.googleapis.com/v1/projects/${PROJECT_ID}/notes/?noteId=${NOTE_ID}" \
    -d "{\"name\":\"projects/${PROJECT_ID}/notes/${NOTE_ID}\",\"attestation\":{\"hint\":{\"humanReadableName\":\"AI Identity build attestation\"}}}" \
    >/dev/null
  echo "✓ note created"
fi

# ---- 4. Attestor bound to the KMS key -------------------------------------
echo "• ensuring attestor $ATTESTOR"
if gcloud container binauthz attestors describe "$ATTESTOR" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "✓ attestor exists"
else
  gcloud container binauthz attestors create "$ATTESTOR" \
    --attestation-authority-note="$NOTE_ID" \
    --attestation-authority-note-project="$PROJECT_ID" \
    --project="$PROJECT_ID" >/dev/null
  echo "✓ attestor created"
fi

# Attach KMS public key to the attestor (idempotent — duplicate add is skipped
# by checking existing keys).
EXISTING_KEYS=$(gcloud container binauthz attestors describe "$ATTESTOR" \
  --project="$PROJECT_ID" --format='value(userOwnedGrafeasNote.publicKeys[].id)' 2>/dev/null || true)
KMS_KEY_ID="//cloudkms.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/keyRings/${KEYRING}/cryptoKeys/${KEY}/cryptoKeyVersions/1"
if echo "$EXISTING_KEYS" | grep -qF "$KMS_KEY_ID"; then
  echo "✓ KMS public key already attached to attestor"
else
  gcloud container binauthz attestors public-keys add \
    --attestor="$ATTESTOR" \
    --keyversion-project="$PROJECT_ID" --keyversion-location="$REGION" \
    --keyversion-keyring="$KEYRING" --keyversion-key="$KEY" --keyversion=1 \
    --project="$PROJECT_ID" >/dev/null
  echo "✓ KMS public key attached"
fi

# ---- 5. IAM bindings ------------------------------------------------------
echo "• granting Binary Authorization service agent read on the note"
curl -sS -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "x-goog-user-project: $PROJECT_ID" \
  "https://containeranalysis.googleapis.com/v1/projects/${PROJECT_ID}/notes/${NOTE_ID}:setIamPolicy" \
  -d "{
    \"resource\":\"projects/${PROJECT_ID}/notes/${NOTE_ID}\",
    \"policy\":{\"bindings\":[
      {\"role\":\"roles/containeranalysis.notes.occurrences.viewer\",\"members\":[\"serviceAccount:${BINAUTH_AGENT}\"]},
      {\"role\":\"roles/containeranalysis.notes.attacher\",\"members\":[\"serviceAccount:${GITHUB_SA}\"]}
    ]}
  }" >/dev/null
echo "✓ note IAM applied"

echo "• granting GitHub Actions SA KMS signer + attestation permissions"
gcloud kms keys add-iam-policy-binding "$KEY" \
  --location="$REGION" --keyring="$KEYRING" \
  --member="serviceAccount:${GITHUB_SA}" \
  --role=roles/cloudkms.signerVerifier \
  --project="$PROJECT_ID" --condition=None >/dev/null 2>&1
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${GITHUB_SA}" \
  --role=roles/binaryauthorization.attestorsViewer \
  --condition=None >/dev/null 2>&1
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${GITHUB_SA}" \
  --role=roles/containeranalysis.occurrences.editor \
  --condition=None >/dev/null 2>&1
echo "✓ IAM bindings applied"

# ---- 6. Cluster-level evaluation mode -------------------------------------
echo "• ensuring cluster binauth evaluation mode = PROJECT_SINGLETON_POLICY_ENFORCE"
CURRENT_MODE=$(gcloud container clusters describe "$CLUSTER" --region="$REGION" \
  --project="$PROJECT_ID" --format='value(binaryAuthorization.evaluationMode)' 2>/dev/null || echo "")
if [[ "$CURRENT_MODE" == "PROJECT_SINGLETON_POLICY_ENFORCE" ]]; then
  echo "✓ cluster already enforcing project singleton policy"
else
  gcloud container clusters update "$CLUSTER" --region="$REGION" \
    --project="$PROJECT_ID" \
    --binauthz-evaluation-mode=PROJECT_SINGLETON_POLICY_ENFORCE >/dev/null
  echo "✓ cluster evaluation mode updated"
fi

echo
echo "=== done ==="
echo "Next steps:"
echo "  # Apply the policy (DRY_RUN initially, flip to ENFORCED_BLOCK_AND_AUDIT_LOG later)"
echo "  gcloud container binauthz policy import binauth-policy.yaml"
echo
echo "  # Sign an existing image digest manually (CI does this automatically on every deploy):"
echo "  gcloud beta container binauthz attestations sign-and-create \\"
echo "    --artifact-url=<REGISTRY>/<PATH>@sha256:... --attestor=$ATTESTOR \\"
echo "    --attestor-project=$PROJECT_ID --keyversion=1 \\"
echo "    --keyversion-project=$PROJECT_ID --keyversion-location=$REGION \\"
echo "    --keyversion-keyring=$KEYRING --keyversion-key=$KEY"
