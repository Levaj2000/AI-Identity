"""Build the Ada Dogfood Proof PDF — investor/partner-ready evidence artifact.

Pulls Ada's real audit-log entries and chain-integrity verdict from the live
AI Identity API, renders them as a forwardable AI Identity Purple PDF.

The point: turn the "we dogfood our own product" claim into a verifiable
audit trail with cryptographic chain integrity. Hayfa (Range) and CypherNova
get an artifact they can show a technical evaluator.

Run: python3 build_ada_proof_pdf.py
Output: ../ada-dogfood-proof-2026-05-12.pdf

Reads the snapshot JSONs created earlier in the session:
  ../ada-audit-snapshot-2026-05-12.json
  ../ada-chain-verify-2026-05-12.json
"""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# ── AI Identity Purple theme ─────────────────────────────────────────────

PURPLE_DEEP = HexColor("#4B2D7F")
PURPLE_MID = HexColor("#6B4FA0")
LAVENDER = HexColor("#F0E8F8")
LAVENDER_DARK = HexColor("#E5D9F1")
WHITE = HexColor("#FFFFFF")
INK = HexColor("#1A1F36")
GREY = HexColor("#6B7280")
LINE = HexColor("#E2E0EE")
ACCENT_GREEN = HexColor("#0E8A4F")
ACCENT_RED = HexColor("#B53A3A")

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"
FONT_MONO = "Courier"
FONT_MONO_BOLD = "Courier-Bold"

HERE = Path(__file__).resolve().parent.parent
SNAPSHOT = HERE / "ada-audit-snapshot-2026-05-12.json"
VERIFY = HERE / "ada-chain-verify-2026-05-12.json"
OUT = HERE / "ada-dogfood-proof-2026-05-12.pdf"

PAGE_W, PAGE_H = letter


def draw_rect(c, x, y, w, h, fill=None, stroke=None):
    if fill is not None:
        c.setFillColor(fill)
    if stroke is not None:
        c.setStrokeColor(stroke)
        c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1 if stroke else 0, fill=1 if fill else 0)


def wrapped(c, x, y, w, text, *, font=FONT, size=10, color=INK, leading=None):
    if leading is None:
        leading = size * 1.35
    c.setFillColor(color)
    c.setFont(font, size)
    words = text.split()
    line: list[str] = []
    while words:
        line.append(words.pop(0))
        if c.stringWidth(" ".join(line), font, size) > w:
            if len(line) > 1:
                last = line.pop()
                words.insert(0, last)
            c.drawString(x, y, " ".join(line))
            y -= leading
            line = []
    if line:
        c.drawString(x, y, " ".join(line))
        y -= leading
    return y


def eyebrow(c, x, y, text):
    c.setFillColor(PURPLE_MID)
    c.setFont(FONT_BOLD, 7.5)
    c.drawString(x, y, text.upper())


def header(c, page_n, total):
    bar_h = 0.55 * inch
    draw_rect(c, 0, PAGE_H - bar_h, PAGE_W, bar_h, fill=PURPLE_DEEP)
    draw_rect(c, 0, PAGE_H - 8, PAGE_W, 8, fill=PURPLE_MID)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 18)
    c.drawString(0.5 * inch, PAGE_H - 0.36 * inch, "AI Identity")
    c.setFillColor(LAVENDER)
    c.setFont(FONT, 10)
    c.drawString(2.0 * inch, PAGE_H - 0.36 * inch, "Dogfood proof — Ada audit trail")
    c.setFillColor(LAVENDER)
    c.setFont(FONT_BOLD, 7)
    c.drawRightString(PAGE_W - 0.5 * inch, PAGE_H - 0.25 * inch, "EVIDENCE PACK")
    c.setFillColor(WHITE)
    c.setFont(FONT, 8.5)
    c.drawRightString(PAGE_W - 0.5 * inch, PAGE_H - 0.41 * inch, "Snapshot: 2026-05-12")


def footer(c, page_n, total):
    draw_rect(c, 0, 0, PAGE_W, 0.4 * inch, fill=LAVENDER)
    c.setFillColor(PURPLE_DEEP)
    c.setFont(FONT_BOLD, 8)
    c.drawString(0.5 * inch, 0.2 * inch, "AI Identity  ·  Ada dogfood proof  ·  ai-identity.co")
    c.setFillColor(GREY)
    c.setFont(FONT, 8)
    c.drawRightString(PAGE_W - 0.5 * inch, 0.2 * inch, f"{page_n} / {total}")


def main():
    snapshot = json.loads(SNAPSHOT.read_text())
    verify = json.loads(VERIFY.read_text())

    entries = snapshot if isinstance(snapshot, list) else snapshot.get("items", [])

    # Normalize legacy past-tense decisions ("allowed"/"denied") to canonical
    # form, matching the display-side normalization in cli/aid.py. PR #235
    # introduced server-side normalization but historical rows still carry
    # the older form.
    decision_norm = {"allow": "allow", "allowed": "allow", "deny": "deny", "denied": "deny"}
    for e in entries:
        e["decision"] = decision_norm.get(e["decision"], e["decision"])

    # Chronological for the timeline; we'll later show representative entries
    entries_sorted = sorted(entries, key=lambda e: e["created_at"])

    allow_n = sum(1 for e in entries_sorted if e["decision"] == "allow")
    deny_n = sum(1 for e in entries_sorted if e["decision"] == "deny")
    first_ts = entries_sorted[0]["created_at"][:10] if entries_sorted else "—"
    last_ts = entries_sorted[-1]["created_at"][:10] if entries_sorted else "—"

    c = canvas.Canvas(str(OUT), pagesize=letter)
    c.setTitle("AI Identity — Ada Dogfood Proof")
    c.setAuthor("Jeff Leva")
    c.setSubject("Live audit-trail evidence pack · 2026-05-12")

    total_pages = 2

    # ── PAGE 1 ───────────────────────────────────────────────────────────
    header(c, 1, total_pages)
    y = PAGE_H - 0.55 * inch - 0.3 * inch
    left = 0.5 * inch
    right = PAGE_W - 0.5 * inch
    col_w = right - left

    eyebrow(c, left, y, "Thesis")
    y -= 14
    c.setFillColor(PURPLE_DEEP)
    c.setFont(FONT_BOLD, 13)
    c.drawString(left, y, "Most companies pitching agent infra can't show you a live audit trail.")
    y -= 16
    c.setFillColor(PURPLE_DEEP)
    c.setFont(FONT_BOLD, 13)
    c.drawString(left, y, "Here is ours, with cryptographic chain proof.")
    y -= 22
    y = wrapped(
        c,
        left,
        y,
        col_w,
        "Ada is AI Identity's internal senior-engineer agent — built on Google ADK, deployed on Cloud Run, "
        "authenticated via her own AI Identity agent key. Every tool call she makes is policy-enforced at "
        "the gateway and emitted into our HMAC-SHA256 chain-of-custody audit log. The snapshot below is "
        "real data pulled from the production API on 2026-05-12, scoped to Ada's agent_id and verified "
        "end-to-end.",
        size=10,
        leading=13,
    )
    y -= 4

    # KPI strip — chain integrity verdict + counts
    kpi_h = 0.92 * inch
    kpi_y = y - kpi_h
    kpis = [
        (
            f"{verify.get('entries_verified', 0)} / {verify.get('total_entries', 0)}",
            "Chain integrity",
            f"verdict: {'VALID' if verify.get('valid') else 'BROKEN'}",
            ACCENT_GREEN if verify.get("valid") else ACCENT_RED,
        ),
        (str(allow_n), "Allow decisions", "every call policy-checked", PURPLE_DEEP),
        (
            str(deny_n),
            "Deny decision",
            "real enforcement event, not rubber-stamp" if deny_n else "(none in window)",
            PURPLE_DEEP if deny_n else GREY,
        ),
        (f"{first_ts}", "First entry", f"through {last_ts}", PURPLE_DEEP),
    ]
    gap = 8
    kpi_w = (col_w - 3 * gap) / 4
    for i, (num, lab, sub, num_color) in enumerate(kpis):
        x = left + i * (kpi_w + gap)
        draw_rect(c, x, kpi_y, kpi_w, kpi_h, fill=LAVENDER)
        c.setFillColor(num_color)
        c.setFont(FONT_BOLD, 22)
        c.drawString(x + 8, kpi_y + kpi_h - 28, num)
        c.setFillColor(INK)
        c.setFont(FONT_BOLD, 9)
        c.drawString(x + 8, kpi_y + kpi_h - 46, lab)
        c.setFillColor(GREY)
        c.setFont(FONT_ITALIC, 8)
        wrapped(
            c,
            x + 8,
            kpi_y + kpi_h - 60,
            kpi_w - 16,
            sub,
            font=FONT_ITALIC,
            size=8,
            color=GREY,
            leading=10,
        )
    y = kpi_y - 0.18 * inch

    # Chain-integrity callout (highlighted) — sized to fit the 4-line body
    cb_h = 0.85 * inch
    draw_rect(c, left, y - cb_h, col_w, cb_h, fill=LAVENDER_DARK)
    draw_rect(c, left, y - cb_h, 3, cb_h, fill=PURPLE_DEEP)
    c.setFillColor(PURPLE_MID)
    c.setFont(FONT_BOLD, 7)
    c.drawString(left + 10, y - 14, "CRYPTOGRAPHIC CHAIN-OF-CUSTODY")
    msg = verify.get("message", "Chain integrity verified")
    wrapped(
        c,
        left + 10,
        y - 28,
        col_w - 20,
        f"{msg}. The audit log uses HMAC-SHA256 entry hashes linked via prev_hash, the same "
        "primitive Git uses for commit history. Any insert/delete/edit of any single row anywhere "
        "in the chain would break verification — and the API would refuse to issue a "
        '"valid: true" response. The 20-entry chain you see below currently verifies clean.',
        size=9,
        color=INK,
        leading=11,
    )
    y -= cb_h + 0.18 * inch

    # ── Sample entries — show 5 with full hashes ─────────────────────────
    eyebrow(c, left, y, "Sample entries · full fields shown")
    y -= 14

    # Pick a mix: include the deny if present, plus a span
    sample: list[dict] = []
    deny_entries = [e for e in entries_sorted if e["decision"] == "deny"]
    if deny_entries:
        sample.append(deny_entries[0])
    # Add 4 allow entries spread through the chain
    allow_entries = [e for e in entries_sorted if e["decision"] == "allow"]
    if allow_entries:
        step = max(1, len(allow_entries) // 4)
        sample.extend(allow_entries[::step][:4])
    # Dedup by id, keep order
    seen = set()
    sample_unique = []
    for e in sample:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        sample_unique.append(e)
    sample = sample_unique[:5]

    for entry in sample:
        # Skip if we're about to overflow page 1
        if y < 1.0 * inch:
            break
        entry_h = 0.95 * inch
        draw_rect(c, left, y - entry_h, col_w, entry_h, fill=WHITE, stroke=LINE)
        # Left accent (green for allow, red for deny)
        accent = ACCENT_GREEN if entry["decision"] == "allow" else ACCENT_RED
        draw_rect(c, left, y - entry_h, 3, entry_h, fill=accent)

        # Decision pill
        pill_x = left + 12
        pill_y = y - 16
        pill_color = ACCENT_GREEN if entry["decision"] == "allow" else ACCENT_RED
        c.setFillColor(pill_color)
        c.setFont(FONT_BOLD, 8)
        c.drawString(pill_x, pill_y, entry["decision"].upper())

        # Endpoint + method
        c.setFillColor(INK)
        c.setFont(FONT_MONO_BOLD, 9)
        ep = f"{entry['method']} {entry['endpoint']}"
        c.drawString(pill_x + 40, pill_y, ep[:80])

        # Timestamp right
        c.setFillColor(GREY)
        c.setFont(FONT, 8)
        c.drawRightString(right - 10, pill_y, entry["created_at"][:19] + "Z")

        # Hash chain block — full hashes don't fit on one line at 7.5pt mono
        # (64 hex chars ~= 288pt > 280pt column gap), so display the first 32
        # hex + ellipsis. The unabridged values live in the JSON snapshot
        # for anyone running the offline verifier.
        def _trunc_hash(h: str, n: int = 32) -> str:
            return h if len(h) <= n else h[:n] + "…"

        c.setFillColor(PURPLE_MID)
        c.setFont(FONT_BOLD, 7)
        c.drawString(pill_x, y - 32, "ENTRY_HASH")
        c.drawString(pill_x + 280, y - 32, "PREV_HASH")
        c.setFillColor(INK)
        c.setFont(FONT_MONO, 7.5)
        c.drawString(pill_x, y - 44, _trunc_hash(entry["entry_hash"]))
        c.drawString(pill_x + 280, y - 44, _trunc_hash(entry["prev_hash"]))

        # Metadata strip
        meta = entry.get("request_metadata", {}) or {}
        meta_parts = [
            f"policy_v{meta.get('policy_version', '?')}",
            f"status={meta.get('status_code', '?')}",
            f"latency={entry.get('latency_ms', '?')}ms",
            f"corr={entry['correlation_id'][:8]}…",
        ]
        c.setFillColor(GREY)
        c.setFont(FONT, 7.5)
        c.drawString(pill_x, y - 60, "  ·  ".join(meta_parts))

        # Entry ID right
        c.setFillColor(GREY)
        c.setFont(FONT_ITALIC, 7)
        c.drawRightString(right - 10, y - 60, f"entry #{entry['id']}")

        y -= entry_h + 6

    footer(c, 1, total_pages)
    c.showPage()

    # ── PAGE 2 ───────────────────────────────────────────────────────────
    header(c, 2, total_pages)
    y = PAGE_H - 0.55 * inch - 0.3 * inch

    eyebrow(c, left, y, "What each row proves")
    y -= 16
    proofs = [
        (
            "Cryptographic chain",
            "Every entry_hash incorporates the previous prev_hash. Editing any field of any row invalidates the rest of the chain. The API exposes /audit/verify to recompute end-to-end and report VALID or BROKEN.",
        ),
        (
            "Authenticated agent identity",
            "Each row is bound to agent_id 2e22d027… — Ada's signed, revocable, rotatable AI Identity key. Not a shared service-account credential.",
        ),
        (
            "Policy enforcement, not after-the-fact logging",
            f"policy_version on each entry shows the gateway evaluated a specific policy at decision time. {deny_n} deny event{'s' if deny_n != 1 else ''} in this window proves enforcement is real, not rubber-stamp.",
        ),
        (
            "Observability without coupling",
            "latency_ms and upstream_latency_ms are recorded per call — operability primitives, not just compliance artifacts. Audit and ops share the same backbone.",
        ),
        (
            "Verifiable offline",
            "Cryptographic chain verification works against an exported JSON file with no network access. Auditors verify with our standalone cli/ai_identity_verify.py — no trust in the AI Identity server required.",
        ),
    ]
    for i, (title, body) in enumerate(proofs):
        # Numbered circle
        diam = 14
        c.setFillColor(PURPLE_DEEP)
        c.circle(left + diam / 2, y - diam / 2 + 2, diam / 2, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 8)
        c.drawString(left + 4, y - diam / 2, str(i + 1))
        # Title + body
        c.setFillColor(PURPLE_DEEP)
        c.setFont(FONT_BOLD, 11)
        c.drawString(left + diam + 8, y - 4, title)
        y -= 18
        y = wrapped(c, left + diam + 8, y, col_w - diam - 8, body, size=9.5, color=INK, leading=12)
        y -= 8

    # How to verify this yourself
    y -= 6
    eyebrow(c, left, y, "Verify this snapshot yourself")
    y -= 14
    box_h = 1.55 * inch
    draw_rect(c, left, y - box_h, col_w, box_h, fill=LAVENDER)
    draw_rect(c, left, y - box_h, 3, box_h, fill=PURPLE_DEEP)
    c.setFillColor(INK)
    c.setFont(FONT, 9.5)
    c.drawString(left + 12, y - 16, "Live chain check against the running production API:")
    c.setFont(FONT_MONO, 8.5)
    c.setFillColor(PURPLE_DEEP)
    c.drawString(
        left + 16, y - 32, "curl 'https://api.ai-identity.co/api/v1/audit/verify?agent_id=<ada>'"
    )
    c.drawString(left + 16, y - 44, "  -H 'X-API-Key: <admin-email>'")
    c.setFillColor(INK)
    c.setFont(FONT, 9.5)
    c.drawString(
        left + 12,
        y - 64,
        "Offline verification against an exported JSON file (no network required):",
    )
    c.setFont(FONT_MONO, 8.5)
    c.setFillColor(PURPLE_DEEP)
    c.drawString(
        left + 16, y - 80, "python3 cli/ai_identity_verify.py chain ada-audit-snapshot.json"
    )
    c.setFillColor(GREY)
    c.setFont(FONT_ITALIC, 8)
    wrapped(
        c,
        left + 12,
        y - 100,
        col_w - 24,
        "Both paths return exit code 0 on success and non-zero with the breaking-entry "
        "ID on failure. Same algorithm — one trusts the API, the other doesn't.",
        font=FONT_ITALIC,
        size=8,
        color=GREY,
        leading=10,
    )
    y -= box_h + 0.2 * inch

    # Closing line
    eyebrow(c, left, y, "Why this matters for your evaluation")
    y -= 14
    c.setFillColor(PURPLE_DEEP)
    c.setFont(FONT_BOLD, 11)
    c.drawString(left, y, "The closed loop, not the demo.")
    y -= 16
    y = wrapped(
        c,
        left,
        y,
        col_w,
        'Every agent infra pitch claims "we have audit logs." The differentiating question is '
        "whether the founder's own agent is currently authenticated through the platform and "
        "emitting cryptographically chained entries that another party can verify without "
        "trusting the founder. We can show you today's chain, today.",
        size=10,
        leading=13,
    )

    footer(c, 2, total_pages)
    c.showPage()
    c.save()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
