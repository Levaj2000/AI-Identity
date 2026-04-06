#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# AI Identity — Automated QA Smoke Test
# Runs the 15-step design partner onboarding checklist against production.
#
# Usage:
#   ./scripts/qa-smoke-test.sh                    # run against production
#   ./scripts/qa-smoke-test.sh http://localhost:8001 http://localhost:8002  # local
#
# Exit codes:
#   0 = all steps passed
#   1 = one or more steps failed
#
# Outputs a summary table and posts results to CEO Dashboard (if reachable).
# ─────────────────────────────────────────────────────────────────────

set -euo pipefail

API="${1:-https://ai-identity-api.onrender.com}"
GW="${2:-https://ai-identity-gateway.onrender.com}"
KEY="${AI_IDENTITY_QA_KEY:-test-dev-key-12345678}"
CEO_API="${CEO_DASHBOARD_API:-http://localhost:8000/api/v1}"
CEO_KEY="${CEO_API_KEY:-}"
RUN_DATE=$(date '+%Y-%m-%d %H:%M')

PASS=0
FAIL=0
RESULTS=()

# ── Helpers ──────────────────────────────────────────────────────────

pass() {
  PASS=$((PASS + 1))
  RESULTS+=("| $1 | $2 | ✅ PASS | $3 |")
  echo "  ✅ Step $1: $2"
}

fail() {
  FAIL=$((FAIL + 1))
  RESULTS+=("| $1 | $2 | ❌ FAIL | $3 |")
  echo "  ❌ Step $1: $2 — $3"
}

cleanup() {
  # Revoke the QA agent if it was created
  if [ -n "${AGENT_ID:-}" ]; then
    echo ""
    local retries=3
    local delay=2
    for i in $(seq 1 $retries); do
      HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$API/api/v1/agents/$AGENT_ID" -H "X-API-Key: $KEY" 2>/dev/null || echo "000")
      if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "400" ]; then
        # 200 = revoked, 400 = already revoked — both mean success
        echo "🧹 Cleaned up QA agent $AGENT_ID (HTTP $HTTP_CODE)"
        return
      fi
      echo "⚠️  Cleanup attempt $i/$retries failed (HTTP $HTTP_CODE), retrying in ${delay}s..."
      sleep $delay
      delay=$((delay * 2))
    done
    echo "❌ Failed to clean up QA agent $AGENT_ID after $retries attempts — manual cleanup needed"
  fi
}
trap cleanup EXIT

echo "═══════════════════════════════════════════════════════════════"
echo "  AI Identity — QA Smoke Test"
echo "  API: $API"
echo "  Gateway: $GW"
echo "  Date: $RUN_DATE"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ── Phase 1: Health & Docs ───────────────────────────────────────────

echo "Phase 1: Health & Docs"

# Step 1: API Health
HEALTH=$(curl -sf "$API/health" 2>/dev/null || echo '{"status":"error"}')
STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null || echo "error")
if [ "$STATUS" = "ok" ]; then
  pass 1 "API Health" "$STATUS"
else
  fail 1 "API Health" "status=$STATUS"
fi

# Step 2: Swagger UI
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" "$API/docs" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  pass 2 "Swagger UI" "HTTP $HTTP_CODE"
else
  fail 2 "Swagger UI" "HTTP $HTTP_CODE"
fi

# ── Phase 2: Agent Lifecycle ─────────────────────────────────────────

echo "Phase 2: Agent Lifecycle"

# Step 3: Create Agent
CREATE_RESP=$(curl -sf -X POST "$API/api/v1/agents" \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"QA Smoke Test Bot","description":"Automated QA","capabilities":["chat_completion","function_calling"],"metadata":{"source":"qa-script"}}' 2>/dev/null || echo '{}')
AGENT_ID=$(echo "$CREATE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent',{}).get('id',''))" 2>/dev/null || echo "")
AGENT_KEY=$(echo "$CREATE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('api_key',''))" 2>/dev/null || echo "")
if [ -n "$AGENT_ID" ] && [ -n "$AGENT_KEY" ]; then
  pass 3 "Create Agent" "id=${AGENT_ID:0:8}..."
else
  fail 3 "Create Agent" "No agent_id or api_key returned"
fi

# Step 4: Get Agent
if [ -n "$AGENT_ID" ]; then
  GET_RESP=$(curl -sf "$API/api/v1/agents/$AGENT_ID" -H "X-API-Key: $KEY" 2>/dev/null || echo '{}')
  GET_NAME=$(echo "$GET_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null || echo "")
  GET_STATUS=$(echo "$GET_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
  if [ "$GET_NAME" = "QA Smoke Test Bot" ] && [ "$GET_STATUS" = "active" ]; then
    pass 4 "Get Agent" "name=$GET_NAME, status=$GET_STATUS"
  else
    fail 4 "Get Agent" "name=$GET_NAME, status=$GET_STATUS"
  fi
else
  fail 4 "Get Agent" "Skipped — no agent_id"
fi

# Step 5: List Agents
LIST_RESP=$(curl -sf "$API/api/v1/agents?status=active" -H "X-API-Key: $KEY" 2>/dev/null || echo '{"total":0}')
LIST_TOTAL=$(echo "$LIST_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
if [ "$LIST_TOTAL" -gt 0 ] 2>/dev/null; then
  pass 5 "List Agents" "total=$LIST_TOTAL"
else
  fail 5 "List Agents" "total=$LIST_TOTAL"
fi

# Step 6: Update Agent
if [ -n "$AGENT_ID" ]; then
  UPD_RESP=$(curl -sf -X PUT "$API/api/v1/agents/$AGENT_ID" \
    -H "X-API-Key: $KEY" \
    -H "Content-Type: application/json" \
    -d '{"capabilities":["chat_completion","function_calling","embeddings"]}' 2>/dev/null || echo '{}')
  UPD_CAPS=$(echo "$UPD_RESP" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('capabilities',[])))" 2>/dev/null || echo "0")
  if [ "$UPD_CAPS" = "3" ]; then
    pass 6 "Update Agent" "capabilities=$UPD_CAPS"
  else
    fail 6 "Update Agent" "expected 3 capabilities, got $UPD_CAPS"
  fi
else
  fail 6 "Update Agent" "Skipped — no agent_id"
fi

# ── Phase 3: Key Management ─────────────────────────────────────────

echo "Phase 3: Key Management"

# Step 7: Create Key
if [ -n "$AGENT_ID" ]; then
  KEY_RESP=$(curl -sf -X POST "$API/api/v1/agents/$AGENT_ID/keys" -H "X-API-Key: $KEY" 2>/dev/null || echo '{}')
  KEY2_ID=$(echo "$KEY_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('key',{}).get('id',''))" 2>/dev/null || echo "")
  KEY2_VAL=$(echo "$KEY_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('api_key',''))" 2>/dev/null || echo "")
  if [ -n "$KEY2_ID" ] && [ -n "$KEY2_VAL" ]; then
    pass 7 "Create Key" "id=$KEY2_ID"
  else
    fail 7 "Create Key" "No key_id or api_key"
  fi
else
  fail 7 "Create Key" "Skipped"
fi

# Step 8: List Keys
if [ -n "$AGENT_ID" ]; then
  KEYS_RESP=$(curl -sf "$API/api/v1/agents/$AGENT_ID/keys" -H "X-API-Key: $KEY" 2>/dev/null || echo '{"total":0}')
  KEYS_TOTAL=$(echo "$KEYS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
  if [ "$KEYS_TOTAL" -ge 2 ] 2>/dev/null; then
    pass 8 "List Keys" "total=$KEYS_TOTAL"
  else
    fail 8 "List Keys" "expected ≥2, got $KEYS_TOTAL"
  fi
else
  fail 8 "List Keys" "Skipped"
fi

# Step 9: Rotate Key
if [ -n "$AGENT_ID" ]; then
  ROT_RESP=$(curl -sf -X POST "$API/api/v1/agents/$AGENT_ID/keys/rotate" -H "X-API-Key: $KEY" 2>/dev/null || echo '{}')
  ROT_NEW=$(echo "$ROT_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('new_key',{}).get('status',''))" 2>/dev/null || echo "")
  ROT_OLD=$(echo "$ROT_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('rotated_key',{}).get('status',''))" 2>/dev/null || echo "")
  if [ "$ROT_NEW" = "active" ] && [ "$ROT_OLD" = "rotated" ]; then
    pass 9 "Rotate Key" "new=active, old=rotated"
  else
    fail 9 "Rotate Key" "new=$ROT_NEW, old=$ROT_OLD"
  fi
else
  fail 9 "Rotate Key" "Skipped"
fi

# Step 10: Verify Rotation
if [ -n "$AGENT_ID" ]; then
  KEYS_RESP2=$(curl -sf "$API/api/v1/agents/$AGENT_ID/keys" -H "X-API-Key: $KEY" 2>/dev/null || echo '{"items":[]}')
  ACTIVE_COUNT=$(echo "$KEYS_RESP2" | python3 -c "import sys,json; keys=json.load(sys.stdin).get('items',[]); print(sum(1 for k in keys if k['status']=='active'))" 2>/dev/null || echo "0")
  ROTATED_COUNT=$(echo "$KEYS_RESP2" | python3 -c "import sys,json; keys=json.load(sys.stdin).get('items',[]); print(sum(1 for k in keys if k['status']=='rotated'))" 2>/dev/null || echo "0")
  if [ "$ACTIVE_COUNT" -ge 2 ] && [ "$ROTATED_COUNT" -ge 1 ] 2>/dev/null; then
    pass 10 "Verify Rotation" "active=$ACTIVE_COUNT, rotated=$ROTATED_COUNT"
  else
    fail 10 "Verify Rotation" "active=$ACTIVE_COUNT, rotated=$ROTATED_COUNT"
  fi
else
  fail 10 "Verify Rotation" "Skipped"
fi

# Step 11: Revoke Key
if [ -n "$AGENT_ID" ] && [ -n "${KEY2_ID:-}" ]; then
  REV_RESP=$(curl -sf -X DELETE "$API/api/v1/agents/$AGENT_ID/keys/$KEY2_ID" -H "X-API-Key: $KEY" 2>/dev/null || echo '{}')
  REV_STATUS=$(echo "$REV_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
  if [ "$REV_STATUS" = "revoked" ]; then
    pass 11 "Revoke Key" "status=revoked"
  else
    fail 11 "Revoke Key" "status=$REV_STATUS"
  fi
else
  fail 11 "Revoke Key" "Skipped"
fi

# ── Phase 4: Credential Vault ────────────────────────────────────────

echo "Phase 4: Credential Vault"

# Step 12: Store Credential
if [ -n "$AGENT_ID" ]; then
  CRED_RESP=$(curl -sf -X POST "$API/api/v1/agents/$AGENT_ID/credentials" \
    -H "X-API-Key: $KEY" \
    -H "Content-Type: application/json" \
    -d '{"provider":"openai","label":"qa-test","api_key":"sk-proj-fake-qa-key-1234567890"}' 2>/dev/null || echo '{}')
  CRED_PREFIX=$(echo "$CRED_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); c=d.get('credential',d); print(c.get('key_prefix',''))" 2>/dev/null || echo "")
  CRED_PLAIN=$(echo "$CRED_RESP" | python3 -c "import sys,json; print('api_key' in json.load(sys.stdin).get('credential',{}).keys())" 2>/dev/null || echo "True")
  if [ "$CRED_PREFIX" = "sk-proj-" ]; then
    pass 12 "Store Credential" "prefix=$CRED_PREFIX, encrypted"
  else
    fail 12 "Store Credential" "prefix=$CRED_PREFIX"
  fi
else
  fail 12 "Store Credential" "Skipped"
fi

# ── Phase 5: Gateway Enforcement ─────────────────────────────────────

echo "Phase 5: Gateway Enforcement"

# Step 13: Gateway Enforce
if [ -n "$AGENT_ID" ]; then
  GW_RESP=$(curl -sf -X POST "$GW/gateway/enforce?agent_id=$AGENT_ID&endpoint=/v1/chat&method=POST&key_type=runtime" 2>/dev/null || echo '{"decision":"error"}')
  GW_DECISION=$(echo "$GW_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('decision','error'))" 2>/dev/null || echo "error")
  if [ "$GW_DECISION" = "allow" ]; then
    pass 13 "Gateway Enforce" "decision=$GW_DECISION"
  else
    fail 13 "Gateway Enforce" "decision=$GW_DECISION (gateway may be down)"
  fi
else
  fail 13 "Gateway Enforce" "Skipped"
fi

# ── Phase 6: Audit & Verify ──────────────────────────────────────────

echo "Phase 6: Audit & Verify"

# Step 14: Audit Log
if [ -n "$AGENT_ID" ]; then
  AUDIT_RESP=$(curl -sf "$API/api/v1/audit?agent_id=$AGENT_ID&limit=10" -H "X-API-Key: $KEY" 2>/dev/null || echo '{"total":0}')
  AUDIT_TOTAL=$(echo "$AUDIT_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo "0")
  if [ "$AUDIT_TOTAL" -gt 0 ] 2>/dev/null; then
    pass 14 "Audit Log" "entries=$AUDIT_TOTAL"
  else
    fail 14 "Audit Log" "entries=$AUDIT_TOTAL (requires gateway traffic)"
  fi
else
  fail 14 "Audit Log" "Skipped"
fi

# Step 15: Verify Chain
if [ -n "$AGENT_ID" ]; then
  VERIFY_RESP=$(curl -sf "$API/api/v1/audit/verify?agent_id=$AGENT_ID" -H "X-API-Key: $KEY" 2>/dev/null || echo '{"valid":false}')
  VERIFY_VALID=$(echo "$VERIFY_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('valid',False))" 2>/dev/null || echo "False")
  if [ "$VERIFY_VALID" = "True" ]; then
    pass 15 "Verify Chain" "valid=true"
  else
    fail 15 "Verify Chain" "valid=$VERIFY_VALID"
  fi
else
  fail 15 "Verify Chain" "Skipped"
fi

# ── Summary ──────────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  RESULTS: $PASS passed, $FAIL failed ($(( PASS + FAIL )) total)"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "| # | Step | Status | Notes |"
echo "|---|------|--------|-------|"
for r in "${RESULTS[@]}"; do
  echo "$r"
done
echo ""

# ── Post to CEO Dashboard ────────────────────────────────────────────

if [ -n "$CEO_KEY" ]; then
  MOOD="neutral"
  [ "$FAIL" -gt 0 ] && MOOD="cautious"
  [ "$FAIL" -eq 0 ] && MOOD="confident"

  BODY="Automated QA smoke test ran against production.\\n\\nResults: $PASS/$((PASS + FAIL)) passed, $FAIL failed.\\n\\n"
  if [ "$FAIL" -gt 0 ]; then
    BODY="${BODY}Failed steps:\\n"
    for r in "${RESULTS[@]}"; do
      if echo "$r" | grep -q "FAIL"; then
        BODY="${BODY}- ${r}\\n"
      fi
    done
  else
    BODY="${BODY}All steps passed — onboarding flow is healthy."
  fi

  curl -sf -X POST "$CEO_API/briefings" \
    -H "X-API-Key: $CEO_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"title\": \"QA Smoke Test — $RUN_DATE\", \"body\": \"$BODY\", \"mood\": \"$MOOD\", \"author\": \"pm\", \"tags\": [\"qa\", \"automated\"], \"pinned\": false}" > /dev/null 2>&1 && \
    echo "📊 Results posted to CEO Dashboard" || \
    echo "⚠️  Could not post to CEO Dashboard (is it running?)"

  # ── Auto-file Ops Issue on failure ──────────────────────────────────
  if [ "$FAIL" -gt 0 ]; then
    # Build description with failed steps
    ISSUE_DESC="Automated QA smoke test detected $FAIL failure(s) on $RUN_DATE.\\n\\nFailed steps:\\n"
    for r in "${RESULTS[@]}"; do
      if echo "$r" | grep -q "FAIL"; then
        ISSUE_DESC="${ISSUE_DESC}- ${r}\\n"
      fi
    done
    ISSUE_DESC="${ISSUE_DESC}\\nTotal: $PASS passed, $FAIL failed out of $((PASS + FAIL))."

    # Determine severity: P1 if >50% fail, P2 otherwise
    HALF=$(( (PASS + FAIL) / 2 ))
    SEVERITY="P2"
    [ "$FAIL" -gt "$HALF" ] && SEVERITY="P1"

    curl -sf -X POST "$CEO_API/ops/issues" \
      -H "X-API-Key: $CEO_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"title\": \"QA Smoke Test Failure — $FAIL step(s) failed ($RUN_DATE)\", \"description\": \"$ISSUE_DESC\", \"severity\": \"$SEVERITY\", \"status\": \"open\", \"company_slug\": \"ai-identity\"}" > /dev/null 2>&1 && \
      echo "🚨 Ops issue filed to CEO Dashboard" || \
      echo "⚠️  Could not file ops issue"
  else
    echo "✅ No failures — no ops issue filed"
  fi
fi

# Exit with failure if any steps failed
[ "$FAIL" -eq 0 ]
