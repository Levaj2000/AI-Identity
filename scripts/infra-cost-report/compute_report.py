#!/usr/bin/env python3
"""
AI Identity — Weekly Compute Headroom Report
============================================
Watches the compute resources the *platform's uptime depends on* and reports how
much HEADROOM each one has before it hits a hard wall. This is the inverse lens
of the monthly infra-cost report: that one asks "where can we cut?", this one
asks "where could we run out and take production down?".

Born from the 2026-06-21 incident: Neon's Free-tier compute-time quota ran out
and rejected connections on `/api/v1/keys/verify` and other paths, taking prod
down (Sentry PYTHON-FASTAPI-V/T/S + a Critical P95 alert). The lesson, set as
standing policy by the founder:

    For compute essential to the AI Identity platform running, err on the side
    of TOO MUCH rather than too little. Only consider adjusting capacity DOWN
    after ~3 months (13 consecutive weekly reports) of sustained low utilization.

So this report's default posture is to FLAG under-provisioning loudly and to
treat over-provisioning as acceptable. It will only nominate a resource for a
possible down-adjustment once the history shows 13+ straight weeks below the
low-utilization threshold — and even then it nominates, it never acts.

Reuses the proven collectors in `infra_cost_report.py` (same `.env`, same
stdlib-only / fail-soft design so launchd never breaks), and adds live Atlas
cluster utilization + GKE footprint.

Usage:
    python3 compute_report.py            # writes report to ./out/compute/
    python3 compute_report.py --email    # also emails the summary (SMTP, same as cost report)
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime

import infra_cost_report as icr  # reuse proven collectors + dotenv + email + _get

# Hard limits / capacities per resource, used to compute headroom %.
# Atlas connection ceilings and RAM by instance size (dedicated tiers).
ATLAS_TIER = {
    "M10": {"conns": 1500, "ram_mb": 2048},
    "M20": {"conns": 3000, "ram_mb": 4096},
    "M30": {"conns": 3000, "ram_mb": 8192},
    "M40": {"conns": 6000, "ram_mb": 16384},
}
# A resource is a down-adjust *candidate* only after this many straight weekly
# reports below LOW_UTIL_PCT on every tracked dimension. 13 weeks ≈ 3 months.
SUSTAINED_LOW_WEEKS = 13
LOW_UTIL_PCT = 40.0  # below this on all dimensions = "low utilization" for the week

# Status vocabulary, worst-first for the executive banner.
CRITICAL, WATCH, OK, PROTECTED = "CRITICAL", "WATCH", "OK", "PROTECTED"
_ICON = {CRITICAL: "🔴", WATCH: "🟡", OK: "🟢", PROTECTED: "🛡️"}


def _pct(used, cap):
    return round(100.0 * used / cap, 1) if cap else None


# ----------------------------------------------------------------------------- Neon
def assess_neon(cfg):
    """Neon Postgres — the resource that took prod down. On a paid plan there is
    NO hard compute-time wall (usage just bills), so 'on a paid plan' IS the
    headroom. Free tier's 191.9 compute-hr quota is the wall that broke us."""
    n = icr.fetch_neon(cfg)
    r = {"name": "Neon Postgres", "raw": n, "dims": {}, "notes": []}
    if not n.get("configured") or n.get("error"):
        r["status"] = WATCH
        r["headline"] = f"could not read Neon ({n.get('error') or n.get('note')})"
        return r
    plan = (n.get("plan") or "?").lower()
    storage_mb = n.get("total_storage_mb") or 0.0
    r["plan"] = plan
    if plan == "free":
        # This is exactly the 2026-06-21 failure mode.
        r["status"] = CRITICAL
        r["headline"] = (
            "on the FREE tier — its 191.9 compute-hr/mo quota is a hard wall that "
            "rejects DB connections when exhausted (this took prod down on 2026-06-21). "
            "Upgrade to a paid plan immediately."
        )
        r["dims"]["compute_quota"] = 100.0  # treat as maxed for scoring
        return r
    # Paid plan: no hard compute wall. Storage on Scale is effectively elastic too.
    r["status"] = PROTECTED
    r["headline"] = (
        f"on paid '{plan}' plan — no hard compute-time wall (compute auto-suspends/scales "
        f"and bills by use). {storage_mb:.0f} MB stored across "
        f"{len(n.get('projects', []))} projects."
    )
    # Storage is elastic on paid plans, so it's not a headroom % — reported in the
    # headline only. No dims means Neon is never auto-nominated for a down-adjust,
    # which is intentional: we do NOT want to downgrade it (see 2026-06-21).
    r["storage_mb"] = storage_mb
    r["notes"].append(
        "DO NOT downgrade Neon below a paid plan while prod depends on it — the Free "
        "tier's compute quota is too tight (see 2026-06-21 incident)."
    )
    return r


# ----------------------------------------------------------------------------- Atlas
def assess_atlas(cfg):
    """MongoDB Atlas — pull live cluster utilization (connections, CPU, RAM) and
    auto-scaling config. Auto-scaling compute + elastic disk = the wall moves
    out from under you, which is the posture we want."""
    pub, priv = cfg.get("ATLAS_PUBLIC_KEY"), cfg.get("ATLAS_PRIVATE_KEY")
    org = cfg.get("ATLAS_ORG_ID")
    r = {"name": "MongoDB Atlas", "dims": {}, "notes": []}
    if not (pub and priv and org):
        r["status"] = WATCH
        r["headline"] = "Atlas API keys not set — cannot read cluster headroom."
        return r
    base = "https://cloud.mongodb.com/api/atlas/v2"
    h = {"Accept": "application/vnd.atlas.2023-11-15+json"}
    try:
        groups = icr._get(f"{base}/orgs/{org}/groups", h, digest=(pub, priv)).get("results", [])
        cluster = gid = None
        for g in groups:
            cl = icr._get(f"{base}/groups/{g['id']}/clusters", h, digest=(pub, priv)).get(
                "results", []
            )
            if cl:
                cluster, gid = cl[0], g["id"]
                break
        if not cluster:
            r["status"] = WATCH
            r["headline"] = "no Atlas cluster found in the org."
            return r
        spec = (cluster.get("replicationSpecs") or [{}])[0]
        rc = (spec.get("regionConfigs") or [{}])[0]
        tier = (rc.get("electableSpecs") or {}).get("instanceSize", "?")
        autosc = (rc.get("autoScaling") or {}).get("compute") or {}
        disk_autosc = (rc.get("autoScaling") or {}).get("diskGB") or {}
        disk_gb = cluster.get("diskSizeGB")
        r["cluster"] = cluster.get("name")
        r["tier"] = tier
        r["autoscale"] = {
            "compute": autosc.get("enabled", False),
            "max": autosc.get("maxInstanceSize"),
            "disk": disk_autosc.get("enabled", False),
            "disk_gb": disk_gb,
        }
        # live utilization from the primary process
        procs = icr._get(f"{base}/groups/{gid}/processes", h, digest=(pub, priv)).get("results", [])
        primary = next((p for p in procs if p.get("typeName") == "REPLICA_PRIMARY"), None)
        primary = primary or (procs[0] if procs else None)
        cap = ATLAS_TIER.get(tier, {})
        if primary:
            pid = primary["id"]
            url = (
                f"{base}/groups/{gid}/processes/{pid}/measurements"
                f"?granularity=PT1H&period=PT6H"
                f"&m=CONNECTIONS&m=SYSTEM_NORMALIZED_CPU_USER&m=SYSTEM_MEMORY_USED"
            )
            meas = icr._get(url, h, digest=(pub, priv)).get("measurements", [])

            def last(name):
                m = next((x for x in meas if x.get("name") == name), None)
                pts = [p for p in (m or {}).get("dataPoints", []) if p.get("value") is not None]
                return pts[-1]["value"] if pts else None

            conns = last("CONNECTIONS")
            cpu = last("SYSTEM_NORMALIZED_CPU_USER")
            mem_kb = last("SYSTEM_MEMORY_USED")
            if conns is not None and cap.get("conns"):
                r["dims"]["connections"] = _pct(conns, cap["conns"])
                r["conns_raw"] = (int(conns), cap["conns"])
            if cpu is not None:
                r["dims"]["cpu"] = round(cpu, 1)
            if mem_kb is not None and cap.get("ram_mb"):
                r["dims"]["memory"] = _pct(mem_kb / 1024, cap["ram_mb"])
                r["mem_raw"] = (round(mem_kb / 1024), cap["ram_mb"])
        # Verdict: auto-scaling on both axes = protected; else judge by utilization.
        worst = max([v for v in r["dims"].values() if v is not None], default=0.0)
        if autosc.get("enabled") and disk_autosc.get("enabled") and worst < 75:
            r["status"] = PROTECTED
            r["headline"] = (
                f"{r['cluster']} on {tier} with auto-scaling ON (compute {tier}→"
                f"{autosc.get('maxInstanceSize')}, elastic disk) — wall moves with demand. "
                f"Peak utilization {worst:.0f}%."
            )
        elif worst >= 85:
            r["status"] = CRITICAL
            r["headline"] = f"{r['cluster']} ({tier}) at {worst:.0f}% on its tightest dimension."
        elif worst >= 70:
            r["status"] = WATCH
            r["headline"] = f"{r['cluster']} ({tier}) at {worst:.0f}% — watch for a tier bump."
        else:
            r["status"] = OK
            r["headline"] = f"{r['cluster']} ({tier}) at {worst:.0f}% peak — comfortable."
        if not autosc.get("enabled"):
            r["notes"].append("Atlas compute auto-scaling is OFF — enable it for a moving wall.")
    except Exception as e:  # noqa: BLE001 — fail soft so the weekly job never dies
        r["status"] = WATCH
        r["headline"] = f"Atlas read failed: {str(e)[:140]}"
    return r


# ----------------------------------------------------------------------------- GKE
def assess_gke(cfg):
    """GKE Autopilot — best-effort. Autopilot provisions per pod requests and
    auto-scales nodes, so it rarely IS the wall; this is informational. kubectl
    may be unavailable/unauth'd under launchd, so fail soft to console-only."""
    r = {"name": "GKE (Autopilot)", "dims": {}, "notes": [], "status": PROTECTED}
    kubectl = shutil.which("kubectl") or next(
        (p for p in ("/opt/homebrew/bin/kubectl", "/usr/local/bin/kubectl") if os.path.exists(p)),
        None,
    )
    try:
        if not kubectl:
            raise FileNotFoundError("kubectl not on PATH")
        env = dict(os.environ)
        env.setdefault("PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin")
        out = subprocess.run(
            [kubectl, "get", "pods", "-A", "-o", "json"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        data = json.loads(out.stdout or "{}")
        pods = data.get("items", [])
        running = [p for p in pods if p.get("status", {}).get("phase") == "Running"]
        if running:
            r["pod_count"] = len(running)
            r["headline"] = (
                f"Autopilot — {len(running)} running pods; nodes auto-provision per request. "
                "No fixed node pool to exhaust (bills pod requests on credits)."
            )
        else:
            # kubectl answered but the active context isn't the prod cluster.
            raise RuntimeError("no running pods in the active kubectl context")
    except Exception as e:  # noqa: BLE001
        r["headline"] = (
            "Autopilot auto-provisions nodes per pod request — no fixed compute wall. "
            f"(live pod read unavailable here: {str(e)[:60]}; check `kubectl top` manually.)"
        )
    return r


# ----------------------------------------------------------------------------- Sentry
def assess_sentry(cfg):
    """Sentry — a soft wall (over-quota drops events, doesn't break prod), tracked
    for completeness. Reuses the cost-report collector."""
    s = icr.fetch_sentry(cfg)
    r = {"name": "Sentry", "raw": s, "dims": {}, "notes": []}
    if not s.get("configured"):
        r["status"] = OK
        r["headline"] = "not configured."
        return r
    e = s.get("errors_30d")
    plan = (s.get("plan") or "?").title()
    if e is not None:
        r["dims"]["errors"] = _pct(e, icr.SENTRY_FREE_QUOTA)
        r["status"] = WATCH if (r["dims"]["errors"] or 0) > 80 else OK
        r["headline"] = (
            f"{plan} plan — {e} errors/30d ({r['dims']['errors']:.0f}% of the 5k free quota). "
            "Over-quota drops events; it does not take prod down."
        )
    else:
        r["status"] = OK
        r["headline"] = f"{plan} plan — volume snapshot unavailable."
    return r


# ----------------------------------------------------------------------------- history
def load_history(path):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return []
    return []


def sustained_low(history, resource_name):
    """How many consecutive most-recent weeks this resource was below LOW_UTIL_PCT
    on every tracked dimension. Used to nominate down-adjust candidates."""
    streak = 0
    for snap in reversed(history):
        dims = (snap.get("resources", {}).get(resource_name, {}) or {}).get("dims", {})
        vals = [v for v in dims.values() if isinstance(v, (int, float))]
        if vals and max(vals) < LOW_UTIL_PCT:
            streak += 1
        else:
            break
    return streak


# ----------------------------------------------------------------------------- report
def build_report(stamp, assessments, history):
    order = {CRITICAL: 0, WATCH: 1, OK: 2, PROTECTED: 3}
    ranked = sorted(assessments, key=lambda a: order.get(a["status"], 9))
    lines = [
        f"# AI Identity — Weekly Compute Headroom · {stamp}",
        "",
        "_Standing policy: for platform-essential compute, err toward TOO MUCH capacity._",
        "_Adjust DOWN only after 13 consecutive weekly reports (~3 months) of sustained low use._",
        "",
        "## Headroom at a glance",
    ]
    for a in ranked:
        lines.append(f"- {_ICON[a['status']]} **{a['name']}** — {a['status']}: {a['headline']}")
    lines.append("")

    # Down-adjust candidates (only after the sustained-low window).
    cands = []
    for a in assessments:
        if a["status"] in (CRITICAL,):
            continue
        weeks = sustained_low(history, a["name"]) if history else 0
        if weeks >= SUSTAINED_LOW_WEEKS:
            cands.append((a["name"], weeks))
    lines.append("## Down-adjust review")
    if cands:
        for name, w in cands:
            lines.append(
                f"- ⬇️ **{name}** has been below {LOW_UTIL_PCT:.0f}% on every dimension for "
                f"{w} straight weeks (≥{SUSTAINED_LOW_WEEKS}). Eligible for a capacity review — "
                "confirm the headroom isn't reserved for a launch/onboarding spike first."
            )
    else:
        weeks_map = {
            a["name"]: (sustained_low(history, a["name"]) if history else 0) for a in assessments
        }
        topname = max(weeks_map, key=weeks_map.get) if weeks_map else None
        prog = (
            f" (longest low streak: {topname} at {weeks_map.get(topname, 0)}/{SUSTAINED_LOW_WEEKS} weeks)"
            if topname
            else ""
        )
        lines.append(
            f"- None yet — hold capacity. No resource has {SUSTAINED_LOW_WEEKS} straight weeks "
            f"of sustained low utilization{prog}."
        )
    lines.append("")

    # Per-resource detail
    lines.append("## Detail")
    for a in ranked:
        lines.append(f"### {_ICON[a['status']]} {a['name']} — {a['status']}")
        lines.append(f"- {a['headline']}")
        if a.get("dims"):
            dim_str = ", ".join(
                f"{k} {v}%" if k not in ("cpu",) else f"{k} {v}%" for k, v in a["dims"].items()
            )
            lines.append(f"- Utilization: {dim_str}")
        if a.get("conns_raw"):
            lines.append(f"- Connections: {a['conns_raw'][0]} / {a['conns_raw'][1]} max")
        if a.get("mem_raw"):
            lines.append(f"- Memory: {a['mem_raw'][0]} / {a['mem_raw'][1]} MB")
        for note in a.get("notes", []):
            lines.append(f"- ⚠️ {note}")
        lines.append("")

    lines.append("---")
    lines.append(
        "_Generated by `scripts/infra-cost-report/compute_report.py`. Watches the compute "
        "resources prod uptime depends on; companion to the monthly infra-cost report._"
    )
    return "\n".join(lines)


def email_body(assessments, cands_text):
    crit = [a for a in assessments if a["status"] == CRITICAL]
    watch = [a for a in assessments if a["status"] == WATCH]
    head = (
        "ALL CLEAR — every platform-essential compute resource has headroom."
        if not crit and not watch
        else f"{len(crit)} critical, {len(watch)} to watch."
    )
    lines = [
        "AI Identity — Weekly Compute Headroom",
        "",
        head,
        "",
    ]
    for a in assessments:
        lines.append(f"  {_ICON[a['status']]} {a['name']} [{a['status']}]: {a['headline']}")
    lines += [
        "",
        cands_text,
        "",
        "Full report attached.",
        "",
        "— Weekly compute-headroom job (CTO automation).",
    ]
    return "\n".join(lines)


# ----------------------------------------------------------------------------- main
def main():
    args = sys.argv[1:]
    icr._load_dotenv()
    cfg = dict(os.environ)
    frm, to, _ = icr._month_bounds(None)
    cfg["_FROM"], cfg["_TO"] = frm, to

    now = datetime.now(UTC)
    stamp = now.strftime("%Y-%m-%d")
    print(f"Building weekly compute headroom report for {stamp} ...", file=sys.stderr)

    assessments = [assess_neon(cfg), assess_atlas(cfg), assess_gke(cfg), assess_sentry(cfg)]

    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "compute")
    os.makedirs(outdir, exist_ok=True)
    hist_path = os.path.join(outdir, "compute_history.json")
    history = load_history(hist_path)

    report_md = build_report(stamp, assessments, history)

    # Append this week's snapshot (status + dims only — small, for trend/down-adjust logic).
    snapshot = {
        "date": stamp,
        "resources": {
            a["name"]: {"status": a["status"], "dims": a.get("dims", {})} for a in assessments
        },
    }
    history = [h for h in history if h.get("date") != stamp] + [snapshot]
    with open(hist_path, "w") as f:
        json.dump(history, f, indent=2)

    md_path = os.path.join(outdir, f"compute-headroom-{stamp}.md")
    with open(md_path, "w") as f:
        f.write(report_md)
    print(f"  wrote {md_path}", file=sys.stderr)
    print("\n" + report_md)

    if "--email" in args:
        # Recompute the candidate line for the email body.
        cands = [
            (a["name"], sustained_low(history, a["name"]))
            for a in assessments
            if a["status"] != CRITICAL and sustained_low(history, a["name"]) >= SUSTAINED_LOW_WEEKS
        ]
        cands_text = (
            "Down-adjust candidates: " + ", ".join(f"{n} ({w}wk low)" for n, w in cands)
            if cands
            else "Down-adjust candidates: none — holding capacity per policy."
        )
        icr.send_email(
            cfg,
            f"AI Identity · Weekly Compute Headroom · {stamp}",
            email_body(assessments, cands_text),
            [md_path],
        )


if __name__ == "__main__":
    main()
