"""Build a shareable pricing sheet PDF for prospective early partners.

Single-document, six-page US-Letter PDF. Brand-aligned with the briefing
deck (navy + amber, sans-serif). Includes:

  1. Cover + tier overview
  2. Detailed tier comparison (Free / Pro / Business / Business+ / Enterprise)
  3. Enterprise tier deep-dive (Multi-Tenant vs Dedicated VPC)
  4. Founding-partner terms (90 days free + 24-month rate lock + perks)
  5. Pricing trajectory & trigger condition for the planned price-up
  6. How to engage

Run: python3 build_pricing_sheet.py
Output: ../pricing-sheet-2026-04-27.pdf
"""

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

# ── Theme ────────────────────────────────────────────────────────────────

NAVY = colors.HexColor("#0B1933")
INK = colors.HexColor("#1A1F36")
GREY = colors.HexColor("#6B7280")
LIGHT_GREY = colors.HexColor("#9CA3AF")
LIGHT_BG = colors.HexColor("#F5F7FA")
LINE = colors.HexColor("#E2E5EB")
WHITE = colors.HexColor("#FFFFFF")

AMBER = colors.HexColor("#E09F3E")
GREEN = colors.HexColor("#36A16B")
RED = colors.HexColor("#E54B4B")
BLUE = colors.HexColor("#4F8FE5")
INDIGO = colors.HexColor("#6F6FE6")
PURPLE = colors.HexColor("#8E6FE6")

PAGE_W, PAGE_H = LETTER
MARGIN = 0.6 * inch

OUT = Path(__file__).resolve().parent.parent / "pricing-sheet-2026-04-27.pdf"


# ── Helpers ──────────────────────────────────────────────────────────────


def draw_header(c: canvas.Canvas, page_num: int, total: int, title: str):
    """Top header bar — wordmark left, page indicator right, title under."""
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN, PAGE_H - 0.5 * inch, "AI IDENTITY")
    c.setFont("Helvetica", 9)
    c.setFillColor(GREY)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.5 * inch, f"Page {page_num} / {total}")
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.line(MARGIN, PAGE_H - 0.65 * inch, PAGE_W - MARGIN, PAGE_H - 0.65 * inch)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(MARGIN, PAGE_H - 1.05 * inch, title)


def draw_footer(c: canvas.Canvas):
    c.setFillColor(GREY)
    c.setFont("Helvetica", 8)
    c.drawString(
        MARGIN,
        0.45 * inch,
        f"AI Identity · Pricing & Terms · {date.today().strftime('%B %d, %Y')}",
    )
    c.drawRightString(
        PAGE_W - MARGIN,
        0.45 * inch,
        "Confidential — for prospective partners",
    )


def text_block(c: canvas.Canvas, x, y, w, h, *, text, size=10, color=INK, bold=False, leading=None):
    """Wrap and draw text in a box. Returns y after drawing."""
    font = "Helvetica-Bold" if bold else "Helvetica"
    leading = leading or size * 1.35
    c.setFillColor(color)
    c.setFont(font, size)
    # Manual wrap
    words = text.split()
    line = ""
    cur_y = y
    for w_word in words:
        test = (line + " " + w_word).strip()
        if c.stringWidth(test, font, size) > w:
            c.drawString(x, cur_y, line)
            cur_y -= leading
            line = w_word
            if cur_y < 0:
                break
        else:
            line = test
    if line:
        c.drawString(x, cur_y, line)
        cur_y -= leading
    return cur_y


def kv_pair(
    c, x, y, label, value, *, label_color=GREY, value_color=NAVY, label_size=8, value_size=12
):
    c.setFillColor(label_color)
    c.setFont("Helvetica-Bold", label_size)
    c.drawString(x, y, label.upper())
    c.setFillColor(value_color)
    c.setFont("Helvetica-Bold", value_size)
    c.drawString(x, y - 0.22 * inch, value)


def card(c, x, y, w, h, *, accent, title, body_lines, body_size=9):
    """Light card with colored left bar."""
    c.setFillColor(LIGHT_BG)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, fill=1, stroke=1)
    c.setFillColor(accent)
    c.rect(x, y, 0.05 * inch, h, fill=1, stroke=0)
    # Title
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x + 0.15 * inch, y + h - 0.25 * inch, title)
    # Body
    body_y = y + h - 0.5 * inch
    for line in body_lines:
        c.setFillColor(INK)
        c.setFont("Helvetica", body_size)
        # naive wrap inside card
        max_w = w - 0.3 * inch
        chunks = []
        current = ""
        for word in line.split():
            test = (current + " " + word).strip()
            if c.stringWidth(test, "Helvetica", body_size) > max_w:
                chunks.append(current)
                current = word
            else:
                current = test
        if current:
            chunks.append(current)
        for chunk in chunks:
            if body_y < y + 0.15 * inch:
                break
            c.drawString(x + 0.15 * inch, body_y, chunk)
            body_y -= body_size * 1.3


# ── Build ────────────────────────────────────────────────────────────────


c = canvas.Canvas(str(OUT), pagesize=LETTER)
c.setTitle("AI Identity — Pricing & Terms")
c.setAuthor("AI Identity")
c.setSubject("Pricing structure and timetable for prospective early partners")

TOTAL = 6


# ── Page 1: Cover + tier overview ────────────────────────────────────────

# Hero band
c.setFillColor(NAVY)
c.rect(0, PAGE_H - 3.4 * inch, PAGE_W, 3.4 * inch, fill=1, stroke=0)
# Amber accent bar
c.setFillColor(AMBER)
c.rect(MARGIN, PAGE_H - 2.3 * inch, 0.18 * inch, 1.4 * inch, fill=1, stroke=0)
c.setFillColor(WHITE)
c.setFont("Helvetica-Bold", 12)
c.drawString(MARGIN + 0.4 * inch, PAGE_H - 1.1 * inch, "AI IDENTITY")
c.setFont("Helvetica-Bold", 36)
c.drawString(MARGIN + 0.4 * inch, PAGE_H - 1.85 * inch, "Pricing & Terms")
c.setFont("Helvetica", 13)
c.setFillColor(colors.HexColor("#C9D4E6"))
c.drawString(
    MARGIN + 0.4 * inch,
    PAGE_H - 2.2 * inch,
    "Cryptographic identity, policy, and audit for AI agents.",
)
c.setFont("Helvetica", 11)
c.setFillColor(colors.HexColor("#9DA9C1"))
c.drawString(
    MARGIN + 0.4 * inch,
    PAGE_H - 2.85 * inch,
    f"Prepared for prospective early partners  ·  {date.today().strftime('%B %d, %Y')}",
)
c.drawString(
    MARGIN + 0.4 * inch,
    PAGE_H - 3.1 * inch,
    "Jeff Leva  ·  Founder & CEO  ·  jeff@ai-identity.co  ·  ai-identity.co",
)

# Below hero — tier overview cards in a strip
y_top = PAGE_H - 4.0 * inch
c.setFillColor(NAVY)
c.setFont("Helvetica-Bold", 14)
c.drawString(MARGIN, y_top, "Five tiers, transparent pricing")
c.setFillColor(GREY)
c.setFont("Helvetica", 10)
c.drawString(
    MARGIN,
    y_top - 0.22 * inch,
    "Every plan includes the tamper-proof audit chain and deny-by-default gateway.",
)

tiers = [
    ("Free", "$0", "5 agents", "2K req/mo", "Prototyping", colors.HexColor("#9CA3AF")),
    ("Pro", "$79", "50 agents", "75K req/mo", "Production-shipping teams", BLUE),
    ("Business", "$299", "200 agents", "500K req/mo", "Scaling teams, advanced needs", BLUE),
    ("Business+", "$599", "500 agents", "1.5M req/mo", "High-volume teams pre-Enterprise", INDIGO),
    ("Enterprise", "$1,500+", "Unlimited", "Unlimited", "Compliance-sensitive deployments", PURPLE),
]
card_y = y_top - 3.4 * inch
card_h = 2.95 * inch
card_w = (PAGE_W - 2 * MARGIN - 0.4 * inch) / 5
for i, (name, price, agents, reqs, note, color) in enumerate(tiers):
    x = MARGIN + i * (card_w + 0.1 * inch)
    c.setFillColor(LIGHT_BG)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.rect(x, card_y, card_w, card_h, fill=1, stroke=1)
    c.setFillColor(color)
    c.rect(x, card_y + card_h - 0.08 * inch, card_w, 0.08 * inch, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x + 0.15 * inch, card_y + card_h - 0.4 * inch, name)
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(NAVY)
    c.drawString(x + 0.15 * inch, card_y + card_h - 0.85 * inch, price)
    c.setFont("Helvetica", 8)
    c.setFillColor(GREY)
    c.drawString(
        x + 0.15 * inch, card_y + card_h - 1.05 * inch, "/ month" if name != "Free" else ""
    )
    c.setFont("Helvetica", 9)
    c.setFillColor(INK)
    c.drawString(x + 0.15 * inch, card_y + card_h - 1.4 * inch, agents)
    c.drawString(x + 0.15 * inch, card_y + card_h - 1.6 * inch, reqs)
    c.setFillColor(GREY)
    c.setFont("Helvetica", 8)
    text_block(
        c,
        x + 0.15 * inch,
        card_y + card_h - 1.95 * inch,
        card_w - 0.3 * inch,
        1.0 * inch,
        text=note,
        size=8,
        color=GREY,
    )

# Note below
note_y = card_y - 0.3 * inch
text_block(
    c,
    MARGIN,
    note_y,
    PAGE_W - 2 * MARGIN,
    0.4 * inch,
    text="Annual billing available on Pro, Business, and Business+ at ~15% discount. "
    "Enterprise is billed monthly with a 24-month rate lock for founding-cohort partners. "
    "See pages 3-5 for Enterprise detail and founding-partner terms.",
    size=9,
    color=GREY,
)

draw_footer(c)
c.showPage()


# ── Page 2: Detailed tier comparison ─────────────────────────────────────

draw_header(c, 2, TOTAL, "Detailed tier comparison")
c.setFillColor(GREY)
c.setFont("Helvetica", 10)
c.drawString(
    MARGIN,
    PAGE_H - 1.3 * inch,
    "Standard rate-card. All plans include the tamper-proof audit chain.",
)

# Build the comparison table
data = [
    ["Feature", "Free", "Pro", "Business", "Business+", "Enterprise"],
    ["Monthly", "$0", "$79", "$299", "$599", "$1,500+"],
    ["Annual (per mo)", "—", "$67", "$254", "$509", "Custom"],
    ["Agents", "5", "50", "200", "500", "Unlimited"],
    ["Requests / month", "2,000", "75,000", "500,000", "1,500,000", "Unlimited"],
    ["Team members", "1", "5", "25", "50", "Unlimited"],
    ["Upstream credentials", "1", "10", "50", "100", "Unlimited"],
    ["Audit retention", "30 d", "90 d", "1 yr", "2 yr", "Unlimited"],
    ["Tamper-proof audit chain", "✓", "✓", "✓", "✓", "✓"],
    ["Gateway policy enforcement", "—", "✓", "✓", "✓", "✓"],
    ["Key rotation (zero-downtime)", "—", "✓", "✓", "✓", "✓"],
    ["Custom policies", "—", "—", "✓", "✓", "✓"],
    ["SAML / SCIM", "—", "Basic", "✓", "✓", "Full"],
    ["Team roles & permissions", "—", "—", "✓", "✓", "✓"],
    ["Agent-level role assignments", "—", "—", "✓", "✓", "✓"],
    ["Anomaly detection", "—", "—", "—", "✓", "✓"],
    ["SLA guarantee", "—", "—", "—", "99.5%", "Custom"],
    [
        "Priority support",
        "Community",
        "Email",
        "Priority",
        "Priority +\nDedicated hrs",
        "Dedicated\n+ SLA",
    ],
    ["Compliance evidence export", "—", "—", "—", "—", "✓"],
    ["Human-in-the-loop review", "—", "—", "—", "—", "✓"],
    ["Dedicated VPC deployment", "—", "—", "—", "—", "✓"],
]
col_widths = [
    1.95 * inch,  # feature
    0.92 * inch,  # free
    0.92 * inch,  # pro
    0.92 * inch,  # business
    1.05 * inch,  # business+
    1.05 * inch,  # enterprise
]
table = Table(data, colWidths=col_widths)
ts = TableStyle(
    [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (1, 0), (-1, 0), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        # Body
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("TEXTCOLOR", (0, 1), (0, -1), NAVY),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        # Pricing rows accent
        ("BACKGROUND", (0, 1), (-1, 2), colors.HexColor("#FAFBFC")),
        ("FONTNAME", (1, 1), (-1, 2), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, 1), (-1, 2), NAVY),
        # Alternating row backgrounds
        ("ROWBACKGROUNDS", (0, 3), (-1, -1), [WHITE, LIGHT_BG]),
        # Alignment
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        # Outer border
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, LINE),
        ("LINEBELOW", (0, 2), (-1, 2), 0.75, LINE),
    ]
)
table.setStyle(ts)
table_w, table_h = table.wrap(PAGE_W - 2 * MARGIN, PAGE_H - 3 * inch)
table.drawOn(c, MARGIN, PAGE_H - 1.6 * inch - table_h)

# Footnote
text_block(
    c,
    MARGIN,
    PAGE_H - 1.7 * inch - table_h - 0.2 * inch,
    PAGE_W - 2 * MARGIN,
    0.5 * inch,
    text="Enterprise pricing splits into two delivery models, detailed on the next page. "
    "Founding-cohort partners (first 3-4 paid Enterprise customers) receive a "
    "24-month rate lock at today's published rates plus 90 days free.",
    size=9,
    color=GREY,
)

draw_footer(c)
c.showPage()


# ── Page 3: Enterprise tier deep-dive ────────────────────────────────────

draw_header(c, 3, TOTAL, "Enterprise — two delivery models")
text_block(
    c,
    MARGIN,
    PAGE_H - 1.4 * inch,
    PAGE_W - 2 * MARGIN,
    0.5 * inch,
    text="Enterprise customers choose between shared multi-tenant infrastructure and "
    "dedicated VPC isolation. Both ship with the full Enterprise feature set; "
    "the difference is deployment topology and compliance posture.",
    size=10,
    color=GREY,
)

# Two-column comparison: Multi-tenant vs VPC
col_w = (PAGE_W - 2 * MARGIN - 0.3 * inch) / 2
col1_x = MARGIN
col2_x = MARGIN + col_w + 0.3 * inch
col_y = PAGE_H - 5.6 * inch
col_h = 3.6 * inch

# Multi-tenant column
c.setFillColor(LIGHT_BG)
c.setStrokeColor(LINE)
c.rect(col1_x, col_y, col_w, col_h, fill=1, stroke=1)
c.setFillColor(PURPLE)
c.rect(col1_x, col_y + col_h - 0.1 * inch, col_w, 0.1 * inch, fill=1, stroke=0)
c.setFillColor(NAVY)
c.setFont("Helvetica-Bold", 14)
c.drawString(col1_x + 0.2 * inch, col_y + col_h - 0.45 * inch, "Enterprise — Multi-Tenant")
kv_pair(
    c,
    col1_x + 0.2 * inch,
    col_y + col_h - 0.95 * inch,
    "Monthly rate",
    "$1,500 / month",
    value_color=NAVY,
    value_size=18,
)
c.setFillColor(GREY)
c.setFont("Helvetica", 9)
c.drawString(
    col1_x + 0.2 * inch,
    col_y + col_h - 1.4 * inch,
    "$18,000 / yr  ·  24-month founding rate lock available",
)

mt_features = [
    "Unlimited agents and requests",
    "Full SSO + SAML / SCIM",
    "Compliance evidence export (SOC 2, EU AI Act, NIST)",
    "Team roles + agent-level role assignments",
    "Human-in-the-loop review",
    "Anomaly detection + 99.9% uptime SLA",
    "Dedicated support with named contact",
    "Audit log retention: unlimited",
    "Shared infrastructure (GKE Autopilot, US-East)",
]
fy = col_y + col_h - 1.75 * inch
for f in mt_features:
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col1_x + 0.2 * inch, fy, "✓")
    c.setFillColor(INK)
    c.setFont("Helvetica", 9)
    c.drawString(col1_x + 0.4 * inch, fy, f)
    fy -= 0.2 * inch

# VPC column
c.setFillColor(LIGHT_BG)
c.setStrokeColor(LINE)
c.rect(col2_x, col_y, col_w, col_h, fill=1, stroke=1)
c.setFillColor(BLUE)
c.rect(col2_x, col_y + col_h - 0.1 * inch, col_w, 0.1 * inch, fill=1, stroke=0)
c.setFillColor(NAVY)
c.setFont("Helvetica-Bold", 14)
c.drawString(col2_x + 0.2 * inch, col_y + col_h - 0.45 * inch, "Enterprise — Dedicated VPC")
kv_pair(
    c,
    col2_x + 0.2 * inch,
    col_y + col_h - 0.95 * inch,
    "Monthly rate",
    "$3,000 / month",
    value_color=NAVY,
    value_size=18,
)
c.setFillColor(GREY)
c.setFont("Helvetica", 9)
c.drawString(
    col2_x + 0.2 * inch,
    col_y + col_h - 1.4 * inch,
    "$36,000 / yr  ·  24-month founding rate lock available",
)

vpc_features = [
    "Everything in Multi-Tenant, plus:",
    "Dedicated infrastructure (isolated GKE cluster)",
    "Dedicated KMS keyring + asymmetric signing keys",
    "Optional BYOC — customer-chosen region (US, EU, APAC)",
    "Choice of region (US, EU, or APAC)",
    "Custom data-residency requirements supported",
    "Dedicated support hours + custom SLA",
    "Direct line to engineering for incident response",
    "Audit log retention: unlimited + cold archive",
]
fy = col_y + col_h - 1.75 * inch
for f in vpc_features:
    c.setFillColor(GREEN if not f.startswith("Everything") else GREY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col2_x + 0.2 * inch, fy, "✓" if not f.startswith("Everything") else "+")
    c.setFillColor(INK if not f.startswith("Everything") else GREY)
    c.setFont("Helvetica-Bold" if f.startswith("Everything") else "Helvetica", 9)
    c.drawString(col2_x + 0.4 * inch, fy, f)
    fy -= 0.2 * inch

# Why two tiers — explanatory note
note_y = col_y - 0.4 * inch
c.setFillColor(NAVY)
c.setFont("Helvetica-Bold", 11)
c.drawString(MARGIN, note_y, "Which one is right for you?")
text_block(
    c,
    MARGIN,
    note_y - 0.3 * inch,
    PAGE_W - 2 * MARGIN,
    1.2 * inch,
    text="Multi-tenant fits most regulated mid-market deployments — the audit chain "
    "isolates each customer cryptographically, even on shared infrastructure. "
    "Dedicated VPC is for organizations with hard isolation requirements: "
    "ITAR / CMMC scoping, internal data-residency rules, customer-mandated "
    "VPC isolation in downstream deals, or a board mandate that AI "
    "infrastructure not run on shared compute. If you're not sure, start on "
    "Multi-Tenant — you can migrate up later.",
    size=9,
    color=INK,
)

# VPC migration / stand-up fee callout
fee_y = note_y - 1.55 * inch
c.setFillColor(LIGHT_BG)
c.setStrokeColor(LINE)
c.rect(MARGIN, fee_y - 0.65 * inch, PAGE_W - 2 * MARGIN, 0.65 * inch, fill=1, stroke=1)
c.setFillColor(BLUE)
c.rect(MARGIN, fee_y - 0.65 * inch, 0.05 * inch, 0.65 * inch, fill=1, stroke=0)
c.setFillColor(NAVY)
c.setFont("Helvetica-Bold", 10)
c.drawString(MARGIN + 0.18 * inch, fee_y - 0.22 * inch, "VPC stand-up fee  ·  $5,000 one-time")
c.setFillColor(INK)
c.setFont("Helvetica", 9)
c.drawString(
    MARGIN + 0.18 * inch,
    fee_y - 0.42 * inch,
    "Covers dedicated cluster provisioning, KMS keyring, Postgres instance, network isolation, and migration "
    "of existing audit-chain data. Waived for founding-cohort partners.",
)

draw_footer(c)
c.showPage()


# ── Page 4: Founding-partner terms ───────────────────────────────────────

draw_header(c, 4, TOTAL, "Founding-partner terms")
text_block(
    c,
    MARGIN,
    PAGE_H - 1.4 * inch,
    PAGE_W - 2 * MARGIN,
    0.5 * inch,
    text="The first three to four paid Enterprise customers receive founding-partner "
    "status. The terms below apply to that cohort only — this is a finite, "
    "selective program, not an evergreen discount.",
    size=10,
    color=GREY,
)

# Hero offer band — taller, two-line headline so nothing overflows
y = PAGE_H - 2.4 * inch
band_h = 1.7 * inch
c.setFillColor(NAVY)
c.rect(MARGIN, y - band_h, PAGE_W - 2 * MARGIN, band_h, fill=1, stroke=0)
c.setFillColor(AMBER)
c.rect(MARGIN, y - band_h, 0.18 * inch, band_h, fill=1, stroke=0)
c.setFillColor(AMBER)
c.setFont("Helvetica-Bold", 10)
c.drawString(MARGIN + 0.4 * inch, y - 0.32 * inch, "FOUNDING-PARTNER OFFER")
# Two-line headline: line 1 white "90 days free", line 2 white "+ 24-month rate lock at today's published rates"
c.setFillColor(WHITE)
c.setFont("Helvetica-Bold", 22)
c.drawString(MARGIN + 0.4 * inch, y - 0.7 * inch, "90 days free")
c.setFont("Helvetica-Bold", 19)
c.drawString(
    MARGIN + 0.4 * inch, y - 1.05 * inch, "+  24-month rate lock at today's published rates"
)
c.setFont("Helvetica", 10)
c.setFillColor(colors.HexColor("#C9D4E6"))
c.drawString(
    MARGIN + 0.4 * inch,
    y - 1.36 * inch,
    "If it isn't a fit at day 90, walk away. No termination clause. "
    "No kickback. Data export via the audit API.",
)
c.setFont("Helvetica-Bold", 9)
c.setFillColor(AMBER)
c.drawString(
    MARGIN + 0.4 * inch, y - 1.58 * inch, "OPEN TO THE FIRST 3-4 PAID ENTERPRISE CUSTOMERS"
)

# Three-column cards: included / status / day 91+
col_y = y - 4.5 * inch
col_h = 2.55 * inch
col_w = (PAGE_W - 2 * MARGIN - 0.3 * inch) / 3
c1, c2, c3 = MARGIN, MARGIN + col_w + 0.15 * inch, MARGIN + 2 * (col_w + 0.15 * inch)

card(
    c,
    c1,
    col_y,
    col_w,
    col_h,
    accent=PURPLE,
    title="ENTERPRISE TIER — INCLUDED",
    body_lines=[
        "·  Unlimited agents",
        "·  Unlimited requests",
        "·  Unlimited audit retention",
        "·  Full SSO + SAML / SCIM",
        "·  Compliance evidence export",
        "·  Team roles + assignments",
        "·  Human-in-the-loop review",
        "·  Anomaly detection",
        "·  Dedicated VPC option",
        "·  Dedicated support + SLA",
    ],
    body_size=8.5,
)
card(
    c,
    c2,
    col_y,
    col_w,
    col_h,
    accent=GREEN,
    title="WHAT FOUNDING STATUS ADDS",
    body_lines=[
        "·  Direct founder line — same-day responsiveness",
        "·  First three policies authored with you, not by you",
        "·  Real influence on product roadmap during evaluation",
        "·  Quarterly evidence-pack export through your auditor of choice",
        "·  Optional named launch case study, full sign-off on every quote",
        "·  Pricing locked at today's rates for 24 months — protected from any future increase",
    ],
    body_size=8.5,
)
card(
    c,
    c3,
    col_y,
    col_w,
    col_h,
    accent=BLUE,
    title="WHAT HAPPENS AT DAY 91",
    body_lines=[
        "Continue on Enterprise — $1,500 (multi-tenant) or $3,000 (VPC). 24-month rate lock kicks in.",
        " ",
        "Step down to Pro / Business / Business+ — $79, $299, or $599. No penalty.",
        " ",
        "Walk away — no termination clause, no kickback. Data export via audit API. We delete on request.",
    ],
    body_size=8.5,
)

draw_footer(c)
c.showPage()


# ── Page 5: Pricing trajectory & timeline ───────────────────────────────

draw_header(c, 5, TOTAL, "Pricing trajectory")
text_block(
    c,
    MARGIN,
    PAGE_H - 1.4 * inch,
    PAGE_W - 2 * MARGIN,
    0.5 * inch,
    text="Honest framing: today's published Enterprise rates are unusually low for the "
    "category because we are early. Below is the planned price-up path. "
    "Founding-cohort partners are insulated from the increase via the 24-month rate lock.",
    size=10,
    color=GREY,
)

# Timeline visual: three phases
phase_y = PAGE_H - 4.5 * inch
phase_h = 2.6 * inch
phase_w = (PAGE_W - 2 * MARGIN - 0.3 * inch) / 3

phases = [
    {
        "kind": "priced",
        "label": "PHASE 1  ·  TODAY",
        "title": "Founding-cohort window",
        "subtitle": "April 2026 — until trigger fires",
        "price_mt": "$1,500 / mo",
        "price_vpc": "$3,000 / mo",
        "note": "Open to the first 3-4 paid Enterprise customers. Each gets 90 days free + a 24-month rate lock at these rates.",
        "color": GREEN,
    },
    {
        "kind": "trigger",
        "label": "TRIGGER  ·  WHEN IT FIRES",
        "title": "Trigger condition",
        "subtitle": "Estimated Q3 2026 — Q1 2027",
        "callout_top": "3rd paid partner",
        "callout_bot": "crosses day-91",
        "note": "When the 3rd founding-cohort partner reaches day-91 with a continued (non-churned) subscription, the standard Enterprise rate moves to Phase 2. Founding partners stay locked at Phase 1 rates.",
        "color": AMBER,
    },
    {
        "kind": "priced",
        "label": "PHASE 2  ·  POST-TRIGGER",
        "title": "Standard rate-card",
        "subtitle": "After trigger, indefinitely",
        "price_mt": "$2,500 / mo",
        "price_vpc": "$5,000 / mo",
        "note": "Standard published Enterprise rate for new customers. Founding-cohort partners continue at $1,500 / $3,000 for the duration of their 24-month lock.",
        "color": INDIGO,
    },
]
for i, p in enumerate(phases):
    x = MARGIN + i * (phase_w + 0.15 * inch)
    # Card background
    c.setFillColor(LIGHT_BG)
    c.setStrokeColor(LINE)
    c.rect(x, phase_y, phase_w, phase_h, fill=1, stroke=1)
    # Top color bar
    c.setFillColor(p["color"])
    c.rect(x, phase_y + phase_h - 0.1 * inch, phase_w, 0.1 * inch, fill=1, stroke=0)
    # Phase label
    c.setFillColor(p["color"])
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 0.18 * inch, phase_y + phase_h - 0.35 * inch, p["label"])
    # Card title
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(x + 0.18 * inch, phase_y + phase_h - 0.6 * inch, p["title"])
    # Subtitle
    c.setFillColor(GREY)
    c.setFont("Helvetica", 9)
    c.drawString(x + 0.18 * inch, phase_y + phase_h - 0.8 * inch, p["subtitle"])

    if p["kind"] == "priced":
        # Two-price stack
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(x + 0.18 * inch, phase_y + phase_h - 1.2 * inch, p["price_mt"])
        c.setFont("Helvetica", 9)
        c.setFillColor(GREY)
        c.drawString(x + 0.18 * inch, phase_y + phase_h - 1.4 * inch, "Multi-tenant")
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(x + 0.18 * inch, phase_y + phase_h - 1.7 * inch, p["price_vpc"])
        c.setFont("Helvetica", 9)
        c.setFillColor(GREY)
        c.drawString(x + 0.18 * inch, phase_y + phase_h - 1.9 * inch, "Dedicated VPC")
    else:
        # Trigger callout — visually distinct but same dimensions as price block
        cy = phase_y + phase_h - 1.95 * inch
        ch = 0.85 * inch
        cx = x + 0.18 * inch
        cw = phase_w - 0.36 * inch
        c.setFillColor(WHITE)
        c.setStrokeColor(p["color"])
        c.setLineWidth(1)
        c.rect(cx, cy, cw, ch, fill=1, stroke=1)
        c.setFillColor(p["color"])
        c.setFont("Helvetica-Bold", 13)
        c.drawCentredString(cx + cw / 2, cy + ch - 0.3 * inch, p["callout_top"])
        c.setFillColor(NAVY)
        c.drawCentredString(cx + cw / 2, cy + ch - 0.55 * inch, p["callout_bot"])

    # Note (same vertical position for all three cards so footer aligns)
    text_block(
        c,
        x + 0.18 * inch,
        phase_y + phase_h - 2.12 * inch,
        phase_w - 0.36 * inch,
        0.85 * inch,
        text=p["note"],
        size=8,
        color=INK,
        leading=10,
    )

# Below — "Why we'll raise prices"
note_y = phase_y - 0.5 * inch
c.setFillColor(NAVY)
c.setFont("Helvetica-Bold", 11)
c.drawString(MARGIN, note_y, "Why the Phase 2 increase is justifiable")
reasons = [
    "Three to four paying customers is the product-market-fit signal that earns ~30-50% pricing power across enterprise SaaS — 67% is the low end of that band.",
    "Case studies from the founding cohort reduce sales cycle for new prospects by a measurable margin.",
    "By trigger-time, we have empirical cost-to-serve data from real workloads — not the GKE estimates we use today.",
    "Comparable enterprise security tools (Vault Enterprise, Wiz, CyberArk machine identities) sit at $30-150K/yr base. AI Identity at $30K/yr stays the cheapest agent-native option.",
    "Feature maturity by Q4 2026: multi-step traces, expanded compliance profiles, expanded SIEM integrations — Enterprise will include more by then.",
]
ry = note_y - 0.3 * inch
for r in reasons:
    c.setFillColor(GREEN)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN, ry, "·")
    ry = text_block(
        c,
        MARGIN + 0.18 * inch,
        ry,
        PAGE_W - 2 * MARGIN - 0.18 * inch,
        0.4 * inch,
        text=r,
        size=9,
        color=INK,
        leading=11,
    )
    ry -= 0.05 * inch

draw_footer(c)
c.showPage()


# ── Page 6: How to engage ──────────────────────────────────────────────

draw_header(c, 6, TOTAL, "How to engage")
text_block(
    c,
    MARGIN,
    PAGE_H - 1.4 * inch,
    PAGE_W - 2 * MARGIN,
    0.5 * inch,
    text="Below is the standard founding-partner conversation flow. It's designed to "
    "be light-touch and to give you decision points before any commitment.",
    size=10,
    color=GREY,
)

steps = [
    (
        "Step 1",
        "Discovery call (45-60 min)",
        "We walk through your agent inventory, the regulatory context, and the specific risk you're trying to manage. Before the call, you'll receive a short Discovery Doc to fill out — it keeps the conversation focused and becomes the foundation for the scoping doc. No deck unless you want one.",
    ),
    (
        "Step 2",
        "Scoping doc (within 5 business days)",
        "I draft a one-page scoping document: which agents, which policies, which compliance posture, success criteria for day 90. You review and we iterate to alignment. No subscription started yet.",
    ),
    (
        "Step 3",
        "Pilot kickoff",
        "Standard Enterprise tier provisioned with 100%-off coupon for 90 days. I write your first three policies with your team. Weekly office hours with me directly.",
    ),
    (
        "Step 4",
        "Day 60 review",
        "Joint review of usage data, policies in flight, value delivered. You decide: continue at $1,500 / $3,000 with 24-month rate lock, step down to Pro / Business / Business+, or walk away.",
    ),
    (
        "Step 5",
        "Day 91 onwards",
        "If continuing: subscription begins automatically, locked at today's published rates for 24 months. Quarterly check-ins with me. Compliance evidence pack delivered every quarter.",
    ),
]
y = PAGE_H - 2.0 * inch
for label, headline, body in steps:
    c.setFillColor(LIGHT_BG)
    c.setStrokeColor(LINE)
    c.rect(MARGIN, y - 1.0 * inch, PAGE_W - 2 * MARGIN, 1.0 * inch, fill=1, stroke=1)
    c.setFillColor(NAVY)
    c.rect(MARGIN, y - 1.0 * inch, 1.4 * inch, 1.0 * inch, fill=1, stroke=0)
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN + 0.2 * inch, y - 0.55 * inch, label)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(MARGIN + 1.6 * inch, y - 0.27 * inch, headline)
    text_block(
        c,
        MARGIN + 1.6 * inch,
        y - 0.5 * inch,
        PAGE_W - 2 * MARGIN - 1.8 * inch,
        0.6 * inch,
        text=body,
        size=9,
        color=INK,
        leading=11,
    )
    y -= 1.1 * inch

# Contact band
c.setFillColor(NAVY)
c.rect(MARGIN, y - 0.85 * inch, PAGE_W - 2 * MARGIN, 0.85 * inch, fill=1, stroke=0)
c.setFillColor(AMBER)
c.rect(MARGIN, y - 0.85 * inch, 0.15 * inch, 0.85 * inch, fill=1, stroke=0)
c.setFillColor(AMBER)
c.setFont("Helvetica-Bold", 9)
c.drawString(MARGIN + 0.35 * inch, y - 0.25 * inch, "TO START THE CONVERSATION")
c.setFillColor(WHITE)
c.setFont("Helvetica-Bold", 14)
c.drawString(MARGIN + 0.35 * inch, y - 0.5 * inch, "Jeff Leva  ·  Founder & CEO")
c.setFont("Helvetica", 11)
c.setFillColor(colors.HexColor("#C9D4E6"))
c.drawString(
    MARGIN + 0.35 * inch,
    y - 0.7 * inch,
    "jeff@ai-identity.co  ·  ai-identity.co  ·  linkedin.com/in/jeff-leva-a7373958",
)

draw_footer(c)
c.showPage()


# Save
OUT.parent.mkdir(parents=True, exist_ok=True)
c.save()
print(f"Saved: {OUT}")
print(f"Pages: {TOTAL}")
