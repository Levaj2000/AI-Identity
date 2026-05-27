# Forensics Knowledge Agent

Vertex AI Search + Next.js chat widget that grounds answers in
AI Identity's published forensics docs. Lives at
[`/forensics`](../../landing-page/src/app/forensics/page.tsx) on the
marketing site.

## Architecture

```
landing-page/src/components/forensics-agent/ForensicsAgent.tsx
    └── POSTs to /api/forensics/ask
            └── landing-page/src/app/api/forensics/ask/route.ts
                    └── Vertex AI Search :answer endpoint
                            └── projects/<id>/locations/global/.../engines/forensics-agent
                                    └── dataStore: forensics-kb
                                            └── gs://<project>-forensics-kb/docs/*.txt
```

Corpus: 8 published blog posts + 1 DeepSeek post + 1 CLI README +
3 internal forensics docs = **13 documents**.

## Refresh the corpus

Run from repo root:

```bash
# 1. Dump the latest blog posts to JSON
(cd landing-page && npx --yes tsx ../scripts/forensics-kb/dump_blog_posts.mjs) \
    > scripts/forensics-kb/out/blog-posts.json

# 2. Stage all source files into out/docs/ + out/metadata.jsonl
python3 scripts/forensics-kb/stage_corpus.py

# 3. Upload + re-import into the existing datastore
bash scripts/forensics-kb/provision.sh
```

The provisioner is idempotent — it skips bucket/datastore/engine
creation if they exist, and re-imports docs with `reconciliationMode: FULL`
so deletes/renames are picked up.

## Local development

```bash
gcloud auth application-default login          # one-time
cp landing-page/.env.local.example landing-page/.env.local
cd landing-page && npm run dev
```

The API route auto-detects ADC when `GOOGLE_SERVICE_ACCOUNT_JSON`
is unset. Visit http://localhost:3000/forensics — click "Ask the docs".

## Production (Vercel)

Vercel can't reach ADC, so it needs a credential. Two paths:

**Option A — Workload Identity Federation (recommended).** No long-lived
key. Vercel mints an OIDC token, GCP exchanges it for a short-lived
access token. Setup outline:

1. Create a Workload Identity Pool + Provider for Vercel's OIDC issuer.
2. Bind the `forensics-agent-runtime@…` SA to the pool.
3. Set Vercel env vars:
   `GOOGLE_APPLICATION_CREDENTIALS_JSON` = the external account config.
4. Modify `getAuth()` to read that var instead.

**Option B — Service account key.** Simpler but the org policy
`constraints/iam.disableServiceAccountKeyCreation` currently blocks
key creation on this project. Would need an exception per project.

Until WIF is wired, the widget on production will return a 503
("Forensics agent auth failed") and the UI surfaces it as a red error
message — degraded gracefully.

## GCP resources

- **Project**: `project-8bbb04f8-fda8-462e-bc2`
- **Bucket**: `gs://project-8bbb04f8-fda8-462e-bc2-forensics-kb`
- **Datastore**: `projects/210992154660/locations/global/collections/default_collection/dataStores/forensics-kb`
- **Engine**: `projects/210992154660/locations/global/collections/default_collection/engines/forensics-agent`
- **Service account**: `forensics-agent-runtime@project-8bbb04f8-fda8-462e-bc2.iam.gserviceaccount.com`
  (role: `roles/discoveryengine.viewer`)
- **Cost**: covered by the GenAI App Builder $1K credit
  (`Trial credit for GenAI App Builder`, expires 2027-05-01)

## Console

https://console.cloud.google.com/gen-app-builder/data-stores?project=project-8bbb04f8-fda8-462e-bc2
