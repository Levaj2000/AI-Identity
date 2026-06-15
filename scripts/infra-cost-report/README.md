# Infra Cost Report

Monthly usage + billing + optimization report across **Neon**, **MongoDB Atlas**,
**GCP/GKE**, and **Sentry**. Emailed to the founder on a schedule as a branded
PDF + spreadsheet.

Data collection is **stdlib-only** (urllib) so the scheduled run never breaks on
a missing venv. Rendering needs two libs — install once where the job runs:

```bash
python3 -m pip install --break-system-packages reportlab openpyxl
```

## What it reports
Per service: usage, billing / credit burn, run-rate, and **optimization flags**
(e.g. "Neon on paid plan but fits Free", "Atlas credits ~N months runway",
"GCP billing export not enabled").

## Setup (one-time)

```bash
cd scripts/infra-cost-report
cp .env.example .env          # fill in keys (see below)
set -a; . ./.env; set +a
python3 infra_cost_report.py  # prints + writes out/infra-cost-YYYY-MM.md
python3 infra_cost_report.py --email   # also emails it
```

### Keys to create

| Provider | Where | Scope |
|---|---|---|
| **Neon** | Console → Org Settings → **API Keys** → Create | org-scoped |
| **Atlas** | Org → **Applications** → **API Keys** → Create | **Organization Billing Viewer** (+ Read Only); IP allowlist only if the org requires it |
| **GCP (exact $)** | Billing → **BigQuery export** → enable, then set `GCP_BILLING_BQ_TABLE` | n/a (read via `bq`) |
| **GCP (headless auth)** | Service account w/ `roles/billing.viewer` + `roles/container.viewer` | for the scheduled run; gcloud user tokens expire |
| **Sentry** (optional) | Settings → **Auth Tokens** → create (`org:read`, `project:read`) | auto-pulls error volume; else manual `SENTRY_ERRORS_30D` |
| **Email** | Google Account → Security → **App passwords** | 16-char app password for `SMTP_APP_PASSWORD` |

> GCP credit *balance* has no API — the report reminds you to read it from
> Billing → Credits each month. Everything else is automatic.

## Scheduling (after test passes)
Runs on the **3rd of each month** (so prior-month invoices are finalized). The
script self-loads `./.env`, so no shell sourcing is needed. On macOS a `launchd`
job is preferred over cron — it catches up at next wake if the Mac was asleep:

```
~/Library/LaunchAgents/co.ai-identity.infra-cost-report.plist
  → ProgramArguments: python3 <path>/infra_cost_report.py --email
  → StartCalendarInterval: { Day: 3, Hour: 9, Minute: 0 }
```

## Files
- `infra_cost_report.py` — collectors (fail-soft per provider) + email + orchestration
- `render.py` — branded PDF (AI Identity Purple) + .xlsx workbook (incl. month-over-month Trend tab)
- `.env.example` — credential template (real `.env` is gitignored)
- `out/` — generated reports + `history.json` trend store (gitignored)
