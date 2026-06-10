"""Frontier R&D Horizon Report — Agent Accountability in 2030.

Second run of the `standards-architect` engine (2026-06-09), recalibrated to FRONTIER altitude
(3-5 year horizon) after feedback that the first report read CTO-tactical. AI Identity Purple,
portrait letter PDF, reproducible source.

Grounded in five parallel frontier-research passes (cryptography beyond PQC; agent-economy
settlement; trust topology at scale; AI forensics as a legal discipline; accountability
architecture at extreme scale), each separating cited 2024-2026 signal from 2030 extrapolation.

Run: python3 docs/strategy/build_rd_horizon_report.py
"""

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

PURPLE_DEEP = HexColor("#4B2D7F")
PURPLE_MID = HexColor("#6B4FA0")
LAVENDER = HexColor("#F0E8F8")
WHITE = HexColor("#FFFFFF")
INK = HexColor("#1A1F36")
GREY = HexColor("#6B7280")
LINE = HexColor("#E2E0EE")
GREEN = HexColor("#1E7F4F")
AMBER = HexColor("#B7791F")
SIGNAL_BG = HexColor("#EAF1FB")
SIGNAL_AC = HexColor("#2C5FA8")

REG, BOLD, ITAL = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"
PAGE_W, PAGE_H = letter
LEFT = 54
CONTENT_W = PAGE_W - 2 * LEFT
FOOTER = "AI Identity  ·  Frontier R&D Horizon Report  ·  2026-06-09"
OUT = Path(__file__).resolve().parent / "ai-identity-rd-horizon-2030-report-2026-06-09.pdf"
_pg = [0]


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
    (c.drawString if align == "l" else c.drawRightString if align == "r" else c.drawCentredString)(
        x, y, s
    )


def wrap(s, font, size, max_w):
    out = []
    for raw in s.split("\n"):
        cur = ""
        for w in raw.split(" "):
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
    text(c, PAGE_W - LEFT, PAGE_H - 28, f"{_pg[0]}", REG, 7.5, GREY, align="r")


def newpage(c, eyebrow):
    if _pg[0] > 0:
        c.showPage()
    _pg[0] += 1
    chrome(c, eyebrow)


def h1(c, top, s):
    return para(c, LEFT, top, s, BOLD, 18, PURPLE_DEEP, leading=22) + 6


def bullet(c, x, top, s, size=9.5, lead=12.5, color=INK, mark="•", mc=PURPLE_MID, mw=14):
    text(c, x, top, mark, BOLD, size, mc)
    for ln in wrap(s, REG, size, CONTENT_W - (x - LEFT) - mw):
        text(c, x + mw, top, ln, REG, size, color)
        top += lead
    return top + 2


def callout(c, top, title, body, accent=PURPLE_MID, bg=LAVENDER, body_size=9):
    lines = wrap(body, REG, body_size, CONTENT_W - 28)
    box_h = 20 + len(lines) * (body_size + 3) + 8
    rect(c, LEFT, top, CONTENT_W, box_h, fill=bg)
    rect(c, LEFT, top, 4, box_h, fill=accent)
    text(c, LEFT + 14, top + 9, title.upper(), BOLD, 8, accent)
    yy = top + 23
    for ln in lines:
        text(c, LEFT + 14, yy, ln, REG, body_size, INK)
        yy += body_size + 3
    return top + box_h + 10


def vector(c, top, name, signal, extrap, disco):
    """A frontier vector card: name, Signal(cited), Extrapolation, Discontinuity."""
    top = para(c, LEFT, top, name, BOLD, 11, INK, leading=14)
    top += 2
    text(c, LEFT, top, "SIGNAL", BOLD, 7, SIGNAL_AC)
    top = para(c, LEFT + 42, top, signal, REG, 9, INK, leading=12)
    top += 1
    text(c, LEFT, top, "→ 2030", BOLD, 7, PURPLE_MID)
    top = para(c, LEFT + 42, top, extrap, REG, 9, INK, leading=12)
    top += 1
    text(c, LEFT, top, "FOR US", BOLD, 7, GREEN)
    top = para(c, LEFT + 42, top, disco, ITAL, 9, HexColor("#33405C"), leading=12)
    return top + 8


def sources(c, top, items):
    text(c, LEFT, top, "SIGNALS (cited)", BOLD, 7.5, GREY)
    top += 11
    for n, s in items:
        text(c, LEFT, top, n, BOLD, 7, SIGNAL_AC)
        for ln in wrap(s, REG, 7, CONTENT_W - 16):
            text(c, LEFT + 14, top, ln, REG, 7, GREY)
            top += 8.6
        top += 1.5
    return top


c = canvas.Canvas(str(OUT), pagesize=letter)

# ── COVER ────────────────────────────────────────────────────────────────
_pg[0] = 1
rect(c, 0, 0, PAGE_W, PAGE_H, fill=PURPLE_DEEP)
rect(c, 0, 0, 14, PAGE_H, fill=PURPLE_MID)
text(c, LEFT, 130, "FRONTIER R&D · HORIZON 2029–2031", BOLD, 11, HexColor("#C9B8E8"))
para(c, LEFT, 168, "Agent\nAccountability\nin 2030", BOLD, 40, WHITE, leading=46)
para(
    c,
    LEFT,
    330,
    "What becomes the durable asset when signing commoditizes,\nidentity fragments, and evidence decides who pays",
    REG,
    13.5,
    HexColor("#D8CBEF"),
    leading=19,
)
rect(c, LEFT, 392, 90, 2, fill=PURPLE_MID)
para(
    c,
    LEFT,
    412,
    "Five independent frontier scans converged on one answer: the thing worth owning in 2030 "
    "is not the signature, the identity, or the payment rail — it is the canonical, verifiable "
    "evidence record that outlives them all.",
    ITAL,
    11.5,
    HexColor("#C9B8E8"),
    leading=17,
    max_w=CONTENT_W - 30,
)
yb = 648
for i, (lbl, val) in enumerate(
    [
        ("PREPARED FOR", "Jeff Leva, Founder — AI Identity"),
        ("GENERATED BY", "standards-architect engine (Claude Code, Opus 4.8) — frontier mode"),
        ("METHOD", "5 parallel research passes · cited 2024–2026 signal + 2030 extrapolation"),
        ("DATE", "2026-06-09"),
    ]
):
    text(c, LEFT, yb + i * 30, lbl, BOLD, 8, PURPLE_MID)
    text(c, LEFT, yb + i * 30 + 12, val, REG, 10, WHITE)

# ── PAGE 2 — THE 2030 THESIS ─────────────────────────────────────────────
newpage(c, "The 2030 thesis · the inversion")
t = h1(c, 54, "The inversion: evidence becomes the scarce asset")
t = para(
    c,
    LEFT,
    t,
    'Today AI Identity\'s pitch is "we sign and hash-chain every agent action." That is a feature, '
    "and by 2030 it is a commodity — NIST already standardized the signatures, and the entire "
    "industry is racing to build per-action authorization. The frontier research says the value "
    "moves somewhere non-obvious. Four forces are converging:",
    REG,
    10.5,
    INK,
    leading=14.5,
)
t += 4
t = bullet(
    c,
    LEFT,
    t,
    "Signing commoditizes — a signature proves *who*; it's the cheapest, most "
    "solved part of the stack (and it batches away almost completely at scale).",
)
t = bullet(
    c,
    LEFT,
    t,
    "Identity fragments — SPIFFE/WIMSE inside the enterprise, DIDs/VCs at the "
    "edges, registries for discovery. No single agent passport wins; identity is ephemeral, "
    "minted thousands of times a second.",
)
t = bullet(
    c,
    LEFT,
    t,
    "Payment rails multiply — AP2, ACP, x402, and the card networks each "
    "re-invented the signed mandate, bound to their own rail. The rail commoditizes.",
)
t = bullet(
    c,
    LEFT,
    t,
    "Prevention statistically fails at scale — at billions of recursive agents, "
    "per-action gates are guaranteed to have gaps; you cannot stop everything.",
)
t += 6
t = callout(
    c,
    t,
    "The non-obvious conclusion",
    "What survives all four is the EVIDENCE — the canonical, cryptographically-bound, "
    "independently-verifiable record of what an agent did, under whose authority, and why, that "
    "remains meaningful after the agents, tokens, trust domains, and rails are gone. The 2030 "
    'winner owns the evidence *format* and the substrate that produces it — the "PDF/A of agent '
    'forensics" — not the signature algorithm. That slot is, today, unclaimed.',
    accent=PURPLE_DEEP,
)
t = callout(
    c,
    t,
    "Why this isn't a CTO answer",
    "It reframes the company from a logging feature (commoditizing) to the evidentiary substrate "
    "of the agent economy (a standards-and-legal land-grab). The bets below are cheap to seed now "
    "and asymmetric: each compounds the OCSF seat already in flight, and each is defensible on "
    "legal-engineering + standards neutrality, not code anyone can clone.",
    accent=GREEN,
    bg=HexColor("#EAF5EF"),
)

# ── PAGE 3 — VECTORS: THE 'HOW' ──────────────────────────────────────────
newpage(c, "Frontier vectors · the cryptographic & scale 'how'")
t = h1(c, 54, "How the substrate gets built")
t = vector(
    c,
    t,
    "1 · Cryptography beyond PQC — own the receipt, not the algorithm",
    "ZK proving cost is falling ~10x/yr; Lagrange DeepProve-1 proved a full LLM inference (Aug "
    "2025). Recursive folding (Nova→HyperNova) compresses millions of proofs into one O(1)-"
    "verifiable object. IETF SCITT defines transparency-service *receipts* over signed statements.",
    "The durable primitive is a SCITT-style receipt over a quantum-safe verifiable data "
    "structure, carrying a pluggable ZK proof of *policy compliance* (prove an agent obeyed "
    "without revealing the data) — not the signature, which is solved. PQC is the baseline; "
    "post-quantum ZK + aggregation is the frontier for evidence with decade-long retention.",
    "Be crypto-agile at the PROOF and AGGREGATION layer, not just the signature layer. The "
    "evidence object — {signed action + policy-proof + receipt + aggregation membership} — is the "
    "product a regulator buys, and it's unclaimed.",
)
t = vector(
    c,
    t,
    '2 · Accountability at scale — "commit everything, prove on demand"',
    "The wall at 10^12 agents is NOT signing (it batches to ~nothing) — it's storage (~80 ZB/yr) "
    "and verification-completeness. Transparency logs already moved to tiled, witnessed "
    "checkpoints (Rekor v2 GA 2025). A 2026 paper (Governance-Aware Agent Telemetry) independently "
    "proposes lightweight streams + selective deep logging on policy breach.",
    '"Sign every action and keep the chain" collapses into "commit every action (cheap Merkle '
    'checkpoint), prove the challenged 0.1% on demand." OTel + tail-sampling covers 99% of '
    'investigations — so "we sign everything" loses to "we sign what matters and can prove the '
    'rest."',
    "The gateway hash-chain is the right primitive, wrong unit of accounting. Become the "
    "cryptographic-completeness layer the sampler ESCALATES into — the complement to telemetry, "
    "not its competitor.",
)
t = sources(
    c,
    t + 2,
    [
        (
            "a",
            "Lagrange DeepProve-1 (2025-08-18); Nova/HyperNova folding (CRYPTO'24, IEEE S&P'25); IETF draft-ietf-scitt-architecture-22.",
        ),
        (
            "b",
            "transparency.dev tile-based logs; Sigstore Rekor v2 GA (2025); Governance-Aware Agent Telemetry, arXiv 2604.05119 (Apr 2026); OpenTelemetry GenAI agent-observability (2025).",
        ),
    ],
)

# ── PAGE 4 — VECTORS: THE 'WHERE' ────────────────────────────────────────
newpage(c, "Frontier vectors · the 'where' it lands")
t = h1(c, 54, "Where the demand concentrates")
t = vector(
    c,
    t,
    "3 · Trust topology — fragmented identity, consolidated evidence schema",
    "Identity is fragmenting on purpose (SPIFFE/WIMSE internal, DID/VC at boundaries). Research "
    "protocols for recursive delegation (AIP, Mar 2026) independently reach for *RFC 8785 "
    "canonical serialization + chained signatures* — the exact primitive AI Identity merged into "
    "OCSF (#1662). Linux Foundation now governs MCP + A2A; identity/accountability is the named "
    "unsolved gap.",
    "Protocols consolidate; identity stays fragmented through 2030. What consolidates one layer "
    "down is the tamper-evident, offline-verifiable DELEGATION LINEAGE record — the schema all the "
    "fragments must emit accountability in. OCSF is the only candidate already serving as the "
    "security industry's shared schema.",
    "Don't be the identity provider (SPIFFE/DID eat that). Make hash-chained, canonically-"
    "serialized delegation lineage MANDATORY — not optional — in OCSF, so every consumer inherits "
    "verifiable (not merely referential) lineage for free.",
)
t = vector(
    c,
    t,
    "4 · The agent economy — disputes, not payments, are the moat",
    "AP2 (Google, Sept 2025), ACP (OpenAI/Stripe), x402 (Coinbase→Linux Foundation), and Visa/MC "
    "agentic tokens each re-invented the signed, scoped, revocable mandate — bound to their own "
    'rail. CFPB\'s Jan 2026 advisory makes "appropriately scoped mandate" the legal hinge of '
    "consumer recourse. Agent-txn disputes run ~2.4x human rates.",
    "Payments commoditize into 4+ rails. The scarce, regulated, neutral layer is the rail-neutral "
    '"produce the signed mandate + action chain" dispute-evidence record + a cross-rail '
    "revocation/status registry (an OCSP/CT-log for delegation grants).",
    "The H2 Mandate Service must not be a 5th mandate format — it must be the rail-neutral notary "
    "that normalizes all of them into one non-repudiable evidence object. Disputes are where "
    "liability, regulation, and money collide.",
)
t = sources(
    c,
    t + 2,
    [
        (
            "c",
            "AIP, arXiv 2603.24775 (Mar 2026); RFC 8693 token exchange + scope attenuation (Okta/CSA 2026); Linux Foundation Agentic AI Foundation (Dec 2025); OCSF #1662 (merged 2026-06-09).",
        ),
        (
            "d",
            "Google AP2 (2025-09-16); OpenAI/Stripe ACP (2025-09-29); Coinbase x402 / x402 Foundation; CFPB agentic-commerce advisory (Jan 2026); Center for Data Innovation dispute-rate (Mar 2026).",
        ),
    ],
)

# ── PAGE 5 — THE 'WHY IT PAYS' ───────────────────────────────────────────
newpage(c, "Frontier vector · the liability inversion")
t = h1(c, 54, "Why evidence — not statute — decides who pays")
t = vector(
    c,
    t,
    "5 · AI forensics becomes an evidentiary, court-tested discipline",
    "The EU AI Liability Directive was WITHDRAWN (Feb 2025, confirmed Oct 2025) — so there is no "
    "statutory presumption of causality. Proposed US Federal Rule of Evidence 707 (comment closed "
    "Feb 2026) puts machine-generated evidence under Daubert reliability tests. C2PA is now ISO/IEC "
    "22144; EU AI Act Art. 50 mandates content-provenance marking from Aug 2026. NVIDIA Hopper "
    "confidential compute runs attested inference at <7% overhead.",
    "Without a statutory presumption, EU and US disputes become RECORDS CONTESTS: whoever holds "
    "the better tamper-evident record wins or shifts liability. Audit trails flip from compliance "
    "cost to litigation asset + insurance-pricing input. By ~2028, insurers price agent "
    "deployments on auditability posture, the way they price MFA today. TEE attestation moves from "
    "privacy feature to chain-of-custody primitive.",
    "Design the spec to satisfy FRE 702/Daubert + ISO 27037 *on its face* (version pinning, "
    "trusted timestamps, documented hash-chain validation, a readable reliability statement), and "
    "carry an OPTIONAL TEE-attestation quote + decision-provenance (model/weights/prompt hash, "
    "C2PA-aligned). The buyer becomes the insurer and the GC — not just the security team.",
)
t += 2
t = callout(
    c,
    t,
    "The deepest, least-contested ground: decision provenance",
    "Everyone is racing to log *actions*. Almost nobody binds *the reasons* — model hash, weight "
    "commitment, prompt/context — into the same tamper-evident record. Proving *why* an agent "
    "acted, aligned to C2PA's manifest model rather than a rival standard, is the deepest moat and "
    "the emptiest slot. OCSF carries the event; the spec carries the signed reason.",
    accent=AMBER,
    bg=HexColor("#FBF4E6"),
)
t = sources(
    c,
    t + 2,
    [
        (
            "e",
            "EU AI Liability Directive withdrawal (IAPP / Bird & Bird, 2025); proposed FRE 707 (Judicial Conference, comment closed 2026-02-16); C2PA 2.4 / ISO-IEC 22144; EU AI Act Art. 50 (Aug 2026).",
        ),
        (
            "f",
            "NVIDIA Hopper Confidential Computing <7% overhead (2025); SPIRE + Confidential Containers (Red Hat, Jan 2026); Raine v. OpenAI (2025); Berkeley Tech Law Journal, multi-agent liability (2026).",
        ),
    ],
)

# ── PAGE 6 — THE CONVERGENCE ─────────────────────────────────────────────
newpage(c, "The convergence · five lanes, one architecture")
t = h1(c, 54, "Five independent scans pointed at the same thing")
t = para(
    c,
    LEFT,
    t,
    "Each frontier vector was researched in isolation. They converged — and that independent "
    "agreement is the strongest signal in this report. Every lane arrived at the same successor "
    "architecture:",
    REG,
    10.5,
    INK,
    leading=14.5,
)
t += 8
# the convergence diagram — a center box with feeders
cx, cyt = LEFT, t
feeders = [
    'Crypto-beyond-PQC → "own the receipt, not the algorithm"',
    'Scale architecture → "commit everything, prove on demand"',
    'Trust topology → "the lineage record is what survives fragmentation"',
    'Agent economy → "the rail-neutral dispute-evidence object"',
    'Forensics/liability → "the court-and-insurer-citable evidence envelope"',
]
for i, f in enumerate(feeders):
    yy = cyt + i * 17
    c.setFillColor(SIGNAL_AC)
    c.circle(LEFT + 4, PAGE_H - yy - 6, 3, fill=1, stroke=0)
    text(c, LEFT + 14, yy, f, REG, 9.5, INK)
t = cyt + len(feeders) * 17 + 6
t = callout(
    c,
    t,
    "The convergent architecture",
    "A transparency-log substrate (commit every action cheaply to a tiled, witnessed, append-only "
    "log) decoupled from a pluggable EVIDENCE OBJECT proved on demand — binding {signed action + "
    "hash-chained delegation lineage + optional TEE-attestation quote + optional ZK policy proof + "
    "decision provenance} into one record that is rail-neutral, identity-provider-agnostic, "
    "quantum-durable, recursively aggregatable, and admissible. Today nobody owns this object.",
    accent=PURPLE_DEEP,
)
t = para(c, LEFT, t, "Three non-obvious inversions worth internalizing:", BOLD, 10, INK, leading=14)
t = bullet(
    c,
    LEFT,
    t,
    '"Lighter regulation" (the AILD withdrawal) makes evidence MORE valuable, '
    "not less — records, not statutes, now allocate liability. The opposite of the common read.",
)
t = bullet(
    c,
    LEFT,
    t,
    "The industry over-invests in prevention; at scale, the differentiated value "
    'flips to "prove and unwind," not "stop it." Countercyclical to where 2026 dollars flow.',
)
t = bullet(
    c,
    LEFT,
    t,
    "A research delegation protocol (AIP) independently re-derived our exact "
    "merged primitive (RFC 8785 canonical serialization + chained signatures). We're not early — "
    "we're *on the line the frontier is converging toward*, with a head start.",
)

# ── PAGE 7 — THE BET ─────────────────────────────────────────────────────
newpage(c, "The bet to seed now · and what not to bet on")
t = h1(c, 54, "The asymmetric bet")
t = callout(
    c,
    t,
    'Seed the "Agent Evidence Record"',
    "A canonical, standards-anchored, commit-and-prove evidence substrate: the gateway emits every "
    "action into a tiled, witnessed transparency log; each entry is a SCITT-aligned receipt "
    "carrying the pluggable evidence object (signature + hash-chained delegation lineage + optional "
    "attestation quote + optional ZK policy proof + decision provenance). Land its schema in OCSF "
    "(the live seat), float it to SCITT / C2PA / the NIST agent initiative. Design it to satisfy "
    "Daubert + ISO 27037 on its face. Be the Switzerland of agent-delegation evidence.",
    accent=PURPLE_DEEP,
)
t = para(c, LEFT, t, "Why it's asymmetric:", BOLD, 10, INK, leading=14)
t = bullet(
    c,
    LEFT,
    t,
    "Cheap to seed (a superset of today's product — nothing breaks), defensible "
    "on legal-engineering + standards adoption (not clonable code), and it compounds the OCSF/"
    "Mandate-Service positions already built.",
)
t = bullet(
    c,
    LEFT,
    t,
    "Near-zero current occupancy: everyone competes on logging, identity, and "
    "rails; the evidence *format* + the commit-and-prove substrate are unclaimed and standards-"
    "adjacent — a registry/format position with winner-take-most dynamics.",
)
t = bullet(
    c,
    LEFT,
    t,
    "Neutrality is the moat a small player CAN hold and Visa/Google can't (they "
    "are conflicted rails) — which is exactly why the standards work is load-bearing, not a side "
    "quest.",
)
t += 4
t = callout(
    c,
    t,
    "What we are deliberately NOT betting on",
    "Don't be the identity provider (SPIFFE/DID/Okta eat it). Don't be the payment rail "
    "(Visa/Stripe/Coinbase eat it). Don't build a reputation engine (Sybil-fragile, unsolved — be "
    "the evidence it cites). Don't race zkML-of-full-LLMs (capital-intensive vs. Lagrange/Succinct; "
    'prove narrow policy predicates instead). Don\'t market "low-overhead signing" (true but '
    "irrelevant — signing is the cheapest thing). Treat PQ-aggregate signatures and verifiable-FHE "
    "as research bets to track, not roadmap.",
    accent=AMBER,
    bg=HexColor("#FBF4E6"),
)

# ── PAGE 8 — THE EXPERIMENTS ─────────────────────────────────────────────
newpage(c, "The cheapest tests · weeks, not quarters")
t = h1(c, 54, "How to find out cheaply if we're right")
t = para(
    c,
    LEFT,
    t,
    "Five lanes proposed near-identical week-scale experiments. They compound into one demo no "
    '"we hash-chain your logs" competitor can match — and each doubles as OCSF/SCITT standards '
    "positioning.",
    REG,
    10.5,
    INK,
    leading=14.5,
)
t += 6


def step(c, top, n, title, body):
    c.setFillColor(PURPLE_DEEP)
    c.circle(LEFT + 9, PAGE_H - top - 7, 9, fill=1, stroke=0)
    text(c, LEFT + 9, top + 1.5, str(n), BOLD, 10, WHITE, align="c")
    text(c, LEFT + 26, top, title, BOLD, 10, INK)
    top = para(c, LEFT + 26, top + 13, body, REG, 9.5, INK, leading=12.5, max_w=CONTENT_W - 26)
    return top + 9


t = step(
    c,
    t,
    1,
    "Stand up the transparency substrate",
    "Add to the existing gateway hash-chain: every N actions, compute a Merkle root and publish a "
    "signed checkpoint to a tiled append-only log (Trillian / Go-sumdb-style / even static tiles "
    "in S3). Build the inclusion-proof verifier — prove any one historical action in O(log N) "
    "without replaying the chain. Measure bytes-to-verify and retention vs. today.",
)
t = step(
    c,
    t,
    2,
    "Wrap entries as SCITT receipts",
    "Mint a transparency receipt per entry; validate the structure against "
    "draft-ietf-scitt-architecture. Mostly integration — days, not weeks.",
)
t = step(
    c,
    t,
    3,
    "Prove interop with the offline CLI",
    "Use the existing verify-CLI to verify a THIRD PARTY's OCSF delegation chain offline, with "
    "zero shared tooling. If someone else's chain verifies in our CLI, the substrate-interop "
    "thesis is proven — and it becomes the conformance test you hand the OCSF WG.",
)
t = step(
    c,
    t,
    4,
    "Run the adversarial admissibility review",
    "Write a 2-page Daubert/702 reliability statement for the trail; put it to 2–3 e-discovery "
    "attorneys + one cyber-insurance underwriter. One question: would this survive a challenge / "
    "lower a premium, and what single field is missing? Their answer is your required schema, free.",
)
t = step(
    c,
    t,
    5,
    "Normalize one cross-rail mandate",
    "Emit a Delegation Evidence Record that ingests one AP2 Cart Mandate (W3C VC) + one ACP Shared "
    "Payment Token into one schema; map it to an OCSF object. Validate the pull with one PSP/"
    "acquirer and one enterprise GC.",
)
t += 2
t = callout(
    c,
    t,
    "The read",
    "If steps 1–3 work in days (they will — mostly integration) and steps 4–5 draw a \"yes, we'd "
    'retain and query this," the 2030 thesis is validated before a meaningful line of new product '
    "code. If they shrug, the moat was the payment after all — and you've learned it for an "
    "engineer-week, not a funding round.",
    accent=GREEN,
    bg=HexColor("#EAF5EF"),
)

c.showPage()
c.save()
print(f"wrote {OUT}  ({OUT.stat().st_size:,} bytes, {_pg[0]} pages)")
