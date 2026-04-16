#!/usr/bin/env bash
# Provision the forensic signer: KMS asymmetric signing key, dedicated GCP
# service account, Workload Identity binding to a dedicated K8s SA, and
# Cloud KMS Data Access audit logs. Does NOT apply the K8s ServiceAccount
# manifest — run `kubectl apply -f k8s/forensic-signer-serviceaccount.yaml`
# afterward (matches the existing setup-binauth.sh / setup-secret-manager.sh
# pattern of keeping GCP-side and cluster-side apply steps separate).
#
# Trust model (summary — full discussion lives in follow-up doc #267):
#   - KMS holds the private key; it never leaves Google's KMS boundary.
#   - The signing pod authenticates to KMS via Workload Identity, so no
#     JSON key material sits on disk anywhere.
#   - The `ai-identity-forensic-signer` service account is DEDICATED to
#     the signing path. api/gateway pods run under the general-purpose
#     `ai-identity-workload` SA, which has no KMS perms; a full compromise
#     of those pods therefore cannot forge attestations.
#   - Every Sign call is captured in Cloud Audit Logs (Data Access logs
#     on cloudkms.googleapis.com), giving a tamper-evident external record
#     of what was signed, by whom, and when.
#   - The key uses EC P-256 SHA-256 — short signatures (~64 bytes), fast
#     offline verification from a PEM public key, and broad tooling
#     support (OpenSSL, Python cryptography, Go crypto/ecdsa).
#   - Rotation is operator-triggered on a ~90-day cadence. GCP KMS does
#     NOT support scheduled rotation for ASYMMETRIC_SIGN keys (the public
#     key changes on rotation, so downstream verifiers must be re-armed
#     before the new version becomes primary — Google forces the
#     operator to drive this explicitly). To rotate:
#
#       gcloud kms keys versions create \
#         --key=session-attestation \
#         --keyring=ai-identity-forensic \
#         --location=us-east1 \
#         --primary
#
#     Old versions stay ENABLED for verification (they go DISABLED only
#     on explicit revocation), so historical attestations remain
#     verifiable across rotations. Full procedure will ship in #267.
#
# Idempotent — safe to re-run. Only takes actions needed to reach the
# target state.
#
# Usage:
#   scripts/setup-forensic-signer.sh [PROJECT_ID]

set -euo pipefail

PROJECT_ID="${1:-project-8bbb04f8-fda8-462e-bc2}"
REGION=us-east1
NS=ai-identity

KEYRING=ai-identity-forensic
KEY=session-attestation
KEY_ALGO=ec-sign-p256-sha256
KEY_PURPOSE=asymmetric-signing
# GCP KMS does not permit scheduled rotation for asymmetric signing keys;
# rotation is operator-triggered via `gcloud kms keys versions create
# --primary` on a ~90-day cadence. See the header comment for details.

GCP_SA_NAME=ai-identity-forensic-signer
GCP_SA_EMAIL="${GCP_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
K8S_SA_NAME=ai-identity-forensic-signer

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')

echo "→ project:  $PROJECT_ID ($PROJECT_NUMBER)"
echo "→ region:   $REGION"
echo "→ key:      $REGION/$KEYRING/$KEY ($KEY_ALGO, manual rotation)"
echo "→ GCP SA:   $GCP_SA_EMAIL"
echo "→ K8s SA:   $NS/$K8S_SA_NAME"
echo

# ── 1. Enable Cloud KMS API ─────────────────────────────────────────────────
echo "• ensuring Cloud KMS API enabled"
gcloud services enable cloudkms.googleapis.com --project="$PROJECT_ID" >/dev/null
echo "✓ cloudkms.googleapis.com enabled"

# ── 2. KMS keyring + asymmetric signing key ────────────────────────────────
echo "• ensuring KMS keyring + signing key"
gcloud kms keyrings describe "$KEYRING" \
  --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1 \
  || gcloud kms keyrings create "$KEYRING" \
       --location="$REGION" --project="$PROJECT_ID" >/dev/null

if gcloud kms keys describe "$KEY" \
     --keyring="$KEYRING" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "  (key already exists)"
else
  # No --rotation-period / --next-rotation-time: GCP KMS rejects those
  # flags for ASYMMETRIC_SIGN keys with INVALID_ARGUMENT. Rotation is
  # operator-triggered via `gcloud kms keys versions create --primary`.
  gcloud kms keys create "$KEY" \
    --keyring="$KEYRING" --location="$REGION" --project="$PROJECT_ID" \
    --purpose="$KEY_PURPOSE" \
    --default-algorithm="$KEY_ALGO" \
    --protection-level=software \
    --labels=component=forensic-signer,environment=production >/dev/null
fi
KEY_RESOURCE="projects/$PROJECT_ID/locations/$REGION/keyRings/$KEYRING/cryptoKeys/$KEY"
echo "✓ key: $KEY_RESOURCE"

# ── 3. Dedicated GCP service account ───────────────────────────────────────
echo "• ensuring GCP service account $GCP_SA_NAME"
gcloud iam service-accounts describe "$GCP_SA_EMAIL" \
  --project="$PROJECT_ID" >/dev/null 2>&1 \
  || gcloud iam service-accounts create "$GCP_SA_NAME" \
       --display-name="AI Identity forensic signer" \
       --description="Signs forensic attestations on session close. Dedicated SA so that api/gateway pod compromise cannot forge signatures." \
       --project="$PROJECT_ID" >/dev/null
echo "✓ GCP SA: $GCP_SA_EMAIL"

# ── 4. Key-level IAM: signerVerifier only, on this key only ────────────────
# Scoped to the specific key (not project-wide or keyring-wide) so that a
# future key added to the same keyring isn't silently signable by this SA.
echo "• granting roles/cloudkms.signerVerifier on the key"
gcloud kms keys add-iam-policy-binding "$KEY" \
  --keyring="$KEYRING" --location="$REGION" --project="$PROJECT_ID" \
  --member="serviceAccount:$GCP_SA_EMAIL" \
  --role="roles/cloudkms.signerVerifier" \
  --condition=None >/dev/null
echo "✓ roles/cloudkms.signerVerifier bound on $KEY"

# ── 5. Workload Identity: K8s SA → GCP SA ──────────────────────────────────
# Binds the `ai-identity/ai-identity-forensic-signer` K8s SA to the GCP SA
# via the project's identity pool. After this plus applying the K8s SA
# manifest, pods that set `serviceAccountName: ai-identity-forensic-signer`
# will authenticate to KMS as $GCP_SA_EMAIL with no JSON key material.
echo "• granting Workload Identity binding (K8s SA → GCP SA)"
gcloud iam service-accounts add-iam-policy-binding "$GCP_SA_EMAIL" \
  --member="serviceAccount:${PROJECT_ID}.svc.id.goog[${NS}/${K8S_SA_NAME}]" \
  --role="roles/iam.workloadIdentityUser" \
  --project="$PROJECT_ID" \
  --condition=None >/dev/null
echo "✓ Workload Identity bound: ${NS}/${K8S_SA_NAME} → $GCP_SA_EMAIL"

# ── 6. Cloud KMS Data Access audit logs ────────────────────────────────────
# Every Sign call becomes an auditable external record. Critical for the
# forensic product: the signing event itself is logged by Google outside
# our control, so even a full cluster compromise can't hide that a
# signature was produced.
echo "• ensuring Data Access audit logs for cloudkms.googleapis.com"
TMP_POLICY=$(mktemp)
trap 'rm -f "$TMP_POLICY"' EXIT
gcloud projects get-iam-policy "$PROJECT_ID" --format=json > "$TMP_POLICY"
set +e
python3 - "$TMP_POLICY" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as f:
    policy = json.load(f)
cfg = policy.setdefault('auditConfigs', [])
svc = 'cloudkms.googleapis.com'
existing = next((c for c in cfg if c.get('service') == svc), None)
want = {'ADMIN_READ', 'DATA_READ', 'DATA_WRITE'}
if existing:
    have = {c['logType'] for c in existing.get('auditLogConfigs', [])}
    missing = sorted(want - have)
    if not missing:
        sys.exit(99)  # already correct — signal "no change"
    existing.setdefault('auditLogConfigs', []).extend(
        {'logType': t} for t in missing
    )
else:
    cfg.append({
        'service': svc,
        'auditLogConfigs': [{'logType': t} for t in sorted(want)],
    })
with open(path, 'w') as f:
    json.dump(policy, f, indent=2)
PY
rc=$?
set -e
case $rc in
  0)
    gcloud projects set-iam-policy "$PROJECT_ID" "$TMP_POLICY" >/dev/null
    echo "✓ KMS Data Access audit logs updated"
    ;;
  99)
    echo "✓ KMS Data Access audit logs already enabled"
    ;;
  *)
    echo "⚠ failed to update audit logs (rc=$rc)"
    exit 1
    ;;
esac

# ── 7. Print public key + env-var hint for downstream cards ────────────────
echo
echo "── Public key for /.well-known/ai-identity-public-keys.json (card #265) ──"
PRIMARY_VERSION=$(gcloud kms keys versions list \
  --key="$KEY" --keyring="$KEYRING" --location="$REGION" --project="$PROJECT_ID" \
  --filter='state=ENABLED' \
  --format='value(name.segment(-1))' \
  --sort-by=~createTime --limit=1)
if [[ -n "${PRIMARY_VERSION:-}" ]]; then
  echo "  version: $PRIMARY_VERSION"
  gcloud kms keys versions get-public-key "$PRIMARY_VERSION" \
    --key="$KEY" --keyring="$KEYRING" --location="$REGION" --project="$PROJECT_ID" \
    2>/dev/null \
    || echo "  (public key material not yet generated — re-run in ~10s)"
else
  echo "  (no ENABLED versions yet — key generation pending; re-run in ~10s)"
fi

cat <<EOF

── Downstream configuration ────────────────────────────────────────────────

Add to the forensic-signing workload's env (card #262 payload design will
wire this up):

  FORENSIC_SIGNING_KEY=$KEY_RESOURCE

Next steps:

  kubectl apply -f k8s/forensic-signer-serviceaccount.yaml

Then sprint items #262 (payload schema) and #263 (sign on session close)
can import google-cloud-kms and issue AsymmetricSign calls against
\$FORENSIC_SIGNING_KEY.
EOF
