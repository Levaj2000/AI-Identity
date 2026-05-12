#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# mandate-smoke.sh — Run the Mandate Service smoke test inside the pod.
#
# Why this wrapper exists:
#   The `ai-identity` namespace enforces PodSecurity `restricted:latest`
#   and the `allow-internal-to-mandate` NetworkPolicy only lets api/gateway
#   pods reach `mandate-service:8003`. That means a bare
#       kubectl run mandate-smoke --image=curlimages/curl ...
#   is rejected by PodSecurity *and* blocked by NetworkPolicy. The least
#   awful workaround is to exec into the existing mandate pod and talk to
#   localhost:8003 from there — no extra image, no policy edits.
#
#   The actual checks live in scripts/mandate_smoke.py; this script just
#   pipes that file into `python3 -` inside the mandate pod.
#
# Usage:
#   ./scripts/mandate-smoke.sh
#   NAMESPACE=ai-identity DEPLOYMENT=mandate ./scripts/mandate-smoke.sh
#
# Requires: gcloud / kubectl context pointing at the GKE cluster with
# read+exec on deployments in $NAMESPACE.
#
# The deployment is named `mandate` (no -deployment suffix).
# Exits non-zero on the first failing check.
# ──────────────────────────────────────────────────────────────────────

set -euo pipefail

NAMESPACE="${NAMESPACE:-ai-identity}"
DEPLOYMENT="${DEPLOYMENT:-mandate}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="${SCRIPT_DIR}/mandate_smoke.py"

if [[ ! -f "$PY_SCRIPT" ]]; then
    echo "❌ missing $PY_SCRIPT" >&2
    exit 1
fi

if ! command -v kubectl >/dev/null 2>&1; then
    echo "❌ kubectl not on PATH" >&2
    exit 1
fi

echo "▶ exec deploy/${DEPLOYMENT} in ns/${NAMESPACE} → python3 - < scripts/mandate_smoke.py"

exec kubectl exec -n "$NAMESPACE" -i "deploy/${DEPLOYMENT}" -- python3 - < "$PY_SCRIPT"
