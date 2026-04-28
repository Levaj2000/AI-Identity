# GKE Autopilot vs Cloud Run: Migration Evaluation

**Date:** 2026-04-07
**Context:** AI Identity is evaluating a migration from Render (paid Starter tier) to Google Cloud, funded by $2,300 in startup credits ($2,000 Google for Startups + $300 existing).
**Goal:** Run essentially free for ~2 years, then re-apply for another Google Cloud grant.

---

## Workload Profile

Before comparing platforms, here is what we are actually running:

| Attribute | Details |
|---|---|
| **Language/Runtime** | Python 3.11, FastAPI + Uvicorn + Gunicorn |
| **Services** | 2 web services: **API** (identity/admin) and **Gateway** (policy enforcement proxy) |
| **Database** | Neon Postgres (external, managed separately -- not migrating) |
| **Redis** | Optional, used only for Gateway rate limiting; falls back to in-memory |
| **Background Jobs** | 1 Render cron job (keepalive pings every 10 min + daily email cron + weekly cleanup) |
| **WebSockets** | None |
| **Container Image** | Python 3.11-slim base, ~200-300 MB estimated |
| **Workers** | 2 Gunicorn workers per service (Uvicorn worker class) |
| **Traffic** | Very low -- early-stage startup, handful of users, mostly dashboard API calls |
| **Cold Start Sensitivity** | Currently running a keepalive cron every 10 min specifically to avoid Render cold starts |
| **Current Render Cost** | 3 x Starter ($7/mo each) = ~$21/month |

Key observations:
- Both services are stateless HTTP APIs. No long-running connections, no WebSockets.
- The Gateway uses Redis optionally (falls back to in-memory), so Redis is not a hard dependency.
- The cron job is lightweight (a Python script that makes a few HTTP calls).
- Traffic is very low. This is a pre-revenue startup with a small number of beta users.

---

## 1. Cost Estimation

### Cloud Run

Cloud Run charges per-request with a generous free tier:

| Resource | Free Tier (per month) | Unit Price Beyond Free |
|---|---|---|
| CPU | 180,000 vCPU-seconds | $0.00002400/vCPU-second |
| Memory | 360,000 GiB-seconds | $0.00000250/GiB-second |
| Requests | 2 million | $0.40 per million |
| Networking | 1 GB egress free (NA) | $0.12/GB |

**Estimated monthly cost for AI Identity on Cloud Run:**

- 2 services, each with 0.5 vCPU / 512 MiB, min instances = 0 (scale to zero)
- Assuming ~50,000 requests/month total (generous for early stage)
- Average request duration: ~100ms
- Total vCPU-seconds: 50,000 x 0.1s x 0.5 vCPU = 2,500 vCPU-seconds
- Total memory: 50,000 x 0.1s x 0.5 GiB = 2,500 GiB-seconds

Both are well within the free tier. **Estimated cost: $0-2/month** (essentially free even without credits).

If you set min-instances=1 to avoid cold starts (like your current keepalive approach):
- 1 instance x 0.5 vCPU x 2,592,000 seconds/month = 1,296,000 vCPU-seconds
- Minus 180,000 free = 1,116,000 billable x $0.0000024 = ~$2.68/month per service
- Memory: 1 instance x 0.5 GiB x 2,592,000 = 1,296,000 GiB-seconds, minus 360,000 free = 936,000 x $0.0000025 = ~$2.34/month per service
- **Total with min-instances=1 for both: ~$10/month**

Cloud Scheduler (for the cron job): $0.10/job/month = negligible.

**Cloud Run monthly estimate: $0-10/month** depending on cold-start strategy.

### GKE Autopilot

GKE Autopilot charges for pod resource requests, with no cluster management fee:

| Resource | Price (us-central1) |
|---|---|
| vCPU | $0.0445/vCPU-hour |
| Memory | $0.0049/GiB-hour |
| Ephemeral Storage | $0.000054/GiB-hour |

**Estimated monthly cost for AI Identity on GKE Autopilot:**

- 2 pods (API + Gateway), each requesting 0.25 vCPU / 512 MiB
- Autopilot enforces minimums: 0.25 vCPU, 0.5 GiB per pod
- Pods run 24/7 (Kubernetes pods do not scale to zero by default)

Per pod per month (730 hours):
- CPU: 0.25 vCPU x 730h x $0.0445 = $8.12
- Memory: 0.5 GiB x 730h x $0.0049 = $1.79
- Per pod total: ~$9.91

Two pods: ~$19.82/month

Add a CronJob pod for keepalive/email tasks (runs briefly every 10 min):
- Negligible cost (runs for seconds, a few cents/month)

**GKE Autopilot monthly estimate: ~$20/month**

Note: GKE Autopilot cannot scale to zero. Pods always run and are always billed. This is the fundamental cost difference.

### Summary: Cost Comparison

| | Cloud Run (scale-to-zero) | Cloud Run (min-instances=1) | GKE Autopilot |
|---|---|---|---|
| **Monthly cost** | $0-2 | ~$10 | ~$20 |
| **Annual cost** | $0-24 | ~$120 | ~$240 |
| **2-year cost** | $0-48 | ~$240 | ~$480 |
| **Credits last** | 50+ years (effectively forever) | ~19 years | ~9.5 years |

---

## 2. Performance

### Cold Starts

| | Cloud Run | GKE Autopilot |
|---|---|---|
| **Cold start (scale-to-zero)** | 2-8 seconds for Python/FastAPI (container pull + Python startup + Gunicorn fork). Can be mitigated with min-instances=1 | No cold starts -- pods always running |
| **Warm latency** | Sub-10ms overhead on top of your app logic | Sub-2ms overhead (direct pod routing) |
| **Current situation** | Similar to Render (you already deal with cold starts and keepalive) | Eliminates the cold start problem entirely |

**Verdict:** GKE Autopilot has better raw latency. Cloud Run with min-instances=1 is equivalent. Cloud Run at scale-to-zero is similar to your current Render experience but with faster cold starts (Render Starter spins down after 15 min; Cloud Run cold starts are typically faster than Render's).

### Scaling

| | Cloud Run | GKE Autopilot |
|---|---|---|
| **Scale-up speed** | New instances in 2-8 seconds | HPA-based, 15-60 seconds for new pods |
| **Scale-down** | To zero (or min-instances) in minutes | To 1 replica minimum |
| **Burst handling** | Excellent -- designed for bursty traffic | Good, but slower to react |
| **Max concurrency** | Configurable per instance (default 80) | Standard Kubernetes |

**Verdict:** Cloud Run scales faster and handles bursty traffic better. For a low-traffic startup, this matters less, but Cloud Run's scaling model is better aligned with unpredictable startup traffic.

---

## 3. Operational Complexity

### Deployment

| | Cloud Run | GKE Autopilot |
|---|---|---|
| **Deploy method** | `gcloud run deploy` or Cloud Build trigger from GitHub | `kubectl apply` or Cloud Build + Skaffold |
| **Config files needed** | 1 YAML (service definition) or CLI flags | Deployment YAML, Service YAML, Ingress, CronJob YAML, possibly HPA |
| **CI/CD setup** | Cloud Build trigger (5-10 lines of cloudbuild.yaml) | Cloud Build + container registry + kubectl apply (more config) |
| **Deploy time** | ~1-2 minutes (similar to Render) | ~2-4 minutes |
| **Rollbacks** | Built-in traffic splitting + instant revision rollback | `kubectl rollout undo` (standard K8s) |
| **Secrets** | Secret Manager integration (native) | Secret Manager + K8s secrets or external-secrets operator |

**Verdict:** Cloud Run is significantly simpler. Render-to-Cloud-Run is a natural transition for teams used to PaaS simplicity. GKE requires learning Kubernetes manifests, kubectl, and managing more configuration.

### Monitoring & Debugging

| | Cloud Run | GKE Autopilot |
|---|---|---|
| **Logs** | Cloud Logging (structured, built-in) | Cloud Logging (same, but more noise from K8s system pods) |
| **Metrics** | Built-in request latency, instance count, CPU/memory | GKE dashboard + custom metrics via Prometheus or Cloud Monitoring |
| **Debugging** | Log Explorer, Error Reporting, Cloud Trace (all automatic) | Same tools available but require more setup; kubectl logs for pod-level |
| **Alerting** | Cloud Monitoring policies (easy setup) | Same, but more dimensions to monitor |

**Verdict:** Roughly equivalent for core monitoring. Cloud Run surfaces fewer distracting system-level metrics, making it easier to focus on your application.

---

## 4. Migration Effort

### Cloud Run Migration

What changes from the current Render setup:

1. **Dockerfile:** Works as-is. Cloud Run uses the same Dockerfile.
2. **render.yaml to Cloud Run service YAML:** Translate service definitions. Each Render service becomes a Cloud Run service. Straightforward mapping.
3. **Environment variables:** Move to Secret Manager or Cloud Run env vars.
4. **Cron job:** Replace Render cron with Cloud Scheduler triggering a Cloud Run job (or an HTTP endpoint on the API service).
5. **Health checks:** Cloud Run has built-in startup/liveness probes. The existing `/health` endpoints work directly.
6. **CORS origins:** Update to new service URLs.
7. **Keepalive cron:** Can be eliminated entirely with min-instances=1, or kept as a Cloud Scheduler job.
8. **Redis:** If needed, use Memorystore for Redis or Upstash. For low traffic, the in-memory fallback works fine on Cloud Run.

**Estimated effort:** 1-2 days for a developer familiar with GCP. Half a day if you have done it before.

### GKE Autopilot Migration

Everything in the Cloud Run list, plus:

1. **Kubernetes manifests:** Write Deployment, Service, Ingress, CronJob, ConfigMap, and Secret manifests for each service (~150-200 lines of YAML total).
2. **Ingress/Load Balancer:** Configure GKE Ingress or use a Gateway API resource for HTTPS routing.
3. **TLS certificates:** Set up managed certificates or cert-manager.
4. **Namespace design:** Decide on namespace strategy (even if just `default`).
5. **Resource requests/limits:** Tune CPU and memory requests for Autopilot billing optimization.
6. **HPA:** Configure Horizontal Pod Autoscaler if you want scaling behavior.

**Estimated effort:** 3-5 days for a developer learning Kubernetes. 1-2 days if experienced with K8s.

**Verdict:** Cloud Run migration is straightforward and maps closely to the Render mental model. GKE Autopilot requires significantly more Kubernetes knowledge and configuration.

---

## 5. Scaling Path

### Cloud Run

- **0 to 1,000 req/sec:** Just works. Cloud Run auto-scales transparently.
- **Multi-region:** Deploy the same service to multiple regions with a Global Load Balancer.
- **Adding services:** Deploy another Cloud Run service. No cluster management.
- **When to leave Cloud Run:** If you need persistent background processes (long-running workers), GPU workloads, or very specific networking (VPC peering, custom CNI). None of these apply to AI Identity today.
- **Ceiling:** Cloud Run handles thousands of concurrent requests per service. You would need to be processing massive volumes before hitting limits.

### GKE Autopilot

- **0 to 1,000 req/sec:** Works, but you manage scaling configuration (HPA, resource requests).
- **Multi-region:** Possible with multi-cluster setup (significantly more complex).
- **Adding services:** Add another Deployment + Service. Shared cluster amortizes overhead.
- **When GKE makes sense:** When you have 10+ microservices, need service mesh, require GPU workloads, or need fine-grained networking control.
- **Ceiling:** Virtually unlimited (Kubernetes scales to thousands of pods).

**Verdict:** Both scale well beyond AI Identity's current and near-term needs. Cloud Run's scaling path is simpler and more cost-effective for a small team. GKE Autopilot is overkill until you have a large engineering team and complex infrastructure needs.

---

## 6. Credit Burn Rate

**Budget:** $2,300 in Google Cloud credits. Goal: last ~2 years.

| Scenario | Monthly Burn | Credits Last |
|---|---|---|
| Cloud Run (scale-to-zero) | ~$2 | **96 years** |
| Cloud Run (min-instances=1, both services) | ~$10 | **19 years** |
| Cloud Run (min=1) + Memorystore Redis | ~$40 | **4.8 years** |
| GKE Autopilot (2 pods, always on) | ~$20 | **9.6 years** |
| GKE Autopilot + Redis (Memorystore) | ~$50 | **3.8 years** |

Additional costs to account for:
- **Container Registry (Artifact Registry):** ~$0.10/GB/month for stored images. Negligible.
- **Cloud Build:** 120 free build-minutes/day. More than enough for this workload.
- **Cloud Logging/Monitoring:** Free tier covers the first 50 GB/month of logs. Sufficient for early stage.
- **Networking:** Minimal egress for API responses. Covered by free tier.

**Verdict:** Cloud Run comfortably fits within the $2,300 budget for 2+ years regardless of configuration. GKE Autopilot also fits, but with less margin and no room for adding Redis or other managed services.

---

## 7. Redis Considerations

The Gateway uses Redis for cross-worker rate limiting but gracefully falls back to in-memory. Options:

| Option | Monthly Cost | Notes |
|---|---|---|
| Skip Redis entirely | $0 | In-memory fallback works for low traffic. Single Cloud Run instance handles rate limiting per-process. |
| Upstash Redis (serverless) | $0 (free tier: 10K commands/day) | Pay-per-use, no idle cost. Works with Cloud Run's serverless model. |
| Memorystore for Redis (Basic, 1 GB) | ~$30/month | Overkill for this use case. Eats into credits. |

**Recommendation:** Use the in-memory fallback for now. If you need shared rate limiting later, Upstash is the cost-effective choice for Cloud Run.

---

## Recommendation

**Cloud Run is the clear winner for AI Identity's current stage.**

Here is why:

1. **Cost:** $0-10/month vs $20+/month for GKE. With $2,300 in credits, Cloud Run gives you 10-19+ years of runway vs 4-9 years on GKE.

2. **Operational fit:** AI Identity has 2 stateless HTTP services and a cron job. This is exactly the workload Cloud Run was designed for. GKE Autopilot adds Kubernetes complexity with no benefit for this architecture.

3. **Migration effort:** Cloud Run is a 1-2 day migration. GKE is 3-5 days. Both use the same Dockerfile, but Cloud Run requires far less configuration.

4. **Cold starts:** Cloud Run with min-instances=1 ($10/month) eliminates cold starts entirely and still costs half of GKE Autopilot. Alternatively, scale-to-zero ($0-2/month) with cold starts of 2-8 seconds is likely acceptable for a dashboard API.

5. **Scaling path:** Cloud Run scales transparently from 0 to thousands of requests/second. You can always migrate to GKE later if you outgrow Cloud Run (unlikely for years).

6. **Keepalive elimination:** With Cloud Run min-instances=1, you can delete the keepalive cron job entirely. One fewer service to manage.

7. **Team size:** A 1-person or small team benefits enormously from Cloud Run's managed infrastructure. Kubernetes operational overhead is not justified at this stage.

### Recommended Configuration

```
Cloud Run Service: ai-identity-api
  - Image: gcr.io/PROJECT/ai-identity-api
  - CPU: 1 vCPU
  - Memory: 512 MiB
  - Min instances: 1 (eliminate cold starts)
  - Max instances: 5
  - Concurrency: 80
  - Region: us-central1 (or us-west1 for Oregon parity with Render)

Cloud Run Service: ai-identity-gateway
  - Image: gcr.io/PROJECT/ai-identity-gateway
  - CPU: 1 vCPU
  - Memory: 512 MiB
  - Min instances: 1
  - Max instances: 5
  - Concurrency: 80
  - Region: same as API

Cloud Scheduler Job: keepalive-and-cron
  - Schedule: 0 16 * * * (daily at 16:00 UTC for email followups)
  - Target: POST https://api-service-url/api/internal/email/send-followups
  - OIDC auth with service account

Cloud Scheduler Job: weekly-cleanup
  - Schedule: 0 4 * * 0 (Sundays at 04:00 UTC)
  - Target: POST https://api-service-url/api/internal/cleanup/inactive-users
  - OIDC auth with service account
```

**Estimated monthly cost: ~$10/month = $240/2 years = 10% of credits.**

### When to Reconsider GKE

Move to GKE Autopilot if/when:
- You have 5+ backend services and want shared infrastructure
- You need GPU workloads (ML inference)
- You need a service mesh or advanced networking
- Your team has dedicated platform/DevOps engineers
- You are spending $500+/month on Cloud Run (this means you have significant traffic and revenue)

None of these conditions apply today or in the near term.

---

## Appendix: Migration Checklist (Cloud Run)

- [ ] Create GCP project and enable Cloud Run, Artifact Registry, Cloud Build, Cloud Scheduler, Secret Manager APIs
- [ ] Push Docker images to Artifact Registry
- [ ] Set up Cloud Build trigger on GitHub main branch (replaces Render auto-deploy)
- [ ] Create Secret Manager secrets for DATABASE_URL, AUDIT_HMAC_KEY, CREDENTIAL_ENCRYPTION_KEY, INTERNAL_SERVICE_KEY, CLERK_ISSUER
- [ ] Deploy API service with `gcloud run deploy`
- [ ] Deploy Gateway service with `gcloud run deploy`
- [ ] Create Cloud Scheduler jobs for daily email cron and weekly cleanup
- [ ] Map custom domain (if needed) via Cloud Run domain mapping
- [ ] Update CORS_ORIGINS env var with new service URLs
- [ ] Update Vercel dashboard frontend to point to new API/Gateway URLs
- [ ] Update Sentry release tracking for new service names
- [ ] Smoke test all endpoints
- [ ] Remove Render keepalive cron job (no longer needed)
- [ ] Monitor for 1 week, then decommission Render services
