"""Render the Anthropic 3-tier posture-map brief as an AI Identity Purple executive PDF.

Board item #416 (Sprint 16). Content source of record:
docs/strategy/anthropic-3-tier-posture-mapping.md
"""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ── AI Identity Purple palette ──────────────────────────────────────────────
DEEP = colors.HexColor("#4B2D7F")
LIGHT = colors.HexColor("#6B4FA0")
LAVENDER = colors.HexColor("#F0E8F8")
INK = colors.HexColor("#2A2A33")
GRAY = colors.HexColor("#6B6B78")
WHITE = colors.white

OUT = "marketing/sales/ai-identity-anthropic-tier-posture-2026-06-23.pdf"
DOCNAME = "Agent-Security Posture Map"
DATE = "June 23, 2026"

styles = getSampleStyleSheet()


def mkstyle(name, **kw):
    base = kw.pop("parent", styles["Normal"])
    return ParagraphStyle(name, parent=base, **kw)


body = mkstyle(
    "body", fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=INK, spaceAfter=6
)
eyebrow = mkstyle("eyebrow", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=LIGHT)
h1 = mkstyle("h1", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=DEEP, spaceAfter=4)
h2 = mkstyle(
    "h2",
    fontName="Helvetica-Bold",
    fontSize=11.5,
    leading=15,
    textColor=DEEP,
    spaceBefore=10,
    spaceAfter=3,
)
thesis = mkstyle(
    "thesis", fontName="Helvetica-BoldOblique", fontSize=11, leading=16, textColor=DEEP
)
callout = mkstyle("callout", fontName="Helvetica", fontSize=9, leading=12.5, textColor=INK)
note = mkstyle("note", fontName="Helvetica", fontSize=8.5, leading=12, textColor=INK, spaceAfter=3)
cell = mkstyle("cell", fontName="Helvetica", fontSize=8.3, leading=10.8, textColor=INK)
cellb = mkstyle("cellb", parent=cell, fontName="Helvetica-Bold", textColor=DEEP)
cellh = mkstyle("cellh", fontName="Helvetica-Bold", fontSize=8.3, leading=10.8, textColor=WHITE)
cover_title = mkstyle("ct", fontName="Helvetica-Bold", fontSize=27, leading=31, textColor=WHITE)
cover_sub = mkstyle(
    "cs", fontName="Helvetica", fontSize=13, leading=18, textColor=colors.HexColor("#D9CCEC")
)
cover_meta = mkstyle(
    "cm", fontName="Helvetica", fontSize=10, leading=15, textColor=colors.HexColor("#D9CCEC")
)


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LAVENDER)
    canvas.setLineWidth(0.6)
    canvas.line(0.75 * inch, 0.62 * inch, letter[0] - 0.75 * inch, 0.62 * inch)
    canvas.setFont("Helvetica", 7.3)
    canvas.setFillColor(GRAY)
    canvas.drawString(0.75 * inch, 0.46 * inch, f"AI Identity  ·  {DOCNAME}  ·  {DATE}")
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.46 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _body_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DEEP)
    canvas.rect(0, letter[1] - 7, letter[0], 7, stroke=0, fill=1)  # top edge bar
    canvas.restoreState()
    _footer(canvas, doc)


def _cover_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DEEP)
    canvas.rect(0, 0, letter[0], letter[1], stroke=0, fill=1)
    canvas.setFillColor(LIGHT)
    canvas.rect(0, 0, 14, letter[1], stroke=0, fill=1)  # left accent bar
    canvas.restoreState()


def tbl(data, col_widths, header=True):
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#DAD0EC")),
    ]
    if header:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), DEEP),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LAVENDER]),
        ]
    t.setStyle(TableStyle(cmds))
    return t


def cellp(text, style=cell):
    return Paragraph(text, style)


story = []

# ── Cover ───────────────────────────────────────────────────────────────────
story += [
    NextPageTemplate("body"),
    Spacer(1, 2.4 * inch),
    Paragraph(
        "POSITIONING  ·  AGENT-SECURITY POSTURE",
        mkstyle("ce", parent=eyebrow, textColor=colors.HexColor("#C9B6E8")),
    ),
    Spacer(1, 10),
    Paragraph("Where AI Identity Sits in<br/>Anthropic's Agent-Security Model", cover_title),
    Spacer(1, 14),
    Paragraph(
        "An honest posture map across the zero-trust tiers — and the layer above them that is ours alone.",
        cover_sub,
    ),
    Spacer(1, 0.7 * inch),
    Paragraph(
        "Prepared for &nbsp;·&nbsp; AI Identity leadership / partner conversations", cover_meta
    ),
    Paragraph(f"Date &nbsp;·&nbsp; {DATE}", cover_meta),
    Paragraph("Basis &nbsp;·&nbsp; Insight #101 · briefing #215 · Sprint 16 item #416", cover_meta),
    PageBreak(),
]

# ── Page 2: thesis + model + posture map ─────────────────────────────────────
story += [
    Paragraph("POSTURE MAP  ·  ANTHROPIC ZERO-TRUST TIERS", eyebrow),
    Spacer(1, 3),
    Paragraph("The bar is rising on credentials. We sit above it.", h1),
    Spacer(1, 6),
]

thesis_tbl = Table(
    [
        [
            Paragraph(
                "Anthropic is raising the bar on agent <i>credentials</i>. AI Identity already operates at the "
                "layer <i>above</i> — the portable record of authority and action — and has now closed the one "
                "credential gap that mattered.",
                thesis,
            )
        ]
    ],
    colWidths=[7.0 * inch],
)
thesis_tbl.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, -1), LAVENDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LINEBEFORE", (0, 0), (0, -1), 3, DEEP),
        ]
    )
)
story += [thesis_tbl, Spacer(1, 10)]

story += [
    Paragraph("The model (our synthesis — not an Anthropic-branded framework)", h2),
    Paragraph(
        "Anthropic publishes zero-trust <i>principles</i>, not a numbered tier ladder. We synthesize them "
        "into a 3-tier maturity model to map ourselves honestly. Their published controls (Claude Code "
        "security docs): &ldquo;multiple short-lived, narrowly scoped credentials &hellip; expiring "
        "independently&rdquo;; <b>fail-closed</b> defaults; least-privilege permissioning.",
        body,
    ),
]

model_rows = [
    [cellp("Tier", cellh), cellp("What it requires", cellh), cellp("Source basis", cellh)],
    [
        cellp("Tier 1<br/>Identity hygiene", cellb),
        cellp(
            "Unique cryptographic identity per agent; short-lived, narrowly-scoped credentials; deny-by-default. <i>Static API keys unsuitable even here.</i>"
        ),
        cellp("Claude Code security docs"),
    ],
    [
        cellp("Tier 2<br/>Transport &amp; key custody", cellb),
        cellp(
            "Mutual TLS; keys held in hardware (HSM/TPM); credentials issued via federation (WIF/OIDC), not stored secrets."
        ),
        cellp("Anthropic Workload Identity Federation"),
    ],
    [
        cellp("Tier 3<br/>Hardware attestation", cellb),
        cellp(
            "Remote attestation of the agent runtime (TPM/enclave/confidential compute); signing identity bound to attested hardware."
        ),
        cellp("Anthropic confidential inference (TPM root)"),
    ],
]
story += [Spacer(1, 4), tbl(model_rows, [1.35 * inch, 3.95 * inch, 1.7 * inch]), Spacer(1, 12)]

story += [Paragraph("AI Identity posture (honest current state)", h2)]
posture_rows = [
    [cellp("Tier", cellh), cellp("AI Identity status", cellh), cellp("Evidence", cellh)],
    [
        cellp("Tier 1", cellb),
        cellp("<b>Largely met &mdash; just advanced.</b>"),
        cellp(
            "Per-agent <font face='Courier'>aid_sk_</font> identity; runtime keys now <b>expire by default</b> + refresh flow (PR #349, in review); gateway <b>fail-closed</b>."
        ),
    ],
    [
        cellp("Tier 2", cellb),
        cellp("<b>Partial &mdash; our <i>root</i> is Tier-2-grade.</b>"),
        cellp(
            "Signing root is <b>Cloud KMS / HSM-backed</b> (ECDSA P-256, JWKS published). Federated issuance for customer agent creds is roadmap (#414); mTLS not yet."
        ),
    ],
    [
        cellp("Tier 3", cellb),
        cellp("<b>Roadmap.</b>"),
        cellp(
            "Consume + record TPM/enclave/mTLS attestation at registration, bound into the OCSF evidence chain (#415)."
        ),
    ],
]
story += [Spacer(1, 4), tbl(posture_rows, [0.9 * inch, 2.1 * inch, 4.0 * inch]), PageBreak()]

# ── Page 3: above the tiers + pre-empt + roadmap + reviewer note ─────────────
story += [
    Paragraph("DIFFERENTIATION  ·  THE LAYER ABOVE", eyebrow),
    Spacer(1, 3),
    Paragraph("What the tiers don't cover is exactly our product.", h1),
    Spacer(1, 6),
    Paragraph("Above the tiers — the part Anthropic doesn't occupy", h2),
    Paragraph(
        "Tiers 1&ndash;3 secure <i>how an agent authenticates</i>. AI Identity adds the layer above: a "
        "<b>portable, cross-vendor, offline-verifiable record of what authority an agent held and what it "
        "did</b> &mdash; OCSF-native audit events plus DSSE/ECDSA-signed evidence a third party can verify "
        "with <b>only our published public key</b> (no shared secret). Hardware attestation makes this "
        "layer <i>more</i> valuable: recorded properly, we become the record layer <b>on top of</b> "
        "hardware roots &mdash; feeding the OCSF workload-attestation gap we are co-authoring with IBM.",
        body,
    ),
]

preempt = Table(
    [
        [
            Paragraph(
                "<b>&ldquo;Are you obsolete?&rdquo; &mdash; No.</b> Hardware-bound credentials are a "
                "<b>complementary lower layer, not a competitor</b>. They raise demand for a portable record that "
                "can <i>incorporate</i> attestations &mdash; precisely our layer. The one genuine catch-up &mdash; "
                "the static agent key Anthropic calls unsuitable at Tier 1 &mdash; is <b>closed</b> (PR #349). Our "
                "signing root is already HSM-backed. We are not behind the trend; we sit on top of it.",
                callout,
            )
        ]
    ],
    colWidths=[7.0 * inch],
)
preempt.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, -1), LAVENDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("LINEBEFORE", (0, 0), (0, -1), 3, DEEP),
        ]
    )
)
story += [Spacer(1, 6), preempt, Spacer(1, 10)]

story += [Paragraph("Roadmap (Sprint 16 board items)", h2)]
road_rows = [
    [
        cellp("#413", cellb),
        cellp("Short-lived runtime tokens by default &mdash; <b>DONE</b>, PR #349 (in review)."),
    ],
    [
        cellp("#414", cellb),
        cellp("OIDC / Workload Identity Federation for customer agent credentials (Tier 2)."),
    ],
    [
        cellp("#415", cellb),
        cellp(
            "Consume + record hardware attestation (Tier 3) &mdash; the moat / OCSF workload-attestation gap."
        ),
    ],
    [cellp("#416", cellb), cellp("This posture map (positioning).")],
]
story += [Spacer(1, 3), tbl(road_rows, [0.8 * inch, 6.2 * inch], header=False), Spacer(1, 12)]

story += [Paragraph("What to watch for (reviewer's note)", h2)]
for w in [
    "The <b>&ldquo;3 tiers&rdquo; are our synthesis</b>, not an Anthropic-labeled framework. Principles are sourced; verify against Anthropic's primary docs before external/customer use.",
    "Tier 1 <b>&ldquo;largely met&rdquo; is contingent</b> on PR #349 merging and deploying. Until then say &ldquo;in review,&rdquo; not &ldquo;shipped.&rdquo;",
    "Tier 2 <b>&ldquo;HSM-backed&rdquo; refers to our signing/attestation root</b>, not customer agent-credential custody (still classical, hashed-at-rest).",
    "<b>mTLS-for-agent-creds and WIF are roadmap, not shipped</b> &mdash; don't imply otherwise.",
    "The <b>&ldquo;Anthropic doesn't occupy the record layer&rdquo; claim is our assessment</b> as of 2026-06; revisit if they ship a provenance/attestation-record product.",
]:
    story.append(Paragraph(f"&bull;&nbsp;&nbsp;{w}", note))

story += [
    Spacer(1, 8),
    Paragraph("Sources", h2),
    Paragraph(
        "Anthropic &mdash; Claude Code Security (short-lived/scoped/expiring credentials; fail-closed; "
        "least privilege): <font color='#4B2D7F'>code.claude.com/docs/en/security</font> &nbsp;·&nbsp; "
        "Anthropic Workload Identity Federation for the Claude API &nbsp;·&nbsp; Anthropic confidential "
        "inference / TPM root of trust &nbsp;·&nbsp; Internal: Insight #101, briefing #215, PR #349.",
        mkstyle("src", parent=note, textColor=GRAY),
    ),
]

# ── Build ────────────────────────────────────────────────────────────────────
doc = BaseDocTemplate(
    OUT,
    pagesize=letter,
    leftMargin=0.75 * inch,
    rightMargin=0.75 * inch,
    topMargin=0.7 * inch,
    bottomMargin=0.8 * inch,
    title="AI Identity — Anthropic Agent-Security Posture Map",
    author="AI Identity",
)
cover_frame = Frame(
    0.95 * inch, 0.8 * inch, letter[0] - 1.7 * inch, letter[1] - 1.6 * inch, id="cover"
)
body_frame = Frame(
    0.75 * inch, 0.8 * inch, letter[0] - 1.5 * inch, letter[1] - 1.6 * inch, id="body"
)
from reportlab.platypus import PageTemplate  # noqa: E402

doc.addPageTemplates(
    [
        PageTemplate(id="cover", frames=[cover_frame], onPage=_cover_page),
        PageTemplate(id="body", frames=[body_frame], onPage=_body_page),
    ]
)
doc.build(story)
print("wrote", OUT)
