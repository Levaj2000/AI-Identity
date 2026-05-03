# Ada — Cloud Run deployment runbook

This is the runbook for running Ada (`agent/`) on Cloud Run. It covers
one-time setup, build + deploy, verification, rollback, and the
environment-variable contract. The companion artifacts are
[`agent/Dockerfile`](../agent/Dockerfile) and
[`agent/cloudbuild.yaml`](../agent/cloudbuild.yaml).

Closes Sprint 12 #329 — the final Level-1 production-readiness gate. Pairs
with #228 (secret-file denylist), #229 (X-Agent-Key auth + CORS lockdown),
#230 (audit-trail dogfood), and #231 (citation eval gate).

---

## Service shape

- **Runtime**: Cloud Run, fully-managed, region `us-east1` (matching the
  GKE-deployed API + gateway services per
  [`cloudbuild.yaml`](../cloudbuild.yaml) at the repo root).
- **Image**: `us-east1-docker.pkg.dev/$PROJECT_ID/ai-identity/ada:$SHORT_SHA`.
- **Ingress**: `internal-and-cloud-load-balancing` (no public reach). Callers
  must have `roles/run.invoker` on the service.
- **Auth**: every protected route requires a valid `X-Agent-Key`
  ([`agent/auth.py`](../agent/auth.py)) verified against AI Identity's
  `/api/v1/keys/verify`. Admin credential lives in Secret Manager.
- **Audit**: every tool call routes through
  [`agent/ada/audit.py`](../agent/ada/audit.py) → `/gateway/enforce`. A
  reachability failure halts Ada (synchronous-enough that AI Identity
  outage is observable).
- **Identity (workload)**: a dedicated GCP service account, bound to
  Vertex AI + the two Secret Manager secrets. No SA JSON keys.

---

## Prerequisites

Run once, by a project owner:

### 1. Enable APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com \
  --project=$PROJECT_ID
```

### 2. Artifact Registry repo

The existing `ai-identity` repo is reused. If it doesn't exist:

```bash
gcloud artifacts repositories create ai-identity \
  --repository-format=docker \
  --location=us-east1 \
  --project=$PROJECT_ID
```

### 3. Runtime service account

```bash
gcloud iam service-accounts create ada-runtime \
  --display-name="Ada — Cloud Run runtime" \
  --project=$PROJECT_ID

# Vertex AI for gemini-2.5-pro inference
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:ada-runtime@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Cloud Logging from inside the container
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:ada-runtime@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter"
```

### 4. Secrets

Two secrets, both read by the runtime SA at startup via Cloud Run's
Secret Manager integration. Plaintext values are never written to disk.

```bash
# Admin key — used by serve.py auth middleware to verify caller X-Agent-Keys.
echo -n "<admin-aid_admin_... key>" | \
  gcloud secrets create ada-admin-key \
    --data-file=- \
    --replication-policy=automatic \
    --project=$PROJECT_ID

# Runtime key — Ada's own aid_sk_ key, sent on every gateway/enforce
# audit call so the row carries her agent_id.
echo -n "<runtime-aid_sk_... key>" | \
  gcloud secrets create ada-runtime-key \
    --data-file=- \
    --replication-policy=automatic \
    --project=$PROJECT_ID

# Grant the runtime SA accessor on both secrets.
for SECRET in ada-admin-key ada-runtime-key; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:ada-runtime@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID
done
```

### 5. Cloud Build SA

Cloud Build itself needs to be allowed to deploy Cloud Run services and
act-as the runtime SA:

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$CB_SA" \
  --role="roles/run.admin"

gcloud iam service-accounts add-iam-policy-binding \
  ada-runtime@$PROJECT_ID.iam.gserviceaccount.com \
  --member="serviceAccount:$CB_SA" \
  --role="roles/iam.serviceAccountUser" \
  --project=$PROJECT_ID
```

---

## Build + deploy

From the repo root:

```bash
ADA_AGENT_ID="<ada's UUID from the AI Identity dashboard>"

gcloud builds submit \
  --config=agent/cloudbuild.yaml \
  --substitutions=SHORT_SHA=$(git rev-parse --short HEAD),_ADA_AGENT_ID=$ADA_AGENT_ID \
  --project=$PROJECT_ID \
  .
```

`SHORT_SHA` is what `/version` will report after startup. `_ADA_AGENT_ID`
must be Ada's actual agent UUID — without it `audit_action()` raises and
every tool call returns an error.

The build runs three steps in [agent/cloudbuild.yaml](../agent/cloudbuild.yaml):

1. `docker build` against [agent/Dockerfile](../agent/Dockerfile)
2. `docker push` to Artifact Registry
3. `gcloud run deploy` with workload-identity SA + Secret Manager mounts

---

## Verification

```bash
# Service URL (no public auth — needs a token)
URL=$(gcloud run services describe ada \
  --region=us-east1 --format='value(status.url)' --project=$PROJECT_ID)

# /version is public via the auth middleware allow-list. Cloud Run's
# IAM gate still requires a token at the platform layer.
TOKEN=$(gcloud auth print-identity-token)
curl -H "Authorization: Bearer $TOKEN" "$URL/version"
# → {"sha":"<SHORT_SHA>","short":"<8-char>"}

# /healthz — same auth shape, returns {"status":"ok"}
curl -H "Authorization: Bearer $TOKEN" "$URL/healthz"

# Protected route without an X-Agent-Key — must 401 (not 403, not 200)
curl -i -H "Authorization: Bearer $TOKEN" "$URL/list-apps"
# → HTTP/2 401, body: {"error":"missing X-Agent-Key header"}

# Protected route with a valid runtime X-Agent-Key — 200
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-Agent-Key: <a runtime aid_sk_... key>" \
     "$URL/list-apps"
# → ["ada"]
```

End-to-end smoke (one full Ada turn against the deployed instance):

```bash
SESSION_ID=$(curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Agent-Key: <runtime key>" \
  -H "Content-Type: application/json" \
  -d '{}' \
  "$URL/apps/ada/users/smoke/sessions" | jq -r .id)

curl -N -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Agent-Key: <runtime key>" \
  -H "Content-Type: application/json" \
  -d "{\"app_name\":\"ada\",\"user_id\":\"smoke\",\"session_id\":\"$SESSION_ID\",\"new_message\":{\"role\":\"user\",\"parts\":[{\"text\":\"What does serve.py do?\"}]}}" \
  "$URL/run_sse"
```

You should see SSE chunks with tool calls (`read_file`, `search_code`)
followed by Ada's response. Each tool call produces an
`audit_log` entry on the AI Identity side, tagged with Ada's `agent_id`.

---

## Granting access

Adding a person who needs to invoke Ada:

```bash
gcloud run services add-iam-policy-binding ada \
  --region=us-east1 \
  --member="user:someone@example.com" \
  --role="roles/run.invoker" \
  --project=$PROJECT_ID
```

For service-to-service calls (e.g., a future internal tool that calls
Ada), grant the caller's SA the same role.

---

## Rollback

Cloud Run keeps every revision. To roll back:

```bash
# List recent revisions
gcloud run revisions list --service=ada --region=us-east1 --project=$PROJECT_ID

# Send 100% of traffic to a known-good revision
gcloud run services update-traffic ada \
  --to-revisions=ada-<rev-name>=100 \
  --region=us-east1 \
  --project=$PROJECT_ID
```

For an emergency cut-off (Ada misbehaving), the fastest path is revoking
her runtime key in the AI Identity dashboard — every audit call then
returns 401, every tool call short-circuits, and the user sees
"Ada audit denied" inline. No Cloud Run deploy needed.

---

## Environment-variable contract

These are all set by [`agent/cloudbuild.yaml`](../agent/cloudbuild.yaml).
Override at deploy time only with a deliberate reason.

| Variable | Source | Purpose |
|---|---|---|
| `ADA_REQUIRE_AUTH` | env (`1`) | Enforces `X-Agent-Key` on protected routes (see [agent/auth.py](../agent/auth.py)) |
| `ADA_REQUIRE_AUDIT` | env (`1`) | Routes every tool call through `/gateway/enforce` (see [agent/ada/audit.py](../agent/ada/audit.py)) |
| `ADA_ADMIN_KEY` | secret `ada-admin-key` | Admin credential the auth middleware uses to verify caller keys |
| `AI_IDENTITY_API_KEY` | secret `ada-runtime-key` | Ada's runtime `aid_sk_...` key, sent in `X-Agent-Key` on each audit call |
| `ADA_AGENT_ID` | env (deploy substitution) | Ada's agent UUID; without it, audit calls raise |
| `AI_IDENTITY_API_URL` | env (default) | API base URL for verify-key calls |
| `AI_IDENTITY_GATEWAY_URL` | env (default) | Gateway base URL for `/gateway/enforce` |
| `GOOGLE_GENAI_USE_VERTEXAI` | env (`1`) | ADK uses Vertex AI for `gemini-2.5-pro` |
| `GOOGLE_CLOUD_PROJECT` | env (deploy) | Vertex project (workload-identity-resolved at runtime) |
| `GOOGLE_CLOUD_LOCATION` | env (deploy) | Vertex region |
| `PORT` | env (Cloud Run) | Cloud Run injects this; `serve.py` binds to it |

---

## Out of scope (Phase 2)

Documented here so the next person picking up the deploy story knows the
edges:

- **Backend nonce-replay check** on the gateway side. Ada already sends a
  per-call `X-Audit-Nonce`; the gateway accepts but does not yet verify
  uniqueness. Tracked as Phase 2 of the audit module ([agent/ada/audit.py](../agent/ada/audit.py)).
- **Custom domain + Cloud Armor**. Today the service is reachable only
  via the auto-assigned `run.app` URL plus IAM. A future deploy step
  fronts it with `ada.ai-identity.co` and Cloud Armor for WAF rules.
- **Live eval mode** (`python -m evals.run_evals --live`) wired into a
  scheduled Cloud Build trigger that exercises a real Ada turn against
  the deployed instance. Today the eval gate is static (cheap, fast).
- **Per-user rate limiting** beyond Cloud Run's default concurrency cap.
  Listed as a Level-2 concern in Insight #74.
