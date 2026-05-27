#!/usr/bin/env bash
# Provision the GCP resources for the forensics knowledge agent.
#
# Idempotent — safe to re-run. Each step skips work that's already done.
#
# Requires:
#   - gcloud auth login (with access to the project below)
#   - scripts/forensics-kb/out/ populated by stage_corpus.py
#
# Costs are covered by the $1K GenAI App Builder credit on this project.

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project-8bbb04f8-fda8-462e-bc2}"
REGION="${REGION:-us}"                       # Vertex AI Search uses "us" or "global"
GCS_REGION="${GCS_REGION:-us-east1}"
BUCKET_NAME="${BUCKET_NAME:-${PROJECT_ID}-forensics-kb}"
DATASTORE_ID="${DATASTORE_ID:-forensics-kb}"
ENGINE_ID="${ENGINE_ID:-forensics-agent}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_DIR="$REPO_ROOT/scripts/forensics-kb/out"

if [ ! -d "$OUT_DIR/docs" ]; then
  echo "Missing $OUT_DIR/docs. Run stage_corpus.py first."
  exit 1
fi

echo "==> Project: $PROJECT_ID"
echo "==> Bucket:  gs://$BUCKET_NAME"
echo "==> Datastore: $DATASTORE_ID  Engine: $ENGINE_ID"
echo

echo "==> [1/5] Enabling APIs"
gcloud services enable \
  discoveryengine.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com \
  --project="$PROJECT_ID"

echo "==> [2/5] Creating GCS bucket (if absent)"
if ! gcloud storage buckets describe "gs://$BUCKET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://$BUCKET_NAME" \
    --project="$PROJECT_ID" \
    --location="$GCS_REGION" \
    --uniform-bucket-level-access
else
  echo "    bucket already exists, skipping"
fi

echo "==> [3/5] Rendering metadata.jsonl with bucket name"
sed "s|__BUCKET__|$BUCKET_NAME|g" "$OUT_DIR/metadata.jsonl" > "$OUT_DIR/metadata.rendered.jsonl"

echo "==> [4/5] Uploading docs + metadata"
gcloud storage cp "$OUT_DIR/docs/"*.txt "gs://$BUCKET_NAME/docs/" \
  --project="$PROJECT_ID"
gcloud storage cp "$OUT_DIR/metadata.rendered.jsonl" \
  "gs://$BUCKET_NAME/metadata.jsonl" \
  --project="$PROJECT_ID"

echo "==> [5/5] Provisioning Vertex AI Search datastore + engine"

ACCESS_TOKEN="$(gcloud auth print-access-token)"
BASE_URL="https://discoveryengine.googleapis.com/v1"
COLLECTION="projects/$PROJECT_ID/locations/$REGION/collections/default_collection"

create_datastore() {
  echo "    creating datastore $DATASTORE_ID"
  curl -fsSL -X POST \
    "$BASE_URL/$COLLECTION/dataStores?dataStoreId=$DATASTORE_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -H "X-Goog-User-Project: $PROJECT_ID" \
    -d '{
      "displayName": "Forensics KB",
      "industryVertical": "GENERIC",
      "solutionTypes": ["SOLUTION_TYPE_SEARCH", "SOLUTION_TYPE_CHAT"],
      "contentConfig": "CONTENT_REQUIRED"
    }' | tee /tmp/forensics-datastore.json
  echo
}

if curl -fsSL "$BASE_URL/$COLLECTION/dataStores/$DATASTORE_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "X-Goog-User-Project: $PROJECT_ID" >/dev/null 2>&1; then
  echo "    datastore $DATASTORE_ID already exists, skipping create"
else
  create_datastore
fi

echo "    importing documents from GCS"
curl -fsSL -X POST \
  "$BASE_URL/$COLLECTION/dataStores/$DATASTORE_ID/branches/default_branch/documents:import" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: $PROJECT_ID" \
  -d "{
    \"gcsSource\": {
      \"inputUris\": [\"gs://$BUCKET_NAME/metadata.jsonl\"],
      \"dataSchema\": \"document\"
    },
    \"reconciliationMode\": \"FULL\"
  }" | tee /tmp/forensics-import.json
echo

if curl -fsSL "$BASE_URL/$COLLECTION/engines/$ENGINE_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "X-Goog-User-Project: $PROJECT_ID" >/dev/null 2>&1; then
  echo "    engine $ENGINE_ID already exists, skipping create"
else
  echo "    creating engine $ENGINE_ID"
  curl -fsSL -X POST \
    "$BASE_URL/$COLLECTION/engines?engineId=$ENGINE_ID" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -H "X-Goog-User-Project: $PROJECT_ID" \
    -d "{
      \"displayName\": \"Forensics Agent\",
      \"solutionType\": \"SOLUTION_TYPE_CHAT\",
      \"industryVertical\": \"GENERIC\",
      \"dataStoreIds\": [\"$DATASTORE_ID\"],
      \"chatEngineConfig\": {
        \"agentCreationConfig\": {
          \"business\": \"AI Identity\",
          \"defaultLanguageCode\": \"en\",
          \"timeZone\": \"America/Denver\"
        }
      }
    }" | tee /tmp/forensics-engine.json
  echo
fi

cat <<EOF

==> Provisioned.
    Project:    $PROJECT_ID
    Datastore:  projects/$PROJECT_ID/locations/$REGION/collections/default_collection/dataStores/$DATASTORE_ID
    Engine:     projects/$PROJECT_ID/locations/$REGION/collections/default_collection/engines/$ENGINE_ID

Import is asynchronous. Check status in the Vertex AI Search console:
    https://console.cloud.google.com/gen-app-builder/data-stores?project=$PROJECT_ID

Next: build the Next.js API route at landing-page/src/app/api/forensics/ask/route.ts.
EOF
