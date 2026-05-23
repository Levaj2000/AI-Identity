"""Build the Range Ventures investor one-pager.

AI Identity Purple template — single-page PDF tear-sheet, designed to be
forwarded inside a partnership without losing the pitch.

Sent alongside the deck in response to Hayfa Aboukier's 2026-05-12 ask.

Run: python3 build_range_ventures_one_pager.py
Output: ../range-ventures-one-pager-2026-05-12.pdf
"""

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

# Use Helvetica everywhere (Inter not guaranteed on every macOS install).
FONT_REG = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"

OUT = Path(__file__).resolve().parent.parent / "range-ventures-one-pager-2026-05-12.pdf"

# Page = US Letter portrait
PAGE_W, PAGE_H = letter  # 612 x 792 pt


# ── Helpers ──────────────────────────────────────────────────────────────


def draw_rect(c, x, y, w, h, fill=None, stroke=None, stroke_width=0.5):
    if fill is not None:
        c.setFillColor(fill)
    if stroke is not None:
        c.setStrokeColor(stroke)
        c.setLineWidth(stroke_width)
    c.rect(x, y, w, h, stroke=1 if stroke else 0, fill=1 if fill else 0)


def draw_text(c, x, y, text, *, font=FONT_REG, size=10, color=INK):
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawString(x, y, text)


def draw_wrapped(c, x, y, w, text, *, font=FONT_REG, size=10, color=INK, leading=None):
    """Word-wrap text into width w, return new y after drawing."""
    if leading is None:
        leading = size * 1.35
    c.setFillColor(color)
    c.setFont(font, size)
    words = text.split()
    line: list[str] = []
    while words:
        line.append(words.pop(0))
        if c.stringWidth(" ".join(line), font, size) > w:
            # back off one word
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


def draw_eyebrow(c, x, y, text):
    c.setFillColor(PURPLE_MID)
    c.setFont(FONT_BOLD, 7.5)
    c.drawString(x, y, text.upper())


def draw_circle_number(c, x, y, diam, number):
    c.setFillColor(PURPLE_DEEP)
    c.circle(x + diam / 2, y + diam / 2, diam / 2, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 7.5)
    txt = str(number)
    tw = c.stringWidth(txt, FONT_BOLD, 7.5)
    c.drawString(x + (diam - tw) / 2, y + diam / 2 - 2.8, txt)


# ── Page composition ─────────────────────────────────────────────────────


def main():
    c = canvas.Canvas(str(OUT), pagesize=letter)
    c.setTitle("AI Identity — Investor One-Pager")
    c.setAuthor("Jeff Leva")
    c.setSubject("Range Ventures · May 2026")

    # ── Top purple header bar ────────────────────────────────────────────
    bar_h = 0.55 * inch
    draw_rect(c, 0, PAGE_H - bar_h, PAGE_W, bar_h, fill=PURPLE_DEEP)
    # Lighter purple accent bar at very top
    draw_rect(c, 0, PAGE_H - 8, PAGE_W, 8, fill=PURPLE_MID)

    # Title in header
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 18)
    c.drawString(0.5 * inch, PAGE_H - 0.36 * inch, "AI Identity")
    c.setFillColor(LAVENDER)
    c.setFont(FONT_REG, 10)
    c.drawString(2.0 * inch, PAGE_H - 0.36 * inch, "Trust Root for the Agent Economy")

    # Right side of header — prepared for
    c.setFillColor(LAVENDER)
    c.setFont(FONT_BOLD, 7)
    c.drawRightString(PAGE_W - 0.5 * inch, PAGE_H - 0.25 * inch, "INVESTOR ONE-PAGER")
    c.setFillColor(WHITE)
    c.setFont(FONT_REG, 8.5)
    c.drawRightString(
        PAGE_W - 0.5 * inch, PAGE_H - 0.41 * inch, "Hayfa Aboukier · Range Ventures · May 12, 2026"
    )

    # ── Cursor below header ──────────────────────────────────────────────
    y = PAGE_H - bar_h - 0.3 * inch
    left = 0.5 * inch
    right = PAGE_W - 0.5 * inch
    col_w = right - left

    # ── Thesis statement ─────────────────────────────────────────────────
    draw_eyebrow(c, left, y, "Thesis")
    y -= 14
    c.setFillColor(PURPLE_DEEP)
    c.setFont(FONT_BOLD, 13)
    c.drawString(
        left,
        y,
        "Every AI agent today runs on a shared key. We're building the trust layer that fixes it.",
    )
    y -= 18
    y = draw_wrapped(
        c,
        left,
        y,
        col_w,
        "Cryptographic agent identity, hash-chained audit, and context-aware policy enforcement — "
        "the primitives the agent economy needs but doesn't have. Live in production today. "
        "Dogfooded by our own engineering agent. Onboarding design partners now.",
        size=9.5,
        color=INK,
        leading=13,
    )
    y -= 4

    # ── Three-column "what we built" strip ───────────────────────────────
    strip_h = 1.05 * inch
    col_gap = 8
    box_w = (col_w - 2 * col_gap) / 3
    strip_y = y - strip_h
    items = [
        (
            "01 / IDENTITY",
            "Per-agent keys",
            "Signed, revocable, rotatable. Issuance, rotation, revocation, TTL — first-class.",
        ),
        (
            "02 / POLICY",
            "Gateway enforcement",
            "Deny-by-default, ABAC on agent metadata. Per-agent, per-decision — not per service account.",
        ),
        (
            "03 / EVIDENCE",
            "Hash-chained audit",
            "HMAC-chained at write time. ECDSA-signed session attestations. Offline verification CLI.",
        ),
    ]
    for i, (eyebrow, title, body) in enumerate(items):
        x = left + i * (box_w + col_gap)
        draw_rect(c, x, strip_y, box_w, strip_h, fill=LAVENDER)
        draw_rect(c, x, strip_y, 3, strip_h, fill=PURPLE_DEEP)
        c.setFillColor(PURPLE_MID)
        c.setFont(FONT_BOLD, 7)
        c.drawString(x + 10, strip_y + strip_h - 14, eyebrow)
        c.setFillColor(PURPLE_DEEP)
        c.setFont(FONT_BOLD, 11)
        c.drawString(x + 10, strip_y + strip_h - 30, title)
        draw_wrapped(
            c, x + 10, strip_y + strip_h - 44, box_w - 20, body, size=8.5, color=INK, leading=11
        )
    y = strip_y - 0.18 * inch

    # ── Why now ──────────────────────────────────────────────────────────
    draw_eyebrow(c, left, y, "Why now")
    y -= 12
    y = draw_wrapped(
        c,
        left,
        y,
        col_w,
        "Two forces collide: agentic AI is moving into production across banks, healthcare, and "
        "government this quarter — and EU AI Act enforcement (Aug 2026), NIST AI RMF, and SOC 2 "
        "are starting to name agent governance as a specific control area. Trust infrastructure "
        "for the agent economy gets built once. We are six to eighteen months ahead of where the "
        "buyer is just starting to ask.",
        size=9,
        color=INK,
        leading=12,
    )
    y -= 4

    # ── Traction / Live today ────────────────────────────────────────────
    draw_eyebrow(c, left, y, "Traction · live today")
    y -= 14
    kpi_h = 0.62 * inch
    kpi_y = y - kpi_h
    kpis = [
        ("Prod", "Live on GKE", "Binary Auth, Cloud Armor, RLS"),
        ("3", "Probes indexed", "/forensics, /compliance-pack, /pqc-readiness"),
        ("~20mo", "Runway stacked", "GCP + MongoDB startup credits"),
        ("0ms", "Added latency", "Offline verification — off the hot path"),
    ]
    kpi_gap = 6
    kpi_w = (col_w - 3 * kpi_gap) / 4
    for i, (num, lab, sub) in enumerate(kpis):
        x = left + i * (kpi_w + kpi_gap)
        draw_rect(c, x, kpi_y, kpi_w, kpi_h, fill=LAVENDER)
        c.setFillColor(PURPLE_DEEP)
        c.setFont(FONT_BOLD, 14)
        c.drawString(x + 6, kpi_y + kpi_h - 18, num)
        c.setFillColor(INK)
        c.setFont(FONT_BOLD, 8)
        c.drawString(x + 6, kpi_y + kpi_h - 32, lab)
        c.setFillColor(GREY)
        c.setFont(FONT_ITALIC, 7)
        draw_wrapped(
            c,
            x + 6,
            kpi_y + kpi_h - 44,
            kpi_w - 12,
            sub,
            font=FONT_ITALIC,
            size=7,
            color=GREY,
            leading=9,
        )
    y = kpi_y - 0.18 * inch

    # ── Dogfood proof callout ────────────────────────────────────────────
    dog_h = 0.7 * inch
    draw_rect(c, left, y - dog_h, col_w, dog_h, fill=LAVENDER_DARK)
    draw_rect(c, left, y - dog_h, 3, dog_h, fill=PURPLE_DEEP)
    c.setFillColor(PURPLE_MID)
    c.setFont(FONT_BOLD, 7)
    c.drawString(left + 10, y - 14, "DOGFOOD PROOF · TODAY")
    msg = (
        "Our own senior-engineer agent, Ada, found a missing try/finally around a "
        "compliance-load-bearing audit trigger, drafted the fix, and shipped PR #263 — "
        "her tool calls signed by our own keys API, attested in our own audit log."
    )
    draw_wrapped(c, left + 10, y - 28, col_w - 20, msg, size=8.5, color=INK, leading=11)
    y -= dog_h + 0.1 * inch

    # ── Team strip ───────────────────────────────────────────────────────
    draw_eyebrow(c, left, y, "Founder")
    y -= 12
    c.setFillColor(PURPLE_DEEP)
    c.setFont(FONT_BOLD, 11)
    c.drawString(left, y, "Jeff Leva — Founder & CEO")
    # Columbia badge on the right
    c.setFillColor(PURPLE_MID)
    c.setFont(FONT_BOLD, 7)
    c.drawRightString(right, y + 3, "INCOMING · COLUMBIA BUSINESS SCHOOL CEO PROGRAM · JUNE 2026")
    y -= 14
    y = draw_wrapped(
        c,
        left,
        y,
        col_w,
        "12+ years operating production systems where ambiguity costs you — SRE on a cloud "
        "banking platform with $50B+ AUM at FIS (99.9% uptime, 30% toil reduction); program "
        "lead at Google driving a 6.6x latency reduction and a D- → A- operational turnaround; "
        "executive escalations at Sprint and British Telecom.",
        size=9,
        color=INK,
        leading=12,
    )
    y -= 8

    # ── The ask ──────────────────────────────────────────────────────────
    ask_h = 1.05 * inch
    ask_y = y - ask_h
    draw_rect(c, left, ask_y, col_w, ask_h, fill=PURPLE_DEEP)
    draw_rect(c, left, ask_y, 4, ask_h, fill=PURPLE_MID)
    c.setFillColor(LAVENDER)
    c.setFont(FONT_BOLD, 7.5)
    c.drawString(left + 12, ask_y + ask_h - 14, "THE ASK")
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 16)
    c.drawString(
        left + 12, ask_y + ask_h - 34, "$1.25M SAFE  ·  $8M post-money cap  ·  Range as the lead"
    )
    c.setFillColor(LAVENDER)
    c.setFont(FONT_REG, 9)
    use_y = ask_y + ask_h - 50
    use_y = draw_wrapped(
        c,
        left + 12,
        use_y,
        col_w - 24,
        "18 months on top of the existing ~20-month credit runway (true 38-month horizon). "
        "Use of funds: one senior engineer (mandate-service productization + partner onboarding), "
        "top-of-funnel ads & content (paid LinkedIn, sponsored newsletters, regulated-industry "
        "conferences), design-partner conversion engine, SOC 2 Type II prep.",
        size=8.5,
        color=LAVENDER,
        leading=11,
    )
    y = ask_y - 0.2 * inch

    # ── Footer ───────────────────────────────────────────────────────────
    draw_rect(c, 0, 0, PAGE_W, 0.5 * inch, fill=LAVENDER)
    c.setFillColor(PURPLE_DEEP)
    c.setFont(FONT_BOLD, 9)
    c.drawString(left, 0.3 * inch, "Jeff Leva  ·  Founder & CEO")
    c.setFillColor(INK)
    c.setFont(FONT_REG, 9)
    c.drawString(left, 0.16 * inch, "jeff@ai-identity.co  ·  ai-identity.co")
    c.setFillColor(GREY)
    c.setFont(FONT_ITALIC, 8)
    c.drawRightString(right, 0.3 * inch, "AI Identity  ·  Investor one-pager  ·  Range Ventures")
    c.drawRightString(right, 0.16 * inch, "May 12, 2026")

    c.showPage()
    c.save()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
