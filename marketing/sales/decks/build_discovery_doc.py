"""Build the AI Identity Discovery Document — a branded PDF sent to prospects
before the discovery call. The client fills out what they can; Jeff adds notes
and context during / after the call. Output feeds directly into the scoping doc.

Run: python3 build_discovery_doc.py
Output: ../discovery-doc.pdf
"""

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# ── Theme (matches pricing sheet) ────────────────────────────────────────

NAVY = colors.HexColor("#0B1933")
INK = colors.HexColor("#1A1F36")
GREY = colors.HexColor("#6B7280")
LIGHT_GREY = colors.HexColor("#9CA3AF")
LIGHT_BG = colors.HexColor("#F5F7FA")
LINE = colors.HexColor("#E2E5EB")
WHITE = colors.HexColor("#FFFFFF")
AMBER = colors.HexColor("#E09F3E")
GREEN = colors.HexColor("#36A16B")
BLUE = colors.HexColor("#4F8FE5")
PURPLE = colors.HexColor("#8E6FE6")
FIELD_BG = colors.HexColor("#FAFBFC")

PAGE_W, PAGE_H = LETTER
MARGIN = 0.65 * inch
CONTENT_W = PAGE_W - 2 * MARGIN

OUT = Path(__file__).resolve().parent.parent / "discovery-doc.pdf"

c = canvas.Canvas(str(OUT), pagesize=LETTER)
c.setTitle("AI Identity — Discovery Document")
c.setAuthor("AI Identity")
c.setSubject("Pre-call discovery intake for prospective Enterprise partners")

TOTAL = 3


# ── Helpers ───────────────────────────────────────────────────────────────


def draw_header(page_num: int):
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN, PAGE_H - 0.5 * inch, "AI IDENTITY")
    c.setFont("Helvetica", 9)
    c.setFillColor(GREY)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.5 * inch, f"Page {page_num} / {TOTAL}")
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.line(MARGIN, PAGE_H - 0.65 * inch, PAGE_W - MARGIN, PAGE_H - 0.65 * inch)


def draw_footer():
    c.setFillColor(GREY)
    c.setFont("Helvetica", 8)
    c.drawString(
        MARGIN,
        0.45 * inch,
        f"AI Identity · Discovery Document · {date.today().strftime('%B %d, %Y')}",
    )
    c.drawRightString(PAGE_W - MARGIN, 0.45 * inch, "Confidential — for prospective partners")


def section_header(y: float, num: str, title: str, subtitle: str = "") -> float:
    """Draws a section header bar. Returns y position below it."""
    bar_h = 0.32 * inch
    c.setFillColor(NAVY)
    c.rect(MARGIN, y - bar_h, CONTENT_W, bar_h, fill=1, stroke=0)
    c.setFillColor(AMBER)
    c.rect(MARGIN, y - bar_h, 0.08 * inch, bar_h, fill=1, stroke=0)
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MARGIN + 0.18 * inch, y - 0.13 * inch, num)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN + 0.52 * inch, y - 0.13 * inch, title.upper())
    if subtitle:
        c.setFillColor(colors.HexColor("#9DA9C1"))
        c.setFont("Helvetica", 8)
        c.drawRightString(PAGE_W - MARGIN - 0.1 * inch, y - 0.13 * inch, subtitle)
    return y - bar_h - 0.12 * inch


def field(
    y: float, label: str, height: float = 0.38 * inch, hint: str = "", width: float = None
) -> float:
    """Draws a labeled input field. Returns y below."""
    w = width or CONTENT_W
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MARGIN, y, label)
    fy = y - 0.14 * inch
    c.setFillColor(FIELD_BG)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.rect(MARGIN, fy - height, w, height, fill=1, stroke=1)
    if hint:
        c.setFillColor(LIGHT_GREY)
        c.setFont("Helvetica", 7.5)
        c.drawString(MARGIN + 0.1 * inch, fy - height + 0.1 * inch, hint)
    return fy - height - 0.16 * inch


def field_pair(
    y: float,
    label_a: str,
    label_b: str,
    hint_a: str = "",
    hint_b: str = "",
    height: float = 0.38 * inch,
) -> float:
    """Two equal-width fields side by side. Returns y below."""
    half = (CONTENT_W - 0.2 * inch) / 2
    left_y = field(y, label_a, height=height, hint=hint_a, width=half)
    # Right field — draw manually at offset x
    rx = MARGIN + half + 0.2 * inch
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(rx, y, label_b)
    fy = y - 0.14 * inch
    c.setFillColor(FIELD_BG)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.5)
    c.rect(rx, fy - height, half, height, fill=1, stroke=1)
    if hint_b:
        c.setFillColor(LIGHT_GREY)
        c.setFont("Helvetica", 7.5)
        c.drawString(rx + 0.1 * inch, fy - height + 0.1 * inch, hint_b)
    return left_y  # both sides same height


def checkbox_list(y: float, items: list[str], cols: int = 2) -> float:
    """Renders a multi-column checkbox list. Returns y below."""
    col_w = CONTENT_W / cols
    row_h = 0.22 * inch
    for i, item in enumerate(items):
        col = i % cols
        row = i // cols
        xi = MARGIN + col * col_w
        yi = y - row * row_h
        # Box
        c.setStrokeColor(LINE)
        c.setFillColor(WHITE)
        c.rect(xi, yi - 0.12 * inch, 0.13 * inch, 0.13 * inch, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont("Helvetica", 8.5)
        c.drawString(xi + 0.2 * inch, yi - 0.1 * inch, item)
    total_rows = -(-len(items) // cols)  # ceiling div
    return y - total_rows * row_h - 0.1 * inch


def note_callout(y: float, text: str, color=BLUE, height: float = 0.52 * inch) -> float:
    c.setFillColor(LIGHT_BG)
    c.setStrokeColor(LINE)
    c.rect(MARGIN, y - height, CONTENT_W, height, fill=1, stroke=1)
    c.setFillColor(color)
    c.rect(MARGIN, y - height, 0.05 * inch, height, fill=1, stroke=0)
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MARGIN + 0.18 * inch, y - 0.16 * inch, "NOTE")
    c.setFillColor(INK)
    c.setFont("Helvetica", 8)
    # simple wrap
    words = text.split()
    line, cur_y = "", y - 0.28 * inch
    max_w = CONTENT_W - 0.3 * inch
    for word in words:
        test = (line + " " + word).strip()
        if c.stringWidth(test, "Helvetica", 8) > max_w:
            c.drawString(MARGIN + 0.18 * inch, cur_y, line)
            cur_y -= 10
            line = word
        else:
            line = test
    if line:
        c.drawString(MARGIN + 0.18 * inch, cur_y, line)
    return y - height - 0.15 * inch


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 1 — Cover + Sections 1 & 2
# ═══════════════════════════════════════════════════════════════════════════

draw_header(1)

# Hero band
c.setFillColor(NAVY)
c.rect(0, PAGE_H - 2.0 * inch, PAGE_W, 2.0 * inch, fill=1, stroke=0)
c.setFillColor(AMBER)
c.rect(MARGIN, PAGE_H - 1.65 * inch, 0.14 * inch, 1.1 * inch, fill=1, stroke=0)
c.setFillColor(WHITE)
c.setFont("Helvetica-Bold", 10)
c.drawString(MARGIN + 0.32 * inch, PAGE_H - 0.72 * inch, "AI IDENTITY")
c.setFont("Helvetica-Bold", 26)
c.drawString(MARGIN + 0.32 * inch, PAGE_H - 1.12 * inch, "Discovery Document")
c.setFillColor(colors.HexColor("#C9D4E6"))
c.setFont("Helvetica", 10)
c.drawString(
    MARGIN + 0.32 * inch,
    PAGE_H - 1.42 * inch,
    "Please fill out what you can before our call. We'll review together and build on it.",
)
c.setFillColor(colors.HexColor("#9DA9C1"))
c.setFont("Helvetica", 9)
c.drawRightString(
    PAGE_W - MARGIN,
    PAGE_H - 1.42 * inch,
    f"Prepared for your discovery call  ·  {date.today().strftime('%B %d, %Y')}",
)

y = PAGE_H - 2.25 * inch

# ── Section 1: Company & Contact ─────────────────────────────────────────
y = section_header(y, "01", "Company & Contact", "Fill out before the call")

y = field_pair(y, "Company name", "Website / LinkedIn")
y = field_pair(y, "Your name & title", "Best email for follow-up")
y = field_pair(
    y,
    "Other attendees on your side",
    "Preferred call timezone / slot",
    hint_a="Name, title (list all who will join)",
    hint_b="e.g. US-East, afternoons",
)
y -= 0.05 * inch

# ── Section 2: Agent Inventory ────────────────────────────────────────────
y = section_header(y, "02", "Agent Inventory", "Tell us what you're running or building")

y = field(
    y,
    "What agents do you have in production or in development?",
    height=0.55 * inch,
    hint="e.g. customer-support agent, internal data-retrieval agent, code-gen pipeline — list each briefly",
)

y = field_pair(
    y,
    "Approx. requests / month (total across agents)",
    "Number of distinct agents (today / projected 12 mo)",
    hint_a="e.g. 200K / mo",
    hint_b="e.g. 4 today → 20 in 12 months",
)

y = field(y, "What do these agents have access to? (check all that apply)", height=0.0 * inch)
y = checkbox_list(
    y + 0.02 * inch,
    [
        "Customer PII / account data",
        "Internal knowledge base / docs",
        "Financial / billing systems",
        "Code repositories",
        "Third-party APIs (CRM, ERP, etc.)",
        "Email / calendar / communication tools",
        "Healthcare / clinical data",
        "Other (describe below)",
    ],
    cols=2,
)
y = field(y, "Other access / notes", height=0.32 * inch)

draw_footer()
c.showPage()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 2 — Sections 3, 4, 5
# ═══════════════════════════════════════════════════════════════════════════

draw_header(2)
y = PAGE_H - 0.95 * inch

# ── Section 3: Compliance & Regulatory Context ────────────────────────────
y = section_header(y, "03", "Compliance & Regulatory Context")

y = field(
    y,
    "Which compliance frameworks apply to your organization? (check all that apply)",
    height=0.0 * inch,
)
y = checkbox_list(
    y + 0.02 * inch,
    [
        "SOC 2 Type II",
        "ISO 27001",
        "HIPAA",
        "GDPR / EU AI Act",
        "NIST AI RMF",
        "FedRAMP",
        "ITAR / CMMC",
        "None yet — planning ahead",
    ],
    cols=2,
)

y = field_pair(
    y,
    "Are you currently audited / certified for any of these?",
    "Next audit or certification deadline",
    hint_a="Which ones, and by which auditor?",
    hint_b="Approximate date or quarter",
)

y = field(
    y,
    "Do you have an AI governance policy today?",
    height=0.38 * inch,
    hint="Yes / No / In progress — describe briefly if yes",
)

y = field(
    y,
    "Any specific data-residency or sovereignty requirements?",
    height=0.38 * inch,
    hint="e.g. data must stay in EU, no US-hosted compute, customer contract requirements",
)
y -= 0.05 * inch

# ── Section 4: Current Risk & Pain Points ────────────────────────────────
y = section_header(y, "04", "Current Risk & Pain Points")

y = field(
    y,
    "What is the primary risk or problem that brought you here?",
    height=0.55 * inch,
    hint="e.g. no audit trail for agent actions, credential sprawl, compliance gap, customer ask, board mandate",
)

y = field_pair(
    y,
    "Has an agent ever taken an action it shouldn't have?",
    "Is this a board / C-suite / legal priority or a team-level initiative?",
    hint_a="Yes / No — brief description if yes",
    hint_b="Who is the internal sponsor for this?",
)

y = field(
    y,
    "What does 'good' look like at the end of a 90-day pilot?",
    height=0.52 * inch,
    hint="Be specific — e.g. 'every agent action is logged and attributable', 'we can produce a SOC 2 evidence pack on demand'",
)
y -= 0.05 * inch

# ── Section 5: Tech Stack & Infrastructure ───────────────────────────────
y = section_header(y, "05", "Tech Stack & Infrastructure")

y = field_pair(
    y,
    "Which AI / agent frameworks are you using?",
    "Where is your infrastructure hosted?",
    hint_a="e.g. LangChain, CrewAI, custom, OpenAI Assistants",
    hint_b="e.g. AWS, GCP, Azure, on-prem, hybrid",
)

y = field_pair(
    y,
    "Identity provider (IdP) in use?",
    "SIEM or log-aggregation tooling?",
    hint_a="e.g. Okta, Azure AD, Google Workspace",
    hint_b="e.g. Splunk, Datadog, none yet",
)

y = field(
    y,
    "Any hard integration requirements or constraints we should know about?",
    height=0.38 * inch,
    hint="e.g. must integrate with existing SIEM, no new SaaS vendors without security review, VPN required",
)

draw_footer()
c.showPage()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 3 — Sections 6 & 7 + Jeff's notes area
# ═══════════════════════════════════════════════════════════════════════════

draw_header(3)
y = PAGE_H - 0.95 * inch

# ── Section 6: Stakeholders & Timeline ───────────────────────────────────
y = section_header(y, "06", "Stakeholders & Timeline")

y = field(
    y,
    "Who else needs to be involved in the decision?",
    height=0.38 * inch,
    hint="e.g. CISO, GC, CTO, procurement — name / role / what they care about",
)

y = field_pair(
    y,
    "What is your target start date for a pilot?",
    "Is there a hard deadline driving urgency?",
    hint_a="e.g. Q3 2026, before next audit",
    hint_b="e.g. contract renewal, board review, audit date",
)

y = field_pair(
    y,
    "Have you evaluated any alternatives?",
    "Approximate annual budget range for this category",
    hint_a="e.g. build in-house, competitor, doing nothing",
    hint_b="e.g. <$50K, $50-150K, $150K+, unknown",
)
y -= 0.05 * inch

# ── Section 7: Anything Else ──────────────────────────────────────────────
y = section_header(
    y, "07", "Anything Else We Should Know?", "Open field — add whatever didn't fit above"
)

y = field(
    y,
    "Open notes — context, concerns, questions you want to make sure we cover",
    height=0.65 * inch,
)
y -= 0.05 * inch

# ── Jeff's Notes (visually distinct) ─────────────────────────────────────
notes_h = y - 0.75 * inch  # use remaining space above footer
c.setFillColor(colors.HexColor("#EEF3FB"))
c.setStrokeColor(BLUE)
c.setLineWidth(0.75)
c.rect(MARGIN, y - notes_h, CONTENT_W, notes_h, fill=1, stroke=1)
c.setFillColor(BLUE)
c.rect(MARGIN, y - notes_h, 0.07 * inch, notes_h, fill=1, stroke=0)
c.setFillColor(BLUE)
c.setFont("Helvetica-Bold", 9)
c.drawString(MARGIN + 0.2 * inch, y - 0.2 * inch, "JEFF'S NOTES")
c.setFillColor(GREY)
c.setFont("Helvetica", 8)
c.drawString(
    MARGIN + 0.2 * inch,
    y - 0.35 * inch,
    "For internal use — observations, clarifications, and next steps from the call",
)
# Ruled lines
line_start = y - 0.55 * inch
line_gap = 0.28 * inch
line_x1 = MARGIN + 0.2 * inch
line_x2 = PAGE_W - MARGIN - 0.1 * inch
cur = line_start
while cur > y - notes_h + 0.15 * inch:
    c.setStrokeColor(colors.HexColor("#C8D8F0"))
    c.setLineWidth(0.4)
    c.line(line_x1, cur, line_x2, cur)
    cur -= line_gap

draw_footer()
c.showPage()


# ── Save ──────────────────────────────────────────────────────────────────
OUT.parent.mkdir(parents=True, exist_ok=True)
c.save()
print(f"Saved: {OUT}")
print(f"Pages: {TOTAL}")
