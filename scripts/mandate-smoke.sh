#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# mandate-smoke.sh — Self-contained smoke test for the Mandate Service.
#
# Exercises behaviour that the k8s liveness probe cannot:
#   1. /health responds 200
#   2. /api/v1/mandates/verify rejects an obviously-invalid mandate
#   3. /api/v1/mandates/verify rejects an ml-dsa-87-only mandate
#      (regression guard for the unknown-algorithm spoofing path closed
#      in the Ship-A hardening pass)
#
# All checks use the unauthenticated /verify endpoint — no API key needed.
# Default target is the in-cluster service; pass MANDATE_URL to override.
#
# Usage:
#   # From inside the cluster (the typical case until Ship B exposes ingress):
#   kubectl run mandate-smoke --rm -it --restart=Never \
#       --image=curlimages/curl --command -- sh -c "$(cat scripts/mandate-smoke.sh)"
#
#   # From a developer machine with port-forward:
#   kubectl port-forward svc/mandate-service 8003:8003 &
#   MANDATE_URL=http://localhost:8003 ./scripts/mandate-smoke.sh
#
# Exit codes: 0 on full pass, non-zero on first failure.
# ──────────────────────────────────────────────────────────────────────

set -euo pipefail

MANDATE_URL="${MANDATE_URL:-http://mandate-service:8003}"
TIMEOUT=15

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
info()  { printf '   %s\n' "$*"; }

fail() {
    red "❌ $1"
    exit 1
}

# ── 1. Health ─────────────────────────────────────────────────────────
echo "▶ /health"
http_code=$(curl -s -o /tmp/mandate-smoke-health.json -w "%{http_code}" \
    --max-time "$TIMEOUT" "$MANDATE_URL/health")
[[ "$http_code" == "200" ]] || fail "/health returned $http_code"
green "✅ /health 200"

# ── 2. Verify rejects an obvious garbage mandate ──────────────────────
echo "▶ /verify rejects garbage"
garbage_payload='{
  "mandate": {
    "mandate_id": "mnd_smoke01",
    "schema_version": "1.0",
    "status": "active",
    "issuer": {"org_id": "smoke", "user_id": "smoke"},
    "subject": {"agent_id": "smoke", "org_id": "smoke"},
    "scope": ["read:smoke"],
    "conditions": {},
    "policy_hash": null,
    "valid_from": "2026-01-01T00:00:00Z",
    "valid_until": "2030-01-01T00:00:00Z",
    "signatures": [
      {"algorithm": "ecdsa-p256-sha256", "key_id": "local:deadbeefdeadbeef", "signature": "AAAA"}
    ],
    "revocation": null,
    "metadata": {},
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  }
}'
response=$(curl -s --max-time "$TIMEOUT" \
    -H "Content-Type: application/json" \
    -d "$garbage_payload" \
    "$MANDATE_URL/api/v1/mandates/verify")
echo "$response" | grep -q '"valid":false' \
    || fail "verifier accepted a garbage mandate: $response"
green "✅ /verify rejects garbage"

# ── 3. Verify rejects ml-dsa-87-only mandate ──────────────────────────
echo "▶ /verify rejects ml-dsa-87-only"
pqc_only_payload='{
  "mandate": {
    "mandate_id": "mnd_smoke02",
    "schema_version": "1.0",
    "status": "active",
    "issuer": {"org_id": "smoke", "user_id": "smoke"},
    "subject": {"agent_id": "smoke", "org_id": "smoke"},
    "scope": ["read:smoke"],
    "conditions": {},
    "policy_hash": null,
    "valid_from": "2026-01-01T00:00:00Z",
    "valid_until": "2030-01-01T00:00:00Z",
    "signatures": [
      {"algorithm": "ml-dsa-87", "key_id": "kms:pqc-placeholder", "signature": "AAAA"}
    ],
    "revocation": null,
    "metadata": {},
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  }
}'
response=$(curl -s --max-time "$TIMEOUT" \
    -H "Content-Type: application/json" \
    -d "$pqc_only_payload" \
    "$MANDATE_URL/api/v1/mandates/verify")
echo "$response" | grep -q '"valid":false' \
    || fail "verifier accepted an ml-dsa-87-only mandate (regression!): $response"
green "✅ /verify rejects ml-dsa-87-only"

green "🎉 Mandate Service smoke passed"
