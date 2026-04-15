#!/usr/bin/env bash
# Create or update the `ai-identity-armor` Cloud Armor security policy.
#
# Idempotent — safe to re-run. Creates the policy if missing, then ensures
# adaptive DDoS protection, the six preconfigured WAF rule sets (in enforce
# mode), and a per-IP throttle rule exist.
#
# After this runs, k8s/backend-config.yaml references the policy by name, and
# the ingress backend services inherit it automatically.
#
# Usage:
#   scripts/setup-cloud-armor.sh [PROJECT_ID]
#
# History: WAF rules originally shipped in `--preview` mode. Preview traffic
# (7 days, 13 hits) was reviewed in Cloud Logging and confirmed to be entirely
# hostile scanner traffic (LFI probes for .env/.aws/credentials, RCE POSTs to
# `/` from rotating fake user agents) with zero legitimate requests caught.
# Rules were promoted to enforce. This script now creates new rules directly
# in enforce mode and will auto-promote any lingering preview rules on re-run.
#
# To re-inspect decisions: resource.type="http_load_balancer"
# jsonPayload.enforcedSecurityPolicy.name="ai-identity-armor"
# jsonPayload.enforcedSecurityPolicy.outcome="DENY"

set -euo pipefail

PROJECT_ID="${1:-project-8bbb04f8-fda8-462e-bc2}"
POLICY="ai-identity-armor"

echo "→ project: $PROJECT_ID"
echo "→ policy:  $POLICY"

# ---- 1. Create policy if missing -------------------------------------------
if gcloud compute security-policies describe "$POLICY" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "✓ policy exists"
else
  echo "• creating policy"
  gcloud compute security-policies create "$POLICY" --project="$PROJECT_ID" \
    --description="AI Identity WAF + adaptive DDoS + per-IP throttling. WAF rules in enforce mode."
fi

# ---- 2. Enable adaptive L7 DDoS protection ---------------------------------
echo "• ensuring adaptive L7 DDoS protection is enabled"
gcloud compute security-policies update "$POLICY" --project="$PROJECT_ID" \
  --enable-layer7-ddos-defense >/dev/null

# ---- 3. WAF preconfigured rules (enforce mode) ------------------------------
#
# priority | ruleset                       | description
# ---------|-------------------------------|---------------------------------
# 1000     | sqli-v33-stable               | SQL injection
# 1100     | xss-v33-stable                | Cross-site scripting
# 1200     | lfi-v33-stable                | Local file inclusion
# 1300     | rfi-v33-stable                | Remote file inclusion
# 1400     | rce-v33-stable                | Remote code execution
# 1500     | scannerdetection-v33-stable   | Scanner / probe detection
declare -a WAF_RULES=(
  "1000|sqli-v33-stable|sql_injection"
  "1100|xss-v33-stable|cross_site_scripting"
  "1200|lfi-v33-stable|local_file_inclusion"
  "1300|rfi-v33-stable|remote_file_inclusion"
  "1400|rce-v33-stable|remote_code_execution"
  "1500|scannerdetection-v33-stable|scanner_probes"
)

for spec in "${WAF_RULES[@]}"; do
  IFS='|' read -r priority ruleset label <<< "$spec"
  if gcloud compute security-policies rules describe "$priority" \
      --security-policy="$POLICY" --project="$PROJECT_ID" >/dev/null 2>&1; then
    # Ensure rule is in enforce mode (idempotently promotes any leftover preview rules)
    is_preview=$(gcloud compute security-policies rules describe "$priority" \
      --security-policy="$POLICY" --project="$PROJECT_ID" --format='value(preview)')
    if [[ "$is_preview" == "True" ]]; then
      echo "• promoting WAF rule $priority ($label) from preview → enforce"
      gcloud compute security-policies rules update "$priority" \
        --security-policy="$POLICY" --project="$PROJECT_ID" \
        --no-preview \
        --description="WAF: $label (enforced)" >/dev/null
    else
      echo "✓ WAF rule $priority ($label) exists (enforced)"
    fi
  else
    echo "• creating WAF rule $priority ($label) in enforce mode"
    gcloud compute security-policies rules create "$priority" \
      --security-policy="$POLICY" --project="$PROJECT_ID" \
      --expression="evaluatePreconfiguredWaf('$ruleset', {'sensitivity': 1})" \
      --action=deny-403 \
      --description="WAF: $label (enforced)"
  fi
done

# ---- 4. Per-IP throttle (enforced — safety net above Redis rate limiter) ---
if gcloud compute security-policies rules describe 2000 \
    --security-policy="$POLICY" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "✓ throttle rule 2000 exists"
else
  echo "• creating throttle rule 2000 (300 req/min per IP, enforced)"
  gcloud compute security-policies rules create 2000 \
    --security-policy="$POLICY" --project="$PROJECT_ID" \
    --src-ip-ranges='*' \
    --action=throttle \
    --rate-limit-threshold-count=300 \
    --rate-limit-threshold-interval-sec=60 \
    --conform-action=allow \
    --exceed-action=deny-429 \
    --enforce-on-key=IP \
    --description="Per-IP throttle: 300 req/min (edge safety net above gateway rate limiter)"
fi

echo
echo "=== Final policy state ==="
gcloud compute security-policies describe "$POLICY" --project="$PROJECT_ID" \
  --format='value(name,adaptiveProtectionConfig.layer7DdosDefenseConfig.enable)'
echo
gcloud compute security-policies rules describe 2000 \
  --security-policy="$POLICY" --project="$PROJECT_ID" \
  --format='value(priority,action,rateLimitOptions.rateLimitThreshold.count)' 2>/dev/null || true

echo
echo "✓ done. k8s/backend-config.yaml references '$POLICY' and the ingress"
echo "  backend services inherit it via cloud.google.com/backend-config annotation"
echo "  on k8s/api-service.yaml and k8s/gateway-service.yaml."
