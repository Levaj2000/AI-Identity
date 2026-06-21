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

## Weekly Compute Headroom Report (`compute_report.py`)

The **inverse lens** of the cost report. The cost report asks *"where can we
cut?"*; this one asks *"where could we run out and take production down?"*. It
exists because on **2026-06-21** Neon's Free-tier compute-time quota ran out and
rejected DB connections, taking prod down.

**Standing policy (founder):** for compute essential to the platform running, err
toward **too much** capacity. Only consider adjusting **down** after ~3 months
(13 consecutive weekly reports) of sustained low utilization — and the report
only *nominates* a candidate after that window; it never acts.

Per resource it reports a headroom status — 🔴 CRITICAL / 🟡 WATCH / 🟢 OK /
🛡️ PROTECTED — with live utilization:
- **Neon** — paid plan = PROTECTED (no hard compute wall); Free tier = CRITICAL.
- **Atlas** — live connections / CPU / RAM vs tier ceiling + auto-scaling config
  (auto-scale on both axes = PROTECTED, the wall moves with demand).
- **GKE Autopilot** — informational; nodes auto-provision per pod request.
- **Sentry** — errors vs the free quota (a soft wall — over-quota drops events,
  doesn't break prod).

Reuses `infra_cost_report.py`'s collectors and `.env`; stdlib-only + fail-soft so
launchd never breaks. A per-week snapshot accumulates in
`out/compute/compute_history.json` to drive the 13-week down-adjust logic.

```bash
python3 compute_report.py            # writes out/compute/compute-headroom-YYYY-MM-DD.md
python3 compute_report.py --email    # also emails the summary (SMTP, same path as the cost report)
```

Scheduled **weekly, Monday 9am** via
`~/Library/LaunchAgents/co.ai-identity.compute-headroom-report.plist`.

## Files
- `infra_cost_report.py` — collectors (fail-soft per provider) + email + orchestration
- `compute_report.py` — weekly compute-headroom report (reuses the collectors)
- `render.py` — branded PDF (AI Identity Purple) + .xlsx workbook (incl. month-over-month Trend tab)
- `.env.example` — credential template (real `.env` is gitignored)
- `out/` — generated reports + `history.json` trend store (gitignored); `out/compute/` for the weekly report
