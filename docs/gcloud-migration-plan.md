# AI Identity: Render to Google Cloud Migration Plan

**Author:** Jeff Leva
**Date:** 2026-04-07
**Status:** Draft
**Budget:** $2,300 in Google Cloud credits (~2 years of runway)

---

## Table of Contents

1. [Architecture Overview (Current vs. Target)](#1-architecture-overview)
2. [Pre-Migration Checklist](#2-pre-migration-checklist)
3. [Phase 1: GCP Foundation](#3-phase-1-gcp-foundation)
4. [Phase 2: Container Registry](#4-phase-2-container-registry)
5. [Phase 3: Deploy Backend Services](#5-phase-3-deploy-backend-services)
6. [Phase 4: Scheduled Tasks (Cron)](#6-phase-4-scheduled-tasks)
7. [Phase 5: CI/CD Pipeline](#7-phase-5-cicd-pipeline)
8. [Phase 6: DNS & Traffic Cutover](#8-phase-6-dns--traffic-cutover)
9. [Phase 7: Monitoring & Observability](#9-phase-7-monitoring--observability)
10. [Phase 8: Cleanup](#10-phase-8-cleanup)
11. [Rollback Plan](#11-rollback-plan)
12. [Timeline](#12-timeline)
13. [Cost Projections & Credit Tracking](#13-cost-projections--credit-tracking)
14. [Appendix: Environment Variables](#appendix-environment-variables)

---

## 1. Architecture Overview

### Current State (Render + Vercel)

| Component | Platform | URL / Config |
|-----------|----------|-------------|
| **API Server** (FastAPI/Gunicorn) | Render Web Service (Starter) | `ai-identity-api.onrender.com` |
| **Gateway** (FastAPI/Gunicorn) | Render Web Service (Starter) | `ai-identity-gateway.onrender.com` |
| **Keepalive Cron** | Render Cron Job (Starter) | Every 10 min; also triggers daily email + weekly cleanup |
| **Dashboard** (Vite/React SPA) | Vercel | `dashboard.ai-identity.co` |
| **Landing Page** (Next.js) | Vercel | `ai-identity.co` |
| **Database** | Neon Postgres (external) | Stays as-is -- no migration needed |
| **Redis** (Gateway rate limiting) | External (likely Upstash or Render Redis) | Referenced via `REDIS_URL` env var |
| **Auth** | Clerk (external) | Stays as-is |
| **Email** | Resend (external) | Stays as-is |
| **Payments** | Stripe (external) | Stays as-is |
| **Error Monitoring** | Sentry (external) | Stays as-is |
| **SDK** | PyPI (langchain-ai-identity) | Published via GitHub Actions -- no change |

### Target State (Google Cloud)

| Component | GCP Service | Why |
|-----------|-------------|-----|
| **API Server** | Cloud Run | Serverless containers, scale-to-zero, pay-per-request |
| **Gateway** | Cloud Run | Same -- separate service for independent scaling |
| **Keepalive / Cron** | Cloud Scheduler + Cloud Run Jobs | Replaces Render cron; triggers HTTP calls or runs containers |
| **Secrets** | Secret Manager | Replaces Render env var sync |
| **Container Images** | Artifact Registry | Replaces Render's built-in Docker builder |
| **CI/CD** | GitHub Actions (existing) + `gcloud` CLI | Keeps familiar workflow; deploys to Cloud Run |
| **Dashboard** | Vercel (unchanged) | Already optimal for SPA; just update API URL |
| **Landing Page** | Vercel (unchanged) | Already optimal for Next.js |
| **DNS** | Cloud DNS (optional) or existing registrar | Only if you want consolidated DNS management |

### What Does NOT Migrate

- **Neon Postgres** -- stays external, no changes
- **Vercel frontends** -- dashboard and landing page stay on Vercel
- **Clerk, Stripe, Resend, Sentry** -- all external SaaS, no changes
- **GitHub Actions CI** -- stays, just add a deploy step
- **PyPI SDK publishing** -- unchanged

---

## 2. Pre-Migration Checklist

Complete these before writing any `gcloud` commands:

- [ ] **Google Cloud Startup Program** -- confirm acceptance and credit disbursement
- [ ] **Google account** -- decide which Google account owns the GCP project (use a company account, not personal)
- [ ] **Domain verification** -- verify `ai-identity.co` in Google Search Console (needed for custom domain mapping)
- [ ] **Inventory secrets** -- export a list of all Render env vars (see [Appendix](#appendix-environment-variables))
- [ ] **Notify stakeholders** -- brief anyone who has Render dashboard access
- [ ] **Backup current Render config** -- screenshot or export all Render service settings
- [ ] **Test Docker build locally** -- ensure `docker compose build` works with current Dockerfile

---

## 3. Phase 1: GCP Foundation

### 3.1 Create Project and Enable Billing

```bash
# Create the GCP project
gcloud projects create ai-identity-prod \
  --name="AI Identity Production" \
  --set-as-default

# Link billing account (get your billing account ID from console)
gcloud billing accounts list
gcloud billing projects link ai-identity-prod \
  --billing-account=BILLING_ACCOUNT_ID

# Set default project
gcloud config set project ai-identity-prod
```

### 3.2 Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  cloudbuild.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudtrace.googleapis.com
```

### 3.3 Set Default Region

Cloud Run in `us-west1` (Oregon) matches your current Render region and is close to Neon's likely US region.

```bash
gcloud config set run/region us-west1
```

### 3.4 IAM: Create a Deploy Service Account

```bash
# Create service account for CI/CD deploys
gcloud iam service-accounts create github-deployer \
  --display-name="GitHub Actions Deployer"

# Grant required roles
PROJECT_ID=ai-identity-prod
SA=github-deployer@${PROJECT_ID}.iam.gserviceaccount.com

for ROLE in \
  roles/run.admin \
  roles/artifactregistry.writer \
  roles/secretmanager.secretAccessor \
  roles/iam.serviceAccountUser \
  roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA" \
    --role="$ROLE"
done
```

### 3.5 Set Up Workload Identity Federation (for GitHub Actions)

This avoids storing long-lived JSON keys in GitHub Secrets.

```bash
# Create workload identity pool
gcloud iam workload-identity-pools create github-pool \
  --location=global \
  --display-name="GitHub Actions Pool"

# Create OIDC provider for GitHub
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global \
  --workload-identity-pool=github-pool \
  --display-name="GitHub OIDC" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# Allow your repo to impersonate the service account
# Replace YOUR_ORG/YOUR_REPO with your actual GitHub repo
gcloud iam service-accounts add-iam-policy-binding $SA \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_ORG/AI-Identity"
```

### 3.6 Secrets Management

Migrate every Render `sync: false` env var into Secret Manager:

```bash
# Create each secret (repeat for each secret)
echo -n "YOUR_DATABASE_URL_VALUE" | \
  gcloud secrets create DATABASE_URL --data-file=- --replication-policy=automatic

echo -n "YOUR_AUDIT_HMAC_KEY_VALUE" | \
  gcloud secrets create AUDIT_HMAC_KEY --data-file=- --replication-policy=automatic

echo -n "YOUR_CREDENTIAL_ENCRYPTION_KEY_VALUE" | \
  gcloud secrets create CREDENTIAL_ENCRYPTION_KEY --data-file=- --replication-policy=automatic

echo -n "YOUR_INTERNAL_SERVICE_KEY_VALUE" | \
  gcloud secrets create INTERNAL_SERVICE_KEY --data-file=- --replication-policy=automatic

echo -n "YOUR_CLERK_ISSUER_VALUE" | \
  gcloud secrets create CLERK_ISSUER --data-file=- --replication-policy=automatic

echo -n "YOUR_REDIS_URL_VALUE" | \
  gcloud secrets create REDIS_URL --data-file=- --replication-policy=automatic

# Stripe secrets
for SECRET in STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET \
  STRIPE_PRICE_ID_PRO STRIPE_PRICE_ID_BUSINESS \
  STRIPE_PRICE_ID_PRO_ANNUAL STRIPE_PRICE_ID_BUSINESS_ANNUAL; do
  echo -n "VALUE_HERE" | \
    gcloud secrets create $SECRET --data-file=- --replication-policy=automatic
done

# Resend
echo -n "YOUR_RESEND_API_KEY" | \
  gcloud secrets create RESEND_API_KEY --data-file=- --replication-policy=automatic

# Sentry
echo -n "YOUR_SENTRY_DSN" | \
  gcloud secrets create SENTRY_DSN --data-file=- --replication-policy=automatic

# Grant Cloud Run service account access to secrets
RUN_SA=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')-compute@developer.gserviceaccount.com

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$RUN_SA" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 4. Phase 2: Container Registry

### 4.1 Create Artifact Registry Repository

```bash
gcloud artifacts repositories create ai-identity \
  --repository-format=docker \
  --location=us-west1 \
  --description="AI Identity container images"
```

### 4.2 Configure Docker Authentication

```bash
gcloud auth configure-docker us-west1-docker.pkg.dev
```

### 4.3 Build and Push Images

The existing Dockerfile uses a `SERVICE` build arg to create per-service images. Build one image per service:

```bash
IMAGE_BASE=us-west1-docker.pkg.dev/ai-identity-prod/ai-identity

# Build and push API image
docker build --build-arg SERVICE=api -t $IMAGE_BASE/api:latest .
docker push $IMAGE_BASE/api:latest

# Build and push Gateway image
docker build --build-arg SERVICE=gateway -t $IMAGE_BASE/gateway:latest .
docker push $IMAGE_BASE/gateway:latest
```

### 4.4 Verify

```bash
gcloud artifacts docker images list us-west1-docker.pkg.dev/ai-identity-prod/ai-identity
```

---

## 5. Phase 3: Deploy Backend Services

### 5.1 Deploy the API Service

```bash
PROJECT_ID=ai-identity-prod
IMAGE=us-west1-docker.pkg.dev/$PROJECT_ID/ai-identity/api:latest

gcloud run deploy ai-identity-api \
  --image=$IMAGE \
  --region=us-west1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8001 \
  --cpu=1 \
  --memory=512Mi \
  --min-instances=1 \
  --max-instances=3 \
  --timeout=120 \
  --concurrency=80 \
  --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO,CORS_ORIGINS=https://ai-identity.co\,https://www.ai-identity.co\,https://dashboard.ai-identity.co\,http://localhost:5173,CORS_ORIGIN_REGEX=https://dashboard-.*-jeff-levas-projects\.vercel\.app,GATEWAY_URL=https://ai-identity-gateway-HASH-uw.a.run.app" \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest,AUDIT_HMAC_KEY=AUDIT_HMAC_KEY:latest,CREDENTIAL_ENCRYPTION_KEY=CREDENTIAL_ENCRYPTION_KEY:latest,INTERNAL_SERVICE_KEY=INTERNAL_SERVICE_KEY:latest,CLERK_ISSUER=CLERK_ISSUER:latest,STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest,STRIPE_WEBHOOK_SECRET=STRIPE_WEBHOOK_SECRET:latest,RESEND_API_KEY=RESEND_API_KEY:latest,SENTRY_DSN=SENTRY_DSN:latest" \
  --command="sh" \
  --args="-c,alembic upgrade head && gunicorn api.app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001 --timeout 120 --keep-alive 5"
```

> **Note on `min-instances=1`:** This eliminates cold starts (a key pain point with Render Starter). Cost is ~$0.50/day for an always-warm instance. If budget is tight, set to `0` and use Cloud Scheduler keepalive instead.

### 5.2 Deploy the Gateway Service

```bash
gcloud run deploy ai-identity-gateway \
  --image=us-west1-docker.pkg.dev/$PROJECT_ID/ai-identity/gateway:latest \
  --region=us-west1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8002 \
  --cpu=1 \
  --memory=512Mi \
  --min-instances=1 \
  --max-instances=3 \
  --timeout=120 \
  --concurrency=80 \
  --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO,CORS_ORIGINS=https://ai-identity.co\,https://www.ai-identity.co\,https://dashboard.ai-identity.co\,http://localhost:5173,CORS_ORIGIN_REGEX=https://dashboard-.*-jeff-levas-projects\.vercel\.app" \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest,AUDIT_HMAC_KEY=AUDIT_HMAC_KEY:latest,CREDENTIAL_ENCRYPTION_KEY=CREDENTIAL_ENCRYPTION_KEY:latest,INTERNAL_SERVICE_KEY=INTERNAL_SERVICE_KEY:latest,REDIS_URL=REDIS_URL:latest,SENTRY_DSN=SENTRY_DSN:latest" \
  --command="gunicorn" \
  --args="gateway.app.main:app,--workers,2,--worker-class,uvicorn.workers.UvicornWorker,--bind,0.0.0.0:8002,--timeout,120,--keep-alive,5"
```

### 5.3 Verify Deployments

```bash
# Get service URLs
API_URL=$(gcloud run services describe ai-identity-api --region=us-west1 --format='value(status.url)')
GW_URL=$(gcloud run services describe ai-identity-gateway --region=us-west1 --format='value(status.url)')

echo "API: $API_URL"
echo "Gateway: $GW_URL"

# Health checks
curl -sf "$API_URL/health"
curl -sf "$GW_URL/health"
```

### 5.4 Update Gateway URL in API Config

After getting the Gateway's Cloud Run URL, update the API's `GATEWAY_URL`:

```bash
gcloud run services update ai-identity-api \
  --region=us-west1 \
  --update-env-vars="GATEWAY_URL=$GW_URL"
```

---

## 6. Phase 4: Scheduled Tasks

The current Render cron job (`keepalive_cron.py`) does three things:

1. **Keepalive pings** every 10 min -- **no longer needed** if using `min-instances=1` on Cloud Run
2. **Follow-up emails** daily at 16:00 UTC -- migrate to Cloud Scheduler
3. **Inactive user cleanup** weekly on Sundays at 04:00 UTC -- migrate to Cloud Scheduler

### 6.1 Daily Follow-up Emails

```bash
API_URL=$(gcloud run services describe ai-identity-api --region=us-west1 --format='value(status.url)')

gcloud scheduler jobs create http ai-identity-followup-emails \
  --location=us-west1 \
  --schedule="0 16 * * *" \
  --time-zone="UTC" \
  --uri="$API_URL/api/internal/email/send-followups" \
  --http-method=POST \
  --headers="x-internal-key=INTERNAL_SERVICE_KEY_VALUE" \
  --attempt-deadline=60s \
  --description="Daily follow-up email check for new users"
```

> **Security note:** For production, use an OIDC token instead of the plain header. Create a Cloud Scheduler service account and configure the API to accept OIDC tokens from it. Alternatively, store the internal key in Secret Manager and use a Cloud Run job wrapper.

### 6.2 Weekly Inactive User Cleanup

```bash
gcloud scheduler jobs create http ai-identity-user-cleanup \
  --location=us-west1 \
  --schedule="0 4 * * 0" \
  --time-zone="UTC" \
  --uri="$API_URL/api/internal/cleanup/inactive-users?inactivity_days=90&dry_run=false" \
  --http-method=POST \
  --headers="x-internal-key=INTERNAL_SERVICE_KEY_VALUE" \
  --attempt-deadline=120s \
  --description="Weekly cleanup of inactive free-tier users"
```

### 6.3 Optional: Keepalive (only if min-instances=0)

If you decide to use `min-instances=0` to save costs, add a keepalive job:

```bash
gcloud scheduler jobs create http ai-identity-keepalive \
  --location=us-west1 \
  --schedule="*/10 * * * *" \
  --time-zone="UTC" \
  --uri="$API_URL/health" \
  --http-method=GET \
  --attempt-deadline=30s \
  --description="Keep Cloud Run warm (only needed if min-instances=0)"
```

---

## 7. Phase 5: CI/CD Pipeline

### 7.1 GitHub Actions Deploy Workflow

Create `.github/workflows/deploy-gcp.yml`:

```yaml
name: Deploy to Google Cloud

on:
  push:
    branches: [main]

env:
  PROJECT_ID: ai-identity-prod
  REGION: us-west1
  REGISTRY: us-west1-docker.pkg.dev/ai-identity-prod/ai-identity

jobs:
  # Run existing CI checks first
  ci:
    uses: ./.github/workflows/ci.yml

  deploy-api:
    name: Deploy API to Cloud Run
    needs: ci
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write  # Required for Workload Identity Federation

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider
          service_account: github-deployer@ai-identity-prod.iam.gserviceaccount.com

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker
        run: gcloud auth configure-docker us-west1-docker.pkg.dev --quiet

      - name: Build and push API image
        run: |
          docker build --build-arg SERVICE=api \
            -t ${{ env.REGISTRY }}/api:${{ github.sha }} \
            -t ${{ env.REGISTRY }}/api:latest \
            .
          docker push ${{ env.REGISTRY }}/api:${{ github.sha }}
          docker push ${{ env.REGISTRY }}/api:latest

      - name: Deploy API to Cloud Run
        run: |
          gcloud run deploy ai-identity-api \
            --image=${{ env.REGISTRY }}/api:${{ github.sha }} \
            --region=${{ env.REGION }} \
            --quiet

  deploy-gateway:
    name: Deploy Gateway to Cloud Run
    needs: ci
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider
          service_account: github-deployer@ai-identity-prod.iam.gserviceaccount.com

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker
        run: gcloud auth configure-docker us-west1-docker.pkg.dev --quiet

      - name: Build and push Gateway image
        run: |
          docker build --build-arg SERVICE=gateway \
            -t ${{ env.REGISTRY }}/gateway:${{ github.sha }} \
            -t ${{ env.REGISTRY }}/gateway:latest \
            .
          docker push ${{ env.REGISTRY }}/gateway:${{ github.sha }}
          docker push ${{ env.REGISTRY }}/gateway:latest

      - name: Deploy Gateway to Cloud Run
        run: |
          gcloud run deploy ai-identity-gateway \
            --image=${{ env.REGISTRY }}/gateway:${{ github.sha }} \
            --region=${{ env.REGION }} \
            --quiet
```

### 7.2 GitHub Secrets to Configure

Add these in GitHub repo Settings > Secrets and variables > Actions:

| Secret Name | Value |
|-------------|-------|
| `GCP_PROJECT_NUMBER` | Your GCP project number (numeric) |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Full provider resource name |
| `GCP_SERVICE_ACCOUNT` | `github-deployer@ai-identity-prod.iam.gserviceaccount.com` |

### 7.3 Update QA Smoke Test

Update `scripts/qa-smoke-test.sh` defaults to point to Cloud Run URLs:

```bash
# Old:
API="${1:-https://ai-identity-api.onrender.com}"
GW="${2:-https://ai-identity-gateway.onrender.com}"

# New (after custom domain setup):
API="${1:-https://api.ai-identity.co}"
GW="${2:-https://gateway.ai-identity.co}"
```

Also update `scripts/keepalive_cron.py` service URLs (or delete the file entirely since Cloud Scheduler replaces it).

---

## 8. Phase 6: DNS & Traffic Cutover

### 8.1 Custom Domain Mapping on Cloud Run

```bash
# Map custom domains (requires domain verification in Google Search Console)
gcloud run domain-mappings create \
  --service=ai-identity-api \
  --domain=api.ai-identity.co \
  --region=us-west1

gcloud run domain-mappings create \
  --service=ai-identity-gateway \
  --domain=gateway.ai-identity.co \
  --region=us-west1
```

Cloud Run will provide DNS records (CNAME) to add at your registrar.

### 8.2 Update DNS Records

At your domain registrar, add the CNAME records that Cloud Run provides:

```
api.ai-identity.co    CNAME    ghs.googlehosted.com.
gateway.ai-identity.co CNAME   ghs.googlehosted.com.
```

### 8.3 Update Frontend References

After DNS propagation (~1-24 hours):

1. **Dashboard `vercel.json`** -- update API rewrite destination:
   ```json
   {
     "rewrites": [
       { "source": "/api/(.*)", "destination": "https://api.ai-identity.co/api/$1" },
       { "source": "/health", "destination": "https://api.ai-identity.co/health" }
     ]
   }
   ```

2. **Dashboard CI** -- update `VITE_API_BASE_URL` in `.github/workflows/ci.yml`:
   ```yaml
   env:
     VITE_API_BASE_URL: https://api.ai-identity.co
   ```

3. **CORS origins** -- update the Cloud Run env vars to include any new domains.

4. **Stripe webhook endpoint** -- update in Stripe Dashboard to point to the new API URL.

### 8.4 Cutover Strategy

Use a **gradual cutover** approach:

1. Deploy to Cloud Run, verify with direct Cloud Run URLs
2. Run QA smoke test against Cloud Run URLs
3. Set up custom domains, wait for DNS propagation
4. Update Vercel rewrites to point to new API
5. Monitor for 48 hours
6. If stable, proceed to Render decommission

---

## 9. Phase 7: Monitoring & Observability

### 9.1 Cloud Run Metrics (Automatic)

Cloud Run automatically provides:
- Request count, latency, error rate
- Container instance count
- CPU and memory utilization
- Cold start frequency

View at: `console.cloud.google.com/run` > select service > Metrics tab.

### 9.2 Structured Logging

Cloud Run logs are automatically sent to Cloud Logging. Since the app already uses Python `logging`, logs will appear in the Logs Explorer.

View at: `console.cloud.google.com/logs`

### 9.3 Uptime Checks

```bash
# Create uptime check for API
gcloud monitoring uptime create ai-identity-api-health \
  --display-name="AI Identity API Health" \
  --resource-type=uptime-url \
  --hostname=api.ai-identity.co \
  --path=/health \
  --period=300 \
  --timeout=10

# Create uptime check for Gateway
gcloud monitoring uptime create ai-identity-gateway-health \
  --display-name="AI Identity Gateway Health" \
  --resource-type=uptime-url \
  --hostname=gateway.ai-identity.co \
  --path=/health \
  --period=300 \
  --timeout=10
```

### 9.4 Alerting Policy

```bash
# Create notification channel (email)
gcloud beta monitoring channels create \
  --display-name="Jeff Email" \
  --type=email \
  --channel-labels=email_address=jeff@ai-identity.co

# Note: Complex alert policies are easier to create via the Console UI.
# Navigate to: Monitoring > Alerting > Create Policy
# Suggested alerts:
#   - Cloud Run error rate > 5% over 5 min
#   - Cloud Run latency p95 > 2000ms over 5 min
#   - Uptime check failure (2 consecutive)
#   - Cloud Run instance count at max (scaling issue)
```

### 9.5 Sentry (Existing)

Sentry is already configured via `SENTRY_DSN` env var in both services. No changes needed -- it will continue to capture application-level errors alongside GCP's infrastructure monitoring.

### 9.6 Budget Alert

```bash
# Create a budget alert at 50%, 80%, and 100% of remaining credits
# This is best done in the Console:
# Billing > Budgets & alerts > Create Budget
# Set amount to $2,300, alert at 25%, 50%, 75%, 90%, 100%
```

---

## 10. Phase 8: Cleanup

Only after 2+ weeks of stable operation on GCP:

### 10.1 Decommission Render Services

1. **Pause Render services** (don't delete yet -- keep as fallback for 30 days):
   - Suspend `ai-identity-api`
   - Suspend `ai-identity-gateway`
   - Suspend `ai-identity-keepalive`

2. **After 30 days of GCP stability**, delete Render services and close the Render account.

### 10.2 Code Cleanup

- [ ] Remove `render.yaml` from the repo (or archive it)
- [ ] Delete `scripts/keepalive_cron.py` (replaced by Cloud Scheduler)
- [ ] Update `scripts/keepalive.sh` or remove it
- [ ] Update `scripts/qa-smoke-test.sh` default URLs
- [ ] Update `README.md` and `docs/ARCHITECTURE.md` to reflect GCP hosting
- [ ] Remove UptimeRobot setup script (`scripts/setup-uptimerobot.sh`) if switching to Cloud Monitoring

### 10.3 Update Documentation

- [ ] Update `QUICKSTART.md` with GCP deploy instructions
- [ ] Update `docs/support-runbook.md` with Cloud Run debugging steps
- [ ] Archive Render-specific docs

---

## 11. Rollback Plan

### Immediate Rollback (< 5 minutes)

If Cloud Run services fail during or after cutover:

1. **Revert DNS** -- point `api.ai-identity.co` and `gateway.ai-identity.co` back to Render URLs
2. **Revert Vercel rewrites** -- restore original `vercel.json` pointing to `*.onrender.com`
3. **Resume Render services** if they were suspended

### Cloud Run Revision Rollback

If a bad deploy goes out to Cloud Run:

```bash
# List revisions
gcloud run revisions list --service=ai-identity-api --region=us-west1

# Route 100% traffic to previous revision
gcloud run services update-traffic ai-identity-api \
  --region=us-west1 \
  --to-revisions=ai-identity-api-PREVIOUS_REVISION=100
```

### Rollback Checklist

1. Identify the issue (Cloud Run logs, Sentry, uptime check alerts)
2. If application bug: roll back to previous Cloud Run revision
3. If infrastructure issue: revert DNS to Render
4. Notify team via Slack/email
5. File post-mortem in CEO Dashboard

---

## 12. Timeline

| Week | Phase | Milestone |
|------|-------|-----------|
| **Week 1** | Foundation | GCP project created, APIs enabled, IAM configured, secrets migrated |
| **Week 1** | Container Registry | Artifact Registry created, first images pushed |
| **Week 2** | Deploy & Test | API and Gateway deployed to Cloud Run, verified with direct URLs |
| **Week 2** | Cron | Cloud Scheduler jobs created for email and cleanup tasks |
| **Week 2** | CI/CD | GitHub Actions deploy workflow added, tested with a PR |
| **Week 3** | DNS Cutover | Custom domains mapped, DNS updated, frontend rewrite updated |
| **Week 3** | Monitoring | Uptime checks, alerts, and budget alerts configured |
| **Week 3-4** | Burn-in | Monitor for 1-2 weeks, run QA smoke tests daily |
| **Week 5** | Cleanup | Suspend Render services |
| **Week 9** | Final | Delete Render services, close account, update docs |

**Total estimated effort:** 2-3 days of hands-on work, spread over 4-5 weeks for safe burn-in.

---

## 13. Cost Projections & Credit Tracking

### Estimated Monthly Cost on Cloud Run

| Resource | Configuration | Est. Monthly Cost |
|----------|---------------|-------------------|
| **Cloud Run - API** | 1 min instance, 1 vCPU, 512Mi, ~100K req/mo | ~$15-25 |
| **Cloud Run - Gateway** | 1 min instance, 1 vCPU, 512Mi, ~100K req/mo | ~$15-25 |
| **Artifact Registry** | ~2 images, <1 GB | ~$0.10 |
| **Secret Manager** | ~15 secrets, <10K accesses/mo | ~$0.10 |
| **Cloud Scheduler** | 3 jobs | Free (3 jobs free tier) |
| **Cloud Logging** | First 50 GB free | $0 |
| **Cloud Monitoring** | Uptime checks (free tier) | $0 |
| **Networking** | Egress (first 1 GB free, minimal after) | ~$1-5 |
| **Total** | | **~$35-60/month** |

### Credit Runway

| Scenario | Monthly Burn | Runway |
|----------|-------------|--------|
| Minimal ($35/mo) | $35 | **65 months (5.4 years)** |
| Expected ($50/mo) | $50 | **46 months (3.8 years)** |
| High ($80/mo) | $80 | **28 months (2.3 years)** |

Even at the high estimate, $2,300 in credits provides over 2 years of runway -- meeting the target.

### Cost Optimization Tips

1. **Set `min-instances=0`** if cold starts are acceptable (saves ~$15/mo per service)
2. **Use Cloud Scheduler keepalive** instead of always-on instances during low-traffic periods
3. **Right-size CPU/memory** after observing actual usage (256Mi may be sufficient)
4. **Set up billing alerts** at 25%, 50%, 75%, 90% of credit balance

### Monitoring Credit Burn

```bash
# Check current billing (CLI)
gcloud billing accounts describe BILLING_ACCOUNT_ID --format=json

# Better: use the Console
# Billing > Overview > Credits remaining
# Billing > Reports > Filter by project
```

Set up a **monthly budget export** to BigQuery for detailed cost analysis (free for the export itself).

---

## Appendix: Environment Variables

Complete inventory of environment variables that need to be migrated from Render to GCP Secret Manager / Cloud Run env vars.

### API Service

| Variable | Type | Source |
|----------|------|--------|
| `DATABASE_URL` | Secret | Secret Manager |
| `ENVIRONMENT` | Plain | Cloud Run env var (`production`) |
| `LOG_LEVEL` | Plain | Cloud Run env var (`INFO`) |
| `CORS_ORIGINS` | Plain | Cloud Run env var |
| `CORS_ORIGIN_REGEX` | Plain | Cloud Run env var |
| `AUDIT_HMAC_KEY` | Secret | Secret Manager |
| `CREDENTIAL_ENCRYPTION_KEY` | Secret | Secret Manager |
| `INTERNAL_SERVICE_KEY` | Secret | Secret Manager |
| `CLERK_ISSUER` | Secret | Secret Manager |
| `GATEWAY_URL` | Plain | Cloud Run env var (Cloud Run gateway URL) |
| `STRIPE_SECRET_KEY` | Secret | Secret Manager |
| `STRIPE_WEBHOOK_SECRET` | Secret | Secret Manager |
| `STRIPE_PRICE_ID_PRO` | Secret | Secret Manager |
| `STRIPE_PRICE_ID_BUSINESS` | Secret | Secret Manager |
| `STRIPE_PRICE_ID_PRO_ANNUAL` | Secret | Secret Manager |
| `STRIPE_PRICE_ID_BUSINESS_ANNUAL` | Secret | Secret Manager |
| `RESEND_API_KEY` | Secret | Secret Manager |
| `SENTRY_DSN` | Secret | Secret Manager |

### Gateway Service

| Variable | Type | Source |
|----------|------|--------|
| `DATABASE_URL` | Secret | Secret Manager (same secret) |
| `ENVIRONMENT` | Plain | Cloud Run env var (`production`) |
| `LOG_LEVEL` | Plain | Cloud Run env var (`INFO`) |
| `CORS_ORIGINS` | Plain | Cloud Run env var |
| `CORS_ORIGIN_REGEX` | Plain | Cloud Run env var |
| `AUDIT_HMAC_KEY` | Secret | Secret Manager |
| `CREDENTIAL_ENCRYPTION_KEY` | Secret | Secret Manager |
| `INTERNAL_SERVICE_KEY` | Secret | Secret Manager |
| `REDIS_URL` | Secret | Secret Manager |
| `SENTRY_DSN` | Secret | Secret Manager |

### Variables That Do NOT Need Migration

| Variable | Reason |
|----------|--------|
| `PYTHON_VERSION` | Baked into Docker image |
| `PYTHONPATH` | Render-specific; not needed with Docker |
| `PORT` | Cloud Run sets this automatically |
