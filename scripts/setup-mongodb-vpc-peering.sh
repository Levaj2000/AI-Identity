#!/usr/bin/env bash
# setup-mongodb-vpc-peering.sh — accept a VPC peering connection from MongoDB Atlas.
#
# Run this AFTER you've initiated peering in the Atlas UI:
#   Network Access → Peering → Add Peering Connection → Google Cloud Platform.
#
# Atlas will show you two values you need to capture:
#   - Atlas's GCP Project ID (e.g. gcp-prod-abc12345)
#   - Atlas's Network Name (e.g. nw-12345678-peer-0)
#
# Usage:
#   export ATLAS_GCP_PROJECT_ID="gcp-prod-abc12345"
#   export ATLAS_NETWORK_NAME="nw-12345678-peer-0"
#   ./scripts/setup-mongodb-vpc-peering.sh
#
# After this completes, watch the Atlas peering page — status flips from
# WAITING_FOR_USER → PENDING_ACCEPTANCE → AVAILABLE within ~2 minutes.

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-project-8bbb04f8-fda8-462e-bc2}"
GCP_NETWORK="${GCP_NETWORK:-default}"
PEERING_NAME="${PEERING_NAME:-mongodb-atlas-peering}"

if [[ -z "${ATLAS_GCP_PROJECT_ID:-}" ]]; then
  echo "ERROR: ATLAS_GCP_PROJECT_ID is not set."
  echo "Get it from Atlas → Network Access → Peering (the 'GCP Project ID' field shown by Atlas)."
  exit 1
fi

if [[ -z "${ATLAS_NETWORK_NAME:-}" ]]; then
  echo "ERROR: ATLAS_NETWORK_NAME is not set."
  echo "Get it from Atlas → Network Access → Peering (the 'Network Name' field)."
  exit 1
fi

echo "▶ Verifying gcloud auth..."
gcloud auth print-access-token >/dev/null

echo "▶ Setting project context to ${PROJECT_ID}..."
gcloud config set project "${PROJECT_ID}"

# ── Create the peering ───────────────────────────────────────────────────
echo "▶ Creating peering ${PEERING_NAME} on VPC ${GCP_NETWORK}..."
echo "   Atlas project: ${ATLAS_GCP_PROJECT_ID}"
echo "   Atlas network: ${ATLAS_NETWORK_NAME}"

gcloud compute networks peerings create "${PEERING_NAME}" \
  --network="${GCP_NETWORK}" \
  --peer-project="${ATLAS_GCP_PROJECT_ID}" \
  --peer-network="${ATLAS_NETWORK_NAME}" \
  --import-custom-routes \
  --export-custom-routes

echo ""
echo "✅ Peering created. Now go back to Atlas → Network Access → Peering"
echo "   and watch the status flip to AVAILABLE (~1-2 min)."
echo ""
echo "Once AVAILABLE, also add the GCP VPC CIDR to Atlas IP Access List:"
echo "   Network Access → IP Access List → Add IP Address"
echo "   Use the CIDR of your GKE cluster's pod range."
echo ""
echo "Verify peering status from gcloud:"
echo "   gcloud compute networks peerings list --network=${GCP_NETWORK}"
