"""Executive R&D Report — Agent Accountability Standards: Landscape & Next Bet (Q3 2026).

First deliverable from the `standards-architect` Claude Code engine (2026-06-09).
AI Identity Purple template, portrait letter PDF. Reproducible source.

Grounded in: live GitHub status of OCSF PRs #1641/#1661/#1662/#1665 (via gh), the local
OCSF clone, and three parallel web-research passes (OCSF AI WG, CoSAI/NIST/EU frameworks,
adjacent agent-identity standards). Every load-bearing claim is footnoted.

Run: python3 docs/strategy/build_rd_landscape_report.py
"""

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

# ── AI Identity Purple theme ─────────────────────────────────────────────
PURPLE_DEEP = HexColor("#4B2D7F")
PURPLE_MID = HexColor("#6B4FA0")
LAVENDER = HexColor("#F0E8F8")
WHITE = HexColor("#FFFFFF")
INK = HexColor("#1A1F36")
GREY = HexColor("#6B7280")
LINE = HexColor("#E2E0EE")
GREEN = HexColor("#1E7F4F")
AMBER = HexColor("#B7791F")

REG, BOLD, ITAL = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"
MONO = "Courier"

PAGE_W, PAGE_H = letter  # 612 x 792
LEFT = 54
CONTENT_W = PAGE_W - 2 * LEFT
FOOTER = "AI Identity  ·  R&D Landscape Report  ·  2026-06-09"
OUT = Path(__file__).resolve().parent / "ai-identity-rd-landscape-report-2026-06-09.pdf"

_page = [0]


def rect(c, x, top, w, h, fill=None, stroke=None, sw=0.5):
    if fill:
        c.setFillColor(fill)
    if stroke:
        c.setStrokeColor(stroke)
        c.setLineWidth(sw)
    c.rect(x, PAGE_H - top - h, w, h, stroke=1 if stroke else 0, fill=1 if fill else 0)


def text(c, x, top, s, font=REG, size=10, color=INK, align="l"):
    c.setFont(font, size)
    c.setFillColor(color)
    y = PAGE_H - top - size
    if align == "l":
        c.drawString(x, y, s)
    elif align == "r":
        c.drawRightString(x, y, s)
    else:
        c.drawCentredString(x, y, s)


def wrap(s, font, size, max_w):
    out = []
    for raw in s.split("\n"):
        words, cur = raw.split(" "), ""
        for w in words:
            trial = w if not cur else cur + " " + w
            if stringWidth(trial, font, size) <= max_w:
                cur = trial
            else:
                if cur:
                    out.append(cur)
                cur = w
        out.append(cur)
    return out


def para(c, x, top, s, font=REG, size=10, color=INK, leading=14, max_w=CONTENT_W):
    for ln in wrap(s, font, size, max_w):
        text(c, x, top, ln, font, size, color)
        top += leading
    return top


def chrome(c, eyebrow):
    rect(c, 0, 0, PAGE_W, 7, fill=PURPLE_MID)
    text(c, LEFT, 30, eyebrow.upper(), BOLD, 8.5, PURPLE_MID)
    rect(c, 0, PAGE_H - 34, PAGE_W, 0.6, fill=LINE)
    text(c, LEFT, PAGE_H - 28, FOOTER, REG, 7.5, GREY)
    text(c, PAGE_W - LEFT, PAGE_H - 28, f"{_page[0]}", REG, 7.5, GREY, align="r")


def newpage(c, eyebrow):
    if _page[0] > 0:
        c.showPage()
    _page[0] += 1
    chrome(c, eyebrow)


def h1(c, top, s):
    top = para(c, LEFT, top, s, BOLD, 19, PURPLE_DEEP, leading=23)
    return top + 6


def bullet(c, x, top, s, size=9.5, lead=13, color=INK, mark="•", mark_color=PURPLE_MID):
    text(c, x, top, mark, BOLD, size, mark_color)
    lines = wrap(s, REG, size, CONTENT_W - (x - LEFT) - 14)
    for ln in lines:
        text(c, x + 14, top, ln, REG, size, color)
        top += lead
    return top + 2


def callout(c, top, title, body, accent=PURPLE_MID, bg=LAVENDER, h=None):
    lines = wrap(body, REG, 9, CONTENT_W - 28)
    box_h = h or (20 + len(lines) * 12 + 8)
    rect(c, LEFT, top, CONTENT_W, box_h, fill=bg)
    rect(c, LEFT, top, 4, box_h, fill=accent)
    text(c, LEFT + 14, top + 9, title.upper(), BOLD, 8, accent)
    yy = top + 23
    for ln in lines:
        text(c, LEFT + 14, yy, ln, REG, 9, INK)
        yy += 12
    return top + box_h + 10


def sup(c, x, top, n, size=9.5):
    """superscript citation marker, returns x advance"""
    c.setFont(BOLD, 6.5)
    c.setFillColor(PURPLE_MID)
    c.drawString(x, PAGE_H - top - size + 4, str(n))
    return stringWidth(str(n), BOLD, 6.5)


def sources(c, top, items):
    text(c, LEFT, top, "SOURCES", BOLD, 7.5, GREY)
    top += 12
    for n, s in items:
        text(c, LEFT, top, f"{n}", BOLD, 7, PURPLE_MID)
        for ln in wrap(s, REG, 7, CONTENT_W - 14):
            text(c, LEFT + 12, top, ln, REG, 7, GREY)
            top += 9
        top += 2
    return top


# ═══════════════════════════════════════════════════════════════════════
c = canvas.Canvas(str(OUT), pagesize=letter)

# ── COVER ────────────────────────────────────────────────────────────────
_page[0] = 1
rect(c, 0, 0, PAGE_W, PAGE_H, fill=PURPLE_DEEP)
rect(c, 0, 0, 14, PAGE_H, fill=PURPLE_MID)
text(c, LEFT, 150, "EXECUTIVE R&D REPORT", BOLD, 11, HexColor("#C9B8E8"))
para(c, LEFT, 190, "Agent Accountability\nStandards", BOLD, 38, WHITE, leading=44, max_w=CONTENT_W)
para(
    c,
    LEFT,
    300,
    "Landscape, AI Identity's position, and the next bet",
    REG,
    15,
    HexColor("#D8CBEF"),
    leading=20,
    max_w=CONTENT_W,
)
rect(c, LEFT, 345, 90, 2, fill=PURPLE_MID)
para(
    c,
    LEFT,
    365,
    "The identity and authorization layer for AI agents is consolidating fast — and "
    "every standard in it defers the tamper-evident, non-repudiable audit layer. That "
    "omission is the bet.",
    ITAL,
    11.5,
    HexColor("#C9B8E8"),
    leading=17,
    max_w=CONTENT_W - 40,
)
# prepared-for block
yb = 640
text(c, LEFT, yb, "PREPARED FOR", BOLD, 8, PURPLE_MID)
text(c, LEFT, yb + 12, "Jeff Leva, Founder — AI Identity", REG, 10.5, WHITE)
text(c, LEFT, yb + 34, "GENERATED BY", BOLD, 8, PURPLE_MID)
text(c, LEFT, yb + 46, "standards-architect engine (Claude Code, Opus 4.8)", REG, 10.5, WHITE)
text(c, LEFT, yb + 68, "DATE", BOLD, 8, PURPLE_MID)
text(c, LEFT, yb + 80, "2026-06-09  ·  grounded in live GitHub + web research", REG, 10.5, WHITE)

# ── PAGE 2 — EXECUTIVE SUMMARY ───────────────────────────────────────────
newpage(c, "Executive summary · the one bet")
t = h1(c, 56, "The bet: become the non-repudiation layer of record")
t = para(
    c,
    LEFT,
    t,
    "Standardization of AI agents has split into two layers. The identity + authorization "
    "layer — who an agent is and what it may do — is consolidating quickly across MCP, A2A, "
    "the OAuth-for-agents stack, and OpenID's accountability group. The forensic layer — "
    "tamper-evident, signed, replayable proof of what an agent actually did — is named as a "
    "requirement by regulators and governance bodies, but no standard carries it. That gap is "
    "durable, dated, and unclaimed.",
    REG,
    10.5,
    INK,
    leading=15,
)
t += 8
t = callout(
    c,
    t,
    "Recommendation",
    "Make AI Identity the non-repudiation layer of record for agent activity: drive the OCSF "
    "generic non-repudiation / tamper-evident-logging profile (AI as first consumer) and ship "
    "the conformant emitter — timed to the EU AI Act record-keeping clauses that bind from "
    "Aug 2026. The precondition just landed: our serialization primitive (#1662) merged today.",
    accent=PURPLE_DEEP,
)
t = callout(
    c,
    t,
    "Immediate next move  (not the destination)",
    "Get #1661 (attestation) over its review bar, and post a SHORT supportive note on Ania's "
    "freshly-filed #1665 (delegation) proposing the attestation-to-delegation seam as a "
    "question to her — listen-first. File the profile only after #1661 proves the pattern and "
    "the room signals. The profile is the prize; the seam is the step.",
    accent=GREEN,
    bg=HexColor("#EAF5EF"),
)
t += 2
t = para(c, LEFT, t, "Why now — three things converged this week:", BOLD, 10.5, INK, leading=15)
t = bullet(
    c,
    LEFT,
    t,
    "Our signature-canonicalization primitive (#1662) MERGED into the OCSF "
    "development line — the first piece of the forensics agenda to actually land.",
)
t = bullet(
    c,
    LEFT,
    t,
    "Ania filed the delegation object (#1665) — the seam we'd been holding "
    "for is now live and proposable, with her.",
)
t = bullet(
    c,
    LEFT,
    t,
    "The EU AI Act's logging / record-keeping obligations for high-risk "
    "systems bind from Aug 2026, with the technical standards still in draft — leadership room.",
)

# ── PAGE 3 — STATE OF PLAY ───────────────────────────────────────────────
newpage(c, "State of play · what's merged, who owns what")
t = h1(c, 56, "State of play")
t = para(
    c,
    LEFT,
    t,
    "OCSF — the schema layer AI Identity profiles as its forensic envelope:",
    BOLD,
    10.5,
    INK,
    leading=15,
)
t = bullet(
    c,
    LEFT,
    t,
    "AI observability shipped in OCSF 1.8.0 (Mar 2026): ai_operation profile, "
    "ai_model, message_context. The foundation is in a tagged release.",
)
t = bullet(
    c,
    LEFT,
    t,
    "Agent-identity layer is in OPEN PRs: #1641 (ai_agent) and #1665 "
    "(delegation), both Ania's (Cisco). Umbrella issue #1640 defines the full design — a new "
    "AI category (uid 9, not 7), control-plane classes (agent_activity, delegation_activity), "
    "and a delegation-lineage graph — none filed yet.",
)
t = bullet(
    c,
    LEFT,
    t,
    "Non-repudiation wedge (ours): #1662 (serialization on digital_signature) "
    "MERGED 2026-06-09 to the dev line the maintainer calls '1.9.0-dev' — no 1.9.0 tag exists "
    "yet. #1661 (attestation object) is OPEN, needs its approvals.",
)
t = bullet(
    c,
    LEFT,
    t,
    "The maintainer roadmap (AWS) is silent on attestation / non-repudiation "
    "/ forensics — this is a bottom-up wedge, which is both the opening and the risk.",
)
t += 4
t = para(
    c,
    LEFT,
    t,
    "The wider field — identity consolidating, audit deferred:",
    BOLD,
    10.5,
    INK,
    leading=15,
)
t = bullet(
    c,
    LEFT,
    t,
    "MCP and A2A were both donated to the Linux Foundation's new Agentic AI "
    "Foundation (Dec 2025 / Jun 2025). Platinum members: AWS, Anthropic, Block, Bloomberg, "
    "Cloudflare, Google, Microsoft, OpenAI.",
)
t = bullet(
    c,
    LEFT,
    t,
    "Auth is solved-ish: MCP on OAuth 2.1 + Resource Indicators (no audit "
    "section); A2A via Agent Cards (TLS + bearer tokens, no signed action log); the "
    "OAuth-for-agents stack (ID-JAG / Cross-App Access, Transaction Tokens, on-behalf-of) "
    "races to model delegated authority chains.",
)
t = bullet(
    c,
    LEFT,
    t,
    "Governance venues are explicitly asking for accountability: NIST's "
    "NCCoE concept paper names 'logging and transparency' and 'access delegation for "
    "accountability'; OpenID's AIIM group lists accountability in its top-three scope.",
)
t = callout(
    c,
    t,
    "The white space, confirmed by omission",
    "No identity or authorization standard carries normative tamper-evident or non-repudiation "
    "requirements. OpenTelemetry GenAI — the de-facto agent telemetry convention — explicitly "
    "disclaims the immutable / audit-ready layer. Nobody has filled this; the venues are "
    "asking who will.",
    accent=AMBER,
    bg=HexColor("#FBF4E6"),
)
t = sources(
    c,
    t + 2,
    [
        (
            "1",
            "OCSF: gh PR status #1641/#1661/#1662/#1665 (2026-06-09); ocsf/ocsf-schema issue #1640; AWS Open Source blog, OCSF 1.8.0 / ITU support (Mar 2026).",
        ),
        (
            "2",
            "Linux Foundation press, Agentic AI Foundation + A2A project (Dec 2025 / Jun 2025); modelcontextprotocol.io authorization spec 2025-11-25; a2a-protocol.org v0.3.0.",
        ),
        (
            "3",
            "NIST CAISI AI Agent Standards Initiative + NCCoE concept paper (Feb 2026); OpenID AIIM Community Group; opentelemetry.io GenAI semantic conventions.",
        ),
    ],
)

# ── PAGE 4 — POSITION & MOAT ─────────────────────────────────────────────
newpage(c, "AI Identity's position · the moat")
t = h1(c, 56, "Where we stand")
t = bullet(
    c,
    LEFT,
    t,
    "Two things our product already emits map cleanly onto the schema: the "
    "gateway audit_log (immutable per-action rows, HMAC-SHA256 hash chain, per-org chains) maps "
    "to the attestation object; the Mandate Service (signed delegation grants, ECDSA-P256 over "
    "RFC 8785 / JCS, hybrid classical+PQC signature array) maps to delegation + digital_signature.",
)
t = bullet(
    c,
    LEFT,
    t,
    "We hold the canonical-serialization primitive (#1662, merged) that the "
    "whole non-repudiation chain signs over — and the attestation object (#1661) that binds "
    "agent identity to a signed, tamper-evident record. Both are deliberately domain-agnostic: "
    "AI is the first consumer, not the only one.",
)
t = bullet(
    c,
    LEFT,
    t,
    "Framing authority: AI Identity anchored the 'AI forensics as its own "
    "concern' boundary in the working group, and was offered OCSF reviewer (approver) status — "
    "shaping power over what AI-related schema lands, not just contributor status.",
)
t += 6
t = callout(
    c,
    t,
    "The moat is ordering, not features",
    "Non-repudiation grows upward from an identity root and a canonical serialization — it "
    "cannot be retrofitted onto telemetry after the fact. Detection/response tools (e.g. "
    "AgentDR) are downstream consumers of a non-repudiable record, not competitors to it. "
    "Whoever owns the signing-from-identity layer is upstream of the entire accountability "
    "stack.",
    accent=PURPLE_DEEP,
)
t = para(c, LEFT, t, "Two honest caveats, attached:", BOLD, 10.5, INK, leading=15)
t = bullet(
    c,
    LEFT,
    t,
    "Concentration / framing risk: the agentic-AI schema effort currently "
    "rests on two contributors (Ania + Jeff) with no visible big-vendor co-sponsor on these "
    "specific PRs. 'Define the standard' is the upside — IF a co-sponsor and the review process "
    "hold; the PRs could still be reshaped.",
    color=INK,
)
t = bullet(
    c,
    LEFT,
    t,
    "'Merged' discipline: only #1662 is merged (to the dev line; no 1.9.0 "
    "release tag). Externally, say 'contributing to OCSF' and cite #1662 as the merged proof "
    "point — do not claim the rest has landed.",
    color=INK,
)
t = sources(
    c,
    t + 4,
    [
        (
            "4",
            "AI Identity repo: gateway audit_log (common/audit), Mandate Service (mandate/app, ECDSA-P256 / JCS, hybrid PQC array); memory project_ocsf_engagement, project_mandate_service.",
        ),
        (
            "5",
            "OCSF PR #1662 (merged 2026-06-09), PR #1661 (open); working-group provenance notes (2026-05-29 → 06-09).",
        ),
    ],
)

# ── PAGE 5 — THE THREE LANES ─────────────────────────────────────────────
newpage(c, "Open lanes · ranked by actionability")
t = h1(c, 56, "The three open lanes")
t = para(
    c,
    LEFT,
    t,
    "Ranked by what we can act on and where being wrong is costliest — not by novelty.",
    ITAL,
    9.5,
    GREY,
    leading=13,
)
t += 4


def lane(c, top, n, title, body, tag, tag_color):
    rect(c, LEFT, top, CONTENT_W, 1, fill=LINE)
    top += 10
    c.setFillColor(PURPLE_DEEP)
    c.circle(LEFT + 9, PAGE_H - top - 7, 9, fill=1, stroke=0)
    text(c, LEFT + 9, top + 1.5, str(n), BOLD, 10, WHITE, align="c")
    text(c, LEFT + 28, top, title, BOLD, 11.5, INK)
    tw = stringWidth(tag, BOLD, 7.5) + 12
    rect(c, PAGE_W - LEFT - tw, top - 1, tw, 14, fill=tag_color)
    text(c, PAGE_W - LEFT - tw / 2, top + 1.5, tag, BOLD, 7.5, WHITE, align="c")
    top += 18
    top = para(c, LEFT + 28, top, body, REG, 9.5, INK, leading=13, max_w=CONTENT_W - 28)
    return top + 8


t = lane(
    c,
    t,
    1,
    "Non-repudiation profile + conformant emitter (OCSF)",
    "The category-defining move. Precondition #1662 merged; #1665 (delegation) just filed, so "
    "the attestation-to-delegation seam is now proposable. NIST/OpenID/EU all asking for "
    "accountability. Lane: ours (#1661) + a seam with Ania (#1665) — propose with her, never "
    "redefine her object.",
    "ACT NOW",
    GREEN,
)
t = lane(
    c,
    t,
    2,
    "Post-quantum-signed evidence records",
    "Differentiator and standards-forward. ML-DSA (FIPS 204) is shipping in CAs and crypto "
    "libraries, yet no agent standard mandates or even profiles PQ signatures for credentials "
    "or audit records — and audit records need decades-long integrity (harvest-now, "
    "verify-later). Aligns with the H2 Mandate Service hybrid design already on the books. "
    "Lower urgency, ours to claim.",
    "BUILD-IN",
    PURPLE_MID,
)
t = lane(
    c,
    t,
    3,
    "Regulatory mapping (EU AI Act / NIST NCCoE)",
    "Highest demand-generation, dated to Q4 2026. Map the forensic-audit capability to the AI "
    "Act's record-keeping / logging / traceability clauses and NCCoE's accountability pillar. "
    "This is the wedge into regulated verticals — the medical full-audit-chain use case a "
    "third party raised in the WG is the lead example. More GTM/compliance than R&D, but it is "
    "what turns the standard into revenue.",
    "FRAME",
    AMBER,
)
t += 2
t = callout(
    c,
    t,
    "These are complementary, not exclusive",
    "Lane 1 wins the seat and ships the reference implementation; Lane 3 supplies the dated "
    "demand that justifies it; Lane 2 is the differentiator you bake into Lane 1's records "
    "rather than a separate project. Sequence, don't choose.",
    accent=PURPLE_DEEP,
)

# ── PAGE 6 — THE BET, STACK-CHECKED ──────────────────────────────────────
newpage(c, "Recommended bet · evaluated vs. our stack")
t = h1(c, 56, "The bet, checked against our stack")
t = para(
    c,
    LEFT,
    t,
    "Make AI Identity the non-repudiation layer of record for agent activity — "
    "drive the OCSF generic non-repudiation profile and ship the conformant emitter, timed to "
    "the EU AI Act Q4 2026 forcing function.",
    BOLD,
    10.5,
    INK,
    leading=15,
)
t += 6


def check(c, top, mark, mark_color, label, body):
    text(c, LEFT, top, mark, BOLD, 11, mark_color)
    text(c, LEFT + 18, top, label, BOLD, 9.5, INK)
    top = para(c, LEFT + 18, top + 12, body, REG, 9.5, INK, leading=12.5, max_w=CONTENT_W - 18)
    return top + 6


t = check(
    c,
    t,
    "✓",
    GREEN,
    "Operational surface — low",
    "Additive to services we already run (gateway, Mandate). No new always-on infrastructure, "
    "which matters on GCP-credit runway.",
)
t = check(
    c,
    t,
    "✓",
    GREEN,
    "Dogfoodable",
    "We already emit the primitives on our own dashboard's verified agents — the emitter proves "
    "itself against our own audit trail.",
)
t = check(
    c,
    t,
    "✓",
    GREEN,
    "Solo-runnable",
    "Standards work + an emitter profile is one-person-shippable; it does not require a team to "
    "operate, unlike a detection/response product.",
)
t = check(
    c,
    t,
    "✓",
    GREEN,
    "Crypto-agility",
    "The signature array (classical + reserved ML-DSA slot) is already designed — Lane 2 folds "
    "in without rework.",
)
t = check(
    c,
    t,
    "~",
    AMBER,
    "Spec alignment — verify",
    "The profile must match the published spec's L2 session-attestation (DSSE + ES256). Align "
    "the profile to the spec, or update the spec with a section number — don't let them drift.",
)
t += 4
t = callout(
    c,
    t,
    "Risks & conditions",
    "(1) No big-vendor co-sponsor yet — recruit one before over-investing. (2) EU AI Act "
    "technical standards are still in draft — map to them as leadership, but never claim "
    "conformance to a standard that isn't published. (3) Lane discipline: the delegation seam "
    "is Ania's — the win is a joint proposal, not a unilateral one.",
    accent=AMBER,
    bg=HexColor("#FBF4E6"),
)
t = callout(
    c,
    t,
    "Verdict",
    "Build. The bet survives every stack-fit check, the precondition merged this week, the "
    "venue is asking, and the regulatory clock is running. The only gating move is social, not "
    "technical: clear #1661, and open the seam with Ania on #1665.",
    accent=GREEN,
    bg=HexColor("#EAF5EF"),
)

c.showPage()
c.save()
print(f"wrote {OUT}  ({OUT.stat().st_size:,} bytes, {_page[0]} pages)")
