#!/usr/bin/env python3
"""
AI Identity — Monthly Infra Cost Report
========================================
Pulls usage + billing from Neon, MongoDB Atlas, and GCP/GKE, then emits a
single Markdown report with optimization flags. Designed to run headless on a
monthly schedule (stdlib only — no pip deps, so cron never breaks on a venv).

Credentials are read from environment (see .env.example). Every provider fails
*soft*: a missing key downgrades that section to "not configured" rather than
killing the whole report, so you can test incrementally as keys come in.

Usage:
    # load env then run
    set -a; . ./.env; set +a
    python3 infra_cost_report.py                 # writes report to ./out/
    python3 infra_cost_report.py --email         # also sends via SMTP
    python3 infra_cost_report.py --month 2026-05 # specific billing month
"""

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from calendar import monthrange
from datetime import UTC, date, datetime

# ----------------------------------------------------------------------------- helpers
HTTP_TIMEOUT = 30
_CTX = ssl.create_default_context()


def _load_dotenv():
    """Parse ./.env next to this script into os.environ. Robust to spaces/quotes
    in values (shell `source` is not), so cron never breaks on a pasted secret."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _get(url, headers=None, digest=None):
    """GET returning parsed JSON. digest=(user,pass) uses HTTP Digest auth."""
    opener = urllib.request.build_opener()
    if digest:
        mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        mgr.add_password(None, url, digest[0], digest[1])
        opener.add_handler(urllib.request.HTTPDigestAuthHandler(mgr))
    req = urllib.request.Request(url, headers=headers or {})
    with opener.open(req, timeout=HTTP_TIMEOUT) as r:
        return json.loads(r.read().decode())


def _month_bounds(month_str):
    """Return (from_iso, to_iso, label) for a 'YYYY-MM' string (default: current)."""
    if month_str:
        y, m = (int(x) for x in month_str.split("-"))
    else:
        now = datetime.now(UTC)
        y, m = now.year, now.month
    end = date(y, m, monthrange(y, m)[1])
    return (
        datetime(y, m, 1, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        datetime(y, m, end.day, 23, 59, 59, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
        f"{y}-{m:02d}",
    )


def _flag(msg):
    return f"⚠️  {msg}"


def _ok(msg):
    return f"✅ {msg}"


# ----------------------------------------------------------------------------- Neon
def fetch_neon(cfg):
    """Neon: plan tier + per-project compute/storage. Flags over-tiering."""
    key = cfg.get("NEON_API_KEY")
    org = cfg.get("NEON_ORG_ID")
    if not key:
        return {"configured": False, "note": "NEON_API_KEY not set"}
    base = "https://console.neon.tech/api/v2"
    h = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    out = {"configured": True, "projects": [], "flags": []}
    try:
        # plan tier
        orgs = _get(f"{base}/organizations", h).get("organizations", []) if not org else None
        if orgs:
            o = orgs[0]
            org = o["id"]
            out["org_name"], out["plan"] = o.get("name"), o.get("plan")
        elif org:
            resp = _get(f"{base}/organizations/{org}", h)
            o = resp.get("organization", resp)  # this endpoint returns the org unwrapped
            out["org_name"], out["plan"] = o.get("name"), o.get("plan")
        # projects (compute/storage)
        proj = _get(f"{base}/projects?org_id={org}&limit=100", h).get("projects", [])
        comp_hours = 0.0
        store_mb = 0.0
        for p in proj:
            ch = round(p.get("cpu_used_sec", 0) / 3600, 2)
            mb = round(p.get("synthetic_storage_size", 0) / 1e6, 1)
            comp_hours += ch
            store_mb += mb
            out["projects"].append({"name": p.get("name"), "compute_hours": ch, "storage_mb": mb})
        out["total_compute_hours"] = round(comp_hours, 2)
        out["total_storage_mb"] = round(store_mb, 1)
        # Plan posture. We deliberately do NOT recommend downgrading Neon to Free:
        # the Free tier's 191.9 compute-hr quota is a hard wall that took prod down
        # on 2026-06-21 (DB connections rejected). Standing policy is to keep
        # platform-essential compute over-provisioned. See compute_report.py.
        if out.get("plan") and out["plan"].lower() != "free":
            out["flags"].append(
                _ok(
                    f"On paid '{out['plan']}' plan — keep it. Free tier's compute quota is a "
                    f"hard wall that broke prod on 2026-06-21; do NOT downgrade while prod "
                    f"depends on Neon."
                )
            )
        else:
            out["flags"].append(
                _flag(
                    "On Free tier — its 191.9 compute-hr quota is a hard wall that rejects DB "
                    "connections when exhausted (took prod down 2026-06-21). Upgrade to a paid plan."
                )
            )
    except urllib.error.HTTPError as e:
        out["error"] = f"HTTP {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        out["error"] = str(e)
    return out


# ----------------------------------------------------------------------------- Atlas
def fetch_atlas(cfg):
    """Atlas: pending + last invoice, credit drawdown, cluster tier. Flags credit runway."""
    pub, priv = cfg.get("ATLAS_PUBLIC_KEY"), cfg.get("ATLAS_PRIVATE_KEY")
    org = cfg.get("ATLAS_ORG_ID")
    if not (pub and priv and org):
        return {"configured": False, "note": "ATLAS_PUBLIC_KEY/PRIVATE_KEY/ORG_ID not all set"}
    base = "https://cloud.mongodb.com/api/atlas/v2"
    h = {"Accept": "application/vnd.atlas.2023-11-15+json"}
    out = {"configured": True, "flags": []}

    def clean(s):
        return s.replace("ATLAS_", "").replace("NDS_", "")

    try:
        # pending (current month): subtotal isn't finalized yet → sum the line items
        pend = _get(f"{base}/orgs/{org}/invoices/pending", h, digest=(pub, priv))
        svc, tiers, pend_cents = {}, set(), 0
        for li in pend.get("lineItems", []):
            sku = li.get("sku", "") or li.get("groupName", "")
            cents = li.get("totalPriceCents", 0)
            pend_cents += cents
            svc[clean(sku)] = round(svc.get(clean(sku), 0) + cents / 100, 2)
            if "INSTANCE_" in sku:
                tiers.add(sku.split("INSTANCE_")[-1])  # e.g. ATLAS_GCP_INSTANCE_M10 → M10
        out["pending_usd"] = round(pend_cents / 100, 2)
        out["service_breakdown"] = svc
        out["tiers"] = sorted(tiers)
        # most recent CLOSED invoice = monthly run-rate (subtotalCents is populated there)
        inv = _get(f"{base}/orgs/{org}/invoices?itemsPerPage=6", h, digest=(pub, priv)).get(
            "results", []
        )
        closed = [i for i in inv if i.get("subtotalCents", 0) > 0]
        if closed:
            last = max(closed, key=lambda i: i.get("endDate", ""))
            out["last_invoice_usd"] = round(last.get("subtotalCents", 0) / 100, 2)
            out["last_invoice_period"] = (last.get("startDate", "?") or "?")[:7]
        # credits: NOT exposed by the invoices API → console-only, unless user supplies balance
        rate = out.get("last_invoice_usd") or out.get("pending_usd")
        bal = cfg.get("ATLAS_CREDIT_BALANCE_USD")
        if bal:
            bal = float(bal)
            months = (bal / rate) if rate else None
            exp = cfg.get("ATLAS_CREDIT_EXPIRY", "")
            tag = _flag if (months is not None and months < 4) else _ok
            out["flags"].append(
                tag(
                    f"Atlas credits: ~${bal:.0f} balance"
                    + (f", ~${rate:.0f}/mo burn → ~{months:.0f} mo runway" if months else "")
                    + (f" (exp {exp})" if exp else "")
                )
            )
        else:
            out["flags"].append(
                _flag(
                    "Atlas credit balance isn't in the API — read Billing → Overview → Credits and set "
                    "ATLAS_CREDIT_BALANCE_USD (+ ATLAS_CREDIT_EXPIRY) in .env to auto-track runway."
                )
            )
    except urllib.error.HTTPError as e:
        out["error"] = (
            f"HTTP {e.code}: {e.read().decode()[:200]} (key needs Org Billing Viewer + IP allowlisted)"
        )
    except Exception as e:
        out["error"] = str(e)
    return out


# ----------------------------------------------------------------------------- GCP / GKE
def fetch_gcp(cfg):
    """
    GCP: exact cost from BigQuery billing export if configured; otherwise a
    labeled estimate from live GKE footprint. Credits balance is console-only.
    """
    table = cfg.get("GCP_BILLING_BQ_TABLE")  # e.g. project.dataset.gcp_billing_export_v1_XXXX
    out = {"configured": bool(table or cfg.get("GCP_PROJECT")), "flags": [], "method": None}
    if table:
        # exact: query last full month by service
        import subprocess

        q = (
            f"SELECT service.description svc, ROUND(SUM(cost),2) cost "
            f"FROM `{table}` "
            f"WHERE invoice.month = FORMAT_DATE('%Y%m', DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)) "
            f"GROUP BY svc ORDER BY cost DESC"
        )
        try:
            r = subprocess.run(
                ["bq", "query", "--use_legacy_sql=false", "--format=json", q],
                capture_output=True,
                text=True,
                timeout=120,
            )
            rows = json.loads(r.stdout or "[]")
            out["method"] = "bigquery_export"
            out["service_breakdown"] = {x["svc"]: float(x["cost"]) for x in rows}
            out["total_usd"] = round(sum(float(x["cost"]) for x in rows), 2)
        except Exception as e:
            out["error"] = f"BQ query failed: {e}"
    else:
        out["method"] = "estimate"
        out["flags"].append(
            _flag(
                "No BigQuery billing export configured — GCP $ is ESTIMATED from live GKE usage. "
                "Enable Billing → BigQuery export for exact figures (one-time, ~24h to populate)."
            )
        )
        out["note"] = (
            "Estimate basis: app pod requests on Autopilot. Run "
            "`kubectl get pods -A` + Autopilot rates. See README for the helper."
        )
    # GCP credit pools — console-only balances, pasted from Billing → Credits (.env)
    credits = []
    for name, amt, exp, note in (
        (
            "GFS Startup (infra)",
            cfg.get("GCP_INFRA_CREDIT_USD"),
            cfg.get("GCP_INFRA_CREDIT_EXPIRY"),
            "main GKE runway",
        ),
        (
            "Vertex / GenAI (Forensics Agent)",
            cfg.get("GCP_VERTEX_CREDIT_USD"),
            cfg.get("GCP_VERTEX_CREDIT_EXPIRY"),
            "use-it-or-lose-it",
        ),
    ):
        if amt:
            credits.append({"name": name, "usd": float(amt), "expiry": exp or "?", "note": note})
    if credits:
        out["credits"] = credits
        out["flags"].append(
            _ok(
                f"GCP credits remaining: ~${sum(c['usd'] for c in credits):,.0f} across "
                f"{len(credits)} pools (balances entered manually — refresh from console)."
            )
        )
        for c in credits:
            if "Vertex" in c["name"] and c["usd"] > 900:
                out["flags"].append(
                    _flag(
                        f"Vertex credit ${c['usd']:.0f} barely used, expires {c['expiry']} — "
                        f"use-it-or-lose-it for the Forensics doc Agent."
                    )
                )
    else:
        out["flags"].append(
            _flag("GCP credit balances not entered — paste from Billing → Credits into .env.")
        )
    return out


# ----------------------------------------------------------------------------- Sentry
SENTRY_FREE_QUOTA = 5000  # Developer (free) plan: errors/month
SENTRY_TEAM_USD = 29.0


def fetch_sentry(cfg):
    """Sentry: plan + 30-day error volume vs free quota. Flags paid-plan-but-idle.
    Live when SENTRY_AUTH_TOKEN is set; otherwise uses manual .env snapshot."""
    org = cfg.get("SENTRY_ORG", "ai-identity")
    plan = cfg.get(
        "SENTRY_PLAN"
    )  # 'team' | 'developer' | 'business' (API plan is unreliable → manual)
    token = cfg.get("SENTRY_AUTH_TOKEN")
    region = cfg.get("SENTRY_REGION_URL", "https://us.sentry.io")
    if not (plan or token):
        return {"configured": False, "note": "SENTRY_PLAN / SENTRY_AUTH_TOKEN not set"}
    out = {
        "configured": True,
        "flags": [],
        "org": org,
        "plan": plan,
        "projects": [],
        "errors_30d": None,
    }
    try:
        if token:
            h = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            out["projects"] = [
                p.get("slug") for p in _get(f"{region}/api/0/organizations/{org}/projects/", h)
            ]
            st = _get(
                f"{region}/api/0/organizations/{org}/stats_v2/"
                f"?statsPeriod=30d&field=sum(quantity)&category=error",
                h,
            )
            total = 0
            for grp in st.get("groups", []):
                total += sum(grp.get("series", {}).get("sum(quantity)", []) or [])
            out["errors_30d"] = int(total)
        # manual fallbacks (.env snapshot until a token is wired)
        if out["errors_30d"] is None and cfg.get("SENTRY_ERRORS_30D"):
            out["errors_30d"] = int(cfg["SENTRY_ERRORS_30D"])
        if not out["projects"] and cfg.get("SENTRY_PROJECTS"):
            out["projects"] = [s.strip() for s in cfg["SENTRY_PROJECTS"].split(",")]
        e = out["errors_30d"]
        paid = (plan or "").lower() in ("team", "business")
        intentional = cfg.get("SENTRY_PLAN_INTENTIONAL", "").lower() in ("1", "true", "yes")
        if paid and intentional:
            out["flags"].append(
                _ok(
                    f"Sentry {plan.title()} (~${SENTRY_TEAM_USD:.0f}/mo) — retained by decision "
                    f"(tracing/spans headroom while pre-launch; revisit after launch)."
                )
            )
        elif paid and e is not None and e < SENTRY_FREE_QUOTA * 0.5:
            out["flags"].append(
                _flag(
                    f"Sentry on paid {plan.title()} (~${SENTRY_TEAM_USD:.0f}/mo) but only {e} errors/30d — "
                    f"free Developer (5k/mo) covers it. Downgrade saves ~${SENTRY_TEAM_USD * 12:.0f}/yr."
                )
            )
        elif e is not None:
            pct = e / SENTRY_FREE_QUOTA * 100
            tag = _flag if pct > 80 else _ok
            out["flags"].append(
                tag(f"Sentry ({plan or 'plan'}): {e} errors/30d = {pct:.0f}% of free 5k quota.")
            )
        if not token:
            out["flags"].append(
                _flag(
                    "Set SENTRY_AUTH_TOKEN in .env to auto-pull Sentry volume (currently manual)."
                )
            )
    except Exception as ex:
        out["error"] = str(ex)
    return out


# ----------------------------------------------------------------------------- report
def build_report(month_label, neon, atlas, gcp, sentry):
    lines = []
    lines.append(f"# AI Identity — Infra Cost Report · {month_label}")
    lines.append(f"_Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}_\n")

    # executive flags first
    flags = []
    for svc in (neon, atlas, gcp, sentry):
        flags += svc.get("flags", []) if isinstance(svc, dict) else []
    lines.append("## Optimization flags")
    lines += [f"- {f}" for f in flags] or ["- (none)"]
    lines.append("")

    # Neon
    lines.append("## 🐘 Neon (Postgres)")
    if not neon.get("configured"):
        lines.append(f"- _Not configured: {neon.get('note')}_")
    elif neon.get("error"):
        lines.append(f"- ❌ {neon['error']}")
    else:
        lines.append(
            f"- Plan: **{neon.get('plan', '?')}** · {len(neon.get('projects', []))} projects "
            f"· {neon.get('total_compute_hours', '?')} compute-hrs · {neon.get('total_storage_mb', '?')} MB"
        )
        for p in neon.get("projects", []):
            lines.append(f"  - `{p['name']}` — {p['compute_hours']} hrs, {p['storage_mb']} MB")
    lines.append("")

    # Atlas
    lines.append("## 🍃 MongoDB Atlas")
    if not atlas.get("configured"):
        lines.append(f"- _Not configured: {atlas.get('note')}_")
    elif atlas.get("error"):
        lines.append(f"- ❌ {atlas['error']}")
    else:
        lines.append(f"- Cluster tier: **{', '.join(atlas.get('tiers', [])) or '?'}** (GCP)")
        lines.append(
            f"- This month MTD: **${atlas.get('pending_usd', '?')}** (billed $0 — covered by credits)"
        )
        if atlas.get("last_invoice_usd") is not None:
            lines.append(
                f"- Last full month ({atlas.get('last_invoice_period', '?')}): "
                f"**${atlas.get('last_invoice_usd')}** ← run-rate"
            )
        for k, v in (atlas.get("service_breakdown") or {}).items():
            lines.append(f"  - {k}: ${v}")
    lines.append("")

    # GCP
    lines.append("## ☸️ GCP / GKE")
    if not gcp.get("configured"):
        lines.append("- _Not configured._")
    elif gcp.get("error"):
        lines.append(f"- ❌ {gcp['error']}")
    else:
        lines.append(f"- Method: **{gcp.get('method')}**")
        if gcp.get("total_usd") is not None:
            lines.append(f"- Total: **${gcp.get('total_usd')}**")
            for k, v in (gcp.get("service_breakdown") or {}).items():
                lines.append(f"  - {k}: ${v}")
        for c in gcp.get("credits") or []:
            lines.append(
                f"  - 💳 {c['name']}: **${c['usd']:,.2f}** (exp {c.get('expiry', '?')}) — {c.get('note', '')}"
            )
        if gcp.get("note"):
            lines.append(f"- {gcp['note']}")
    lines.append("")

    # Sentry
    lines.append("## 🔦 Sentry (error monitoring)")
    if not sentry.get("configured"):
        lines.append(f"- _Not configured: {sentry.get('note')}_")
    elif sentry.get("error"):
        lines.append(f"- ❌ {sentry['error']}")
    else:
        lines.append(
            f"- Plan: **{(sentry.get('plan') or '?').title()}** · "
            f"{len(sentry.get('projects', []))} projects · "
            f"{sentry.get('errors_30d', '?')} errors / 30d"
        )
    lines.append("")
    lines.append(
        "---\n_Generated by `scripts/infra-cost-report/infra_cost_report.py` (CTO automation)._"
    )
    return "\n".join(lines)


# ----------------------------------------------------------------------------- email
def email_body(label, summary, flags):
    lines = [
        f"AI Identity — Infrastructure Cost Report · {label}",
        "",
        f"Cash out-of-pocket this month: ${summary['out_of_pocket_usd']:,.2f}  (infra running on credits)",
        f"GCP credit runway: ${summary['gcp_credits_total']:,.0f} across {summary['gcp_credit_pools']} pools",
        f"Atlas run-rate: ${summary['atlas_run_rate']:,.2f}/mo  (M10, credit-covered)",
        "",
        "Action items & flags:",
    ]
    lines += [f"  {f}" for f in flags]
    lines += [
        "",
        "Full breakdown attached — branded PDF + spreadsheet (month-over-month trend tab).",
        "",
        "— Generated automatically by the CTO infra-cost-report job.",
    ]
    return "\n".join(lines)


def send_email(cfg, subject, body_text, attachments=None):
    import smtplib
    from email.mime.application import MIMEApplication
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    host = cfg.get("SMTP_HOST", "smtp.gmail.com")
    port = int(cfg.get("SMTP_PORT", "587"))
    user = cfg.get("SMTP_USER")
    pw = (cfg.get("SMTP_APP_PASSWORD") or "").replace(
        " ", ""
    )  # Gmail shows it spaced; login wants 16 chars
    to = cfg.get("REPORT_TO", "jeff@ai-identity.co")
    if not (user and pw):
        print("  [email] SMTP_USER/SMTP_APP_PASSWORD not set — skipping send.", file=sys.stderr)
        return False
    msg = MIMEMultipart()
    msg["Subject"], msg["From"], msg["To"] = subject, user, to
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    for ap in attachments or []:
        with open(ap, "rb") as fh:
            part = MIMEApplication(fh.read(), Name=os.path.basename(ap))
        part["Content-Disposition"] = f'attachment; filename="{os.path.basename(ap)}"'
        msg.attach(part)
    with smtplib.SMTP(host, port, timeout=HTTP_TIMEOUT) as s:
        s.starttls(context=_CTX)
        s.login(user, pw)
        s.sendmail(user, [to], msg.as_string())
    print(f"  [email] sent to {to} with {len(attachments or [])} attachment(s)")
    return True


# ----------------------------------------------------------------------------- main
def main():
    args = sys.argv[1:]
    month = None
    if "--month" in args:
        month = args[args.index("--month") + 1]
    _load_dotenv()
    cfg = dict(os.environ)
    frm, to, label = _month_bounds(month)
    cfg["_FROM"], cfg["_TO"] = frm, to

    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    print(f"Building infra cost report for {label} ...", file=sys.stderr)
    neon = fetch_neon(cfg)
    atlas = fetch_atlas(cfg)
    gcp = fetch_gcp(cfg)
    sentry = fetch_sentry(cfg)
    flags = [f for svc in (neon, atlas, gcp, sentry) for f in (svc.get("flags") or [])]
    report_md = build_report(label, neon, atlas, gcp, sentry)

    # cash out-of-pocket = the only services NOT on credits (today: Sentry)
    sentry_cash = {"team": 29.0, "business": 80.0}.get((sentry.get("plan") or "").lower(), 0.0)
    summary = {
        "out_of_pocket_usd": sentry_cash,  # Neon Free + Atlas & GCP on credits; Sentry is real cash
        "gcp_credits_total": sum(c["usd"] for c in gcp.get("credits", [])),
        "gcp_credit_pools": len(gcp.get("credits", [])),
        "atlas_mtd": atlas.get("pending_usd") or 0,
        "atlas_run_rate": atlas.get("last_invoice_usd") or 0,
        "neon_storage_mb": neon.get("total_storage_mb") or 0,
        "sentry_plan": sentry.get("plan"),
        "sentry_errors_30d": sentry.get("errors_30d"),
    }

    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, f"infra-cost-{label}.md"), "w") as f:
        f.write(report_md)

    # month-over-month history
    hist_path = os.path.join(outdir, "history.json")
    history = {}
    if os.path.exists(hist_path):
        try:
            with open(hist_path) as hf:
                history = json.load(hf)
        except Exception:
            history = {}
    history[label] = summary
    with open(hist_path, "w") as hf:
        json.dump(history, hf, indent=2)

    # branded deliverables
    import render

    pdf_path = os.path.join(outdir, f"AI-Identity-Infra-Cost-{label}.pdf")
    xlsx_path = os.path.join(outdir, f"AI-Identity-Infra-Cost-{label}.xlsx")
    render.build_pdf(label, generated, summary, flags, neon, atlas, gcp, sentry, pdf_path)
    render.build_xlsx(label, summary, flags, neon, atlas, gcp, sentry, history, xlsx_path)
    print(f"  wrote {pdf_path}\n  wrote {xlsx_path}", file=sys.stderr)
    print("\n" + report_md)

    if "--email" in args:
        send_email(
            cfg,
            f"AI Identity · Infra Cost Report · {label}",
            email_body(label, summary, flags),
            [pdf_path, xlsx_path],
        )


if __name__ == "__main__":
    main()
