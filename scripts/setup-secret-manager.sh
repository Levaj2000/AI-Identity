#!/usr/bin/env bash
# Provision Secret Manager + Workload Identity + audit logs for ai-identity.
#
# Idempotent — safe to re-run. Performs all of:
#   1. Enable Secret Manager API
#   2. Enable Data Access audit logs for secretmanager.googleapis.com
#   3. Enable the GKE Autopilot managed Secret Manager CSI addon
#   4. Create GCP service account `ai-identity-workload@...`
#   5. Mirror the 11 non-Stripe-price-ID keys from the K8s Secret
#      `ai-identity-secrets` into Secret Manager as `ai-identity-<KEY>`,
#      with per-secret IAM grants to the workload SA
#   6. Create K8s ServiceAccount `ai-identity-workload` + Workload
#      Identity binding to the GCP SA
#
# After this script, apply k8s/serviceaccount.yaml + k8s/secretproviderclass.yaml
# + the updated deployments / cronjobs, and the Secret Manager CSI driver
# will synthesize the `ai-identity-secrets-synced` K8s Secret consumed by
# the workloads via envFrom.
#
# Usage:
#   scripts/setup-secret-manager.sh [PROJECT_ID]
#
# Requires: gcloud authenticated, kubectl pointed at the ai-identity cluster,
# and the source K8s Secret `ai-identity-secrets` still present in the
# `ai-identity` namespace (this script reads values from it to populate SM).

set -euo pipefail

PROJECT_ID="${1:-project-8bbb04f8-fda8-462e-bc2}"
CLUSTER="ai-identity"
REGION="us-east1"
NS="ai-identity"
SA_NAME="ai-identity-workload"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Secrets that MUST stay in Secret Manager (the 4 Stripe price IDs are public
# Stripe product IDs, not sensitive — they live in k8s/configmap.yaml).
SECRETS=(
  AUDIT_HMAC_KEY
  CLERK_ISSUER
  CREDENTIAL_ENCRYPTION_KEY
  DATABASE_URL
  INTERNAL_SERVICE_KEY
  PERPLEXITY_API_KEY
  REDIS_URL
  RESEND_API_KEY
  SENTRY_DSN
  STRIPE_SECRET_KEY
  STRIPE_WEBHOOK_SECRET
)

echo "→ project: $PROJECT_ID"
echo "→ cluster: $CLUSTER ($REGION)"
echo

# ---- 1. Enable Secret Manager API ------------------------------------------
echo "• ensuring Secret Manager API is enabled"
gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID" >/dev/null
echo "✓ secretmanager.googleapis.com enabled"

# ---- 2. Data Access audit logs ---------------------------------------------
echo "• ensuring Data Access audit logs for Secret Manager"
TMP_POLICY=$(mktemp)
trap 'rm -f "$TMP_POLICY"' EXIT
gcloud projects get-iam-policy "$PROJECT_ID" --format=json > "$TMP_POLICY"
python3 - "$TMP_POLICY" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as f: p = json.load(f)
cfg = p.setdefault('auditConfigs', [])
svc = 'secretmanager.googleapis.com'
existing = next((c for c in cfg if c.get('service') == svc), None)
want = {'ADMIN_READ','DATA_READ','DATA_WRITE'}
changed = False
if existing:
    have = {c['logType'] for c in existing.get('auditLogConfigs', [])}
    missing = want - have
    if missing:
        existing.setdefault('auditLogConfigs', []).extend(
            {'logType': t} for t in sorted(missing)
        )
        changed = True
else:
    cfg.append({
        'service': svc,
        'auditLogConfigs': [{'logType': t} for t in sorted(want)],
    })
    changed = True
if changed:
    with open(path, 'w') as f: json.dump(p, f)
    print('  audit config updated', file=sys.stderr)
else:
    print('  audit config already current', file=sys.stderr)
PY
gcloud projects set-iam-policy "$PROJECT_ID" "$TMP_POLICY" >/dev/null 2>&1
echo "✓ audit logs (ADMIN_READ/DATA_READ/DATA_WRITE) applied"

# ---- 3. GKE Autopilot Secret Manager addon ---------------------------------
echo "• ensuring GKE Autopilot Secret Manager CSI addon"
SM_ENABLED=$(gcloud container clusters describe "$CLUSTER" --region="$REGION" \
  --project="$PROJECT_ID" --format='value(secretManagerConfig.enabled)' 2>/dev/null || echo "")
if [[ "$SM_ENABLED" == "True" ]]; then
  echo "✓ addon already enabled"
else
  echo "• enabling (takes ~3-5 minutes for the cluster update to settle)"
  gcloud container clusters update "$CLUSTER" --region="$REGION" \
    --project="$PROJECT_ID" --enable-secret-manager >/dev/null
  echo "✓ addon enabled"
fi

# ---- 4. GCP service account -------------------------------------------------
echo "• ensuring GCP service account $SA_EMAIL"
if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "✓ GCP SA exists"
else
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name="AI Identity Workload (Secret Manager accessor)" \
    --project="$PROJECT_ID" >/dev/null
  echo "✓ GCP SA created"
fi

# ---- 5. Mirror K8s Secret → Secret Manager (per-secret IAM) -----------------
echo "• mirroring 11 secrets to Secret Manager + granting per-secret IAM"
if ! kubectl get secret ai-identity-secrets -n "$NS" >/dev/null 2>&1; then
  echo "✗ source K8s Secret ai-identity-secrets not found — nothing to mirror"
  echo "  (this is expected after Phase 3 cleanup; skip the mirror step)"
else
  for k in "${SECRETS[@]}"; do
    NAME="ai-identity-${k}"
    VALUE=$(kubectl get secret ai-identity-secrets -n "$NS" \
      -o jsonpath="{.data.${k}}" 2>/dev/null | base64 -d)
    if [[ -z "$VALUE" ]]; then
      echo "  ✗ $k — empty source, skip"
      continue
    fi
    if gcloud secrets describe "$NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
      CREATED="exists"
    else
      gcloud secrets create "$NAME" --replication-policy=automatic \
        --labels=app=ai-identity --project="$PROJECT_ID" >/dev/null
      CREATED="created"
    fi
    CURRENT=$(gcloud secrets versions access latest --secret="$NAME" \
      --project="$PROJECT_ID" 2>/dev/null || true)
    if [[ "$CURRENT" != "$VALUE" ]]; then
      printf '%s' "$VALUE" | gcloud secrets versions add "$NAME" \
        --data-file=- --project="$PROJECT_ID" >/dev/null
      VERSIONED="new-version"
    else
      VERSIONED="unchanged"
    fi
    gcloud secrets add-iam-policy-binding "$NAME" \
      --member="serviceAccount:${SA_EMAIL}" \
      --role=roles/secretmanager.secretAccessor \
      --project="$PROJECT_ID" --condition=None >/dev/null 2>&1
    echo "  ✓ $NAME ($CREATED, $VERSIONED)"
  done
fi

# ---- 6. K8s SA + Workload Identity binding ----------------------------------
echo "• ensuring K8s ServiceAccount + Workload Identity binding"
kubectl create serviceaccount "$SA_NAME" -n "$NS" --dry-run=client -o yaml | \
  kubectl apply -f - >/dev/null
kubectl annotate serviceaccount "$SA_NAME" -n "$NS" \
  "iam.gke.io/gcp-service-account=${SA_EMAIL}" --overwrite >/dev/null
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --role=roles/iam.workloadIdentityUser \
  --member="serviceAccount:${PROJECT_ID}.svc.id.goog[${NS}/${SA_NAME}]" \
  --project="$PROJECT_ID" --condition=None >/dev/null 2>&1
echo "✓ K8s SA ${NS}/${SA_NAME} ↔ GCP SA ${SA_EMAIL}"

echo
echo "=== done ==="
echo "Next steps:"
echo "  kubectl apply -f k8s/configmap.yaml"
echo "  kubectl apply -f k8s/serviceaccount.yaml"
echo "  kubectl apply -f k8s/secretproviderclass.yaml"
echo "  kubectl apply -f k8s/api-deployment.yaml"
echo "  kubectl apply -f k8s/gateway-deployment.yaml"
echo "  kubectl apply -f k8s/cronjob-cleanup.yaml -f k8s/cronjob-email.yaml"
echo "  # Wait for rollout to succeed, smoke-test, then:"
echo "  kubectl delete secret ai-identity-secrets -n $NS"
