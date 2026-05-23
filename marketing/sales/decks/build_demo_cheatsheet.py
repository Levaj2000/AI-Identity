"""Build the AI Identity demo cheat-sheet.

A founder-facing punchcard for live demos with investors and design partners.
Three high-value demos, exact clicks/commands, minimum talking points. Print
or open on a second monitor during the call.

Run: python3 build_demo_cheatsheet.py
Output: ../ai-identity-demo-cheatsheet.pdf
"""

from __future__ import annotations

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
ACCENT_AMBER = HexColor("#B5781A")

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"
FONT_MONO = "Courier"
FONT_MONO_BOLD = "Courier-Bold"

OUT = Path(__file__).resolve().parent.parent / "ai-identity-demo-cheatsheet.pdf"

PAGE_W, PAGE_H = letter


# ── Helpers ──────────────────────────────────────────────────────────────


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


def eyebrow(c, x, y, text, color=PURPLE_MID):
    c.setFillColor(color)
    c.setFont(FONT_BOLD, 7.5)
    c.drawString(x, y, text.upper())


def numbered_circle(c, x, y, diam, number, color=PURPLE_DEEP):
    c.setFillColor(color)
    c.circle(x + diam / 2, y + diam / 2, diam / 2, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 8)
    txt = str(number)
    tw = c.stringWidth(txt, FONT_BOLD, 8)
    c.drawString(x + (diam - tw) / 2, y + diam / 2 - 2.8, txt)


def header_bar(c, title, subtitle):
    bar_h = 0.55 * inch
    draw_rect(c, 0, PAGE_H - bar_h, PAGE_W, bar_h, fill=PURPLE_DEEP)
    draw_rect(c, 0, PAGE_H - 8, PAGE_W, 8, fill=PURPLE_MID)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 16)
    c.drawString(0.5 * inch, PAGE_H - 0.36 * inch, title)
    # Subtitle right-aligned to avoid colliding with the title
    c.setFillColor(LAVENDER)
    c.setFont(FONT, 10)
    c.drawRightString(PAGE_W - 0.5 * inch, PAGE_H - 0.36 * inch, subtitle)


def footer_bar(c, label, page_n, total):
    draw_rect(c, 0, 0, PAGE_W, 0.35 * inch, fill=LAVENDER)
    c.setFillColor(PURPLE_DEEP)
    c.setFont(FONT_BOLD, 8)
    c.drawString(0.5 * inch, 0.16 * inch, label)
    c.setFillColor(GREY)
    c.setFont(FONT, 8)
    c.drawRightString(PAGE_W - 0.5 * inch, 0.16 * inch, f"{page_n} / {total}")


def step(c, x, y, w, num, text):
    """Numbered step with wrapped text. Returns the new y cursor."""
    diam = 14
    numbered_circle(c, x, y - 11, diam, num)
    new_y = wrapped(c, x + diam + 6, y - 6, w - diam - 6, text, size=10, color=INK, leading=13)
    return new_y - 2


def code_block(c, x, y, w, lines, *, fill=LAVENDER_DARK):
    """Render a monospaced code block. Returns new y cursor."""
    line_h = 11
    pad_top = 6
    pad_bot = 4
    h = pad_top + line_h * len(lines) + pad_bot
    draw_rect(c, x, y - h, w, h, fill=fill)
    draw_rect(c, x, y - h, 3, h, fill=PURPLE_DEEP)
    c.setFillColor(INK)
    c.setFont(FONT_MONO, 8.5)
    ty = y - pad_top - 8
    for ln in lines:
        c.drawString(x + 8, ty, ln)
        ty -= line_h
    return y - h - 4


def punchline(c, x, y, w, text, *, color=PURPLE_DEEP):
    """Single bold sentence — the only thing they actually say out loud.

    Box height scales with wrapped text length so it never overflows into
    the next section. Estimated using avg char width at 10pt bold.
    """
    # Estimate line count from text width vs available width inside the box.
    # Bold Helvetica at 10pt: avg char width ~5.5pt. Inner width = w - 20.
    inner_w = w - 20
    avg_char_w = 5.5
    chars_per_line = max(1, int(inner_w / avg_char_w))
    import math

    lines = max(1, math.ceil(len(text) / chars_per_line))
    line_h = 12
    pad_top = 20  # space for eyebrow above the text
    pad_bot = 8
    h = pad_top + lines * line_h + pad_bot
    draw_rect(c, x, y - h, w, h, fill=LAVENDER)
    draw_rect(c, x, y - h, 3, h, fill=color)
    eyebrow(c, x + 10, y - 13, "SAY (verbatim or close)")
    wrapped(c, x + 10, y - 27, inner_w, text, font=FONT_BOLD, size=10, color=color, leading=line_h)
    return y - h - 6


def main():
    c = canvas.Canvas(str(OUT), pagesize=letter)
    c.setTitle("AI Identity — Demo Cheat-sheet")
    c.setAuthor("Jeff Leva")
    c.setSubject("Live demo punchcard · Friday 2026-05-15")

    left = 0.5 * inch
    right = PAGE_W - 0.5 * inch
    col_w = right - left
    total_pages = 2

    # ── PAGE 1 ───────────────────────────────────────────────────────────
    header_bar(c, "Demo cheat-sheet", "AI Identity · Friday 2026-05-15")
    y = PAGE_H - 0.55 * inch - 0.3 * inch

    # Preflight checklist
    eyebrow(c, left, y, "Preflight · before you join the call")
    y -= 14
    preflight = [
        "Refresh the evidence pack — see command at the bottom of this page",
        "Two browser tabs open: dashboard.ai-identity.co/dashboard/agents AND .../forensics",
        "Forensics tab pre-set: Agent = ada, From = 05/03 12:00 AM, To = 05/05 12:00 AM, Decision = All",
        "Close every other tab and chat window. Browser zoom 110%.",
        "Deck + one-pager + proof PDF open in a fourth tab as fallback.",
    ]
    for i, item in enumerate(preflight, 1):
        y = step(c, left, y, col_w, i, item)
    y -= 6

    # ── DEMO 1 ───────────────────────────────────────────────────────────
    eyebrow(c, left, y, "Demo 1 · Agent identity · 30 sec · low risk", color=ACCENT_GREEN)
    y -= 14
    c.setFillColor(PURPLE_DEEP)
    c.setFont(FONT_BOLD, 13)
    c.drawString(left, y, "Ada is a real, authenticated agent — not a service account.")
    y -= 18

    demo1 = [
        "Share screen on the Agents tab.",
        "Click `ada` in the agents list → opens her detail page.",
        "Point at: agent_id (UUID), status = active, key fingerprint, created_at.",
    ]
    for i, item in enumerate(demo1, 1):
        y = step(c, left, y, col_w, i, item)
    y = punchline(
        c,
        left,
        y,
        col_w,
        "\"This is Ada's signed, revocable, rotatable identity — not a shared key in someone's .env file.\"",
    )

    # ── DEMO 2 (starts on page 1, the headline demo) ─────────────────────
    eyebrow(c, left, y, "Demo 2 · Forensics chain · 3 min · the headline", color=PURPLE_DEEP)
    y -= 14
    c.setFillColor(PURPLE_DEEP)
    c.setFont(FONT_BOLD, 13)
    c.drawString(left, y, "Every decision the gateway made for Ada — cryptographically chained.")
    y -= 18

    demo2 = [
        'Switch to Forensics tab. Point at "Hash Chain (N entries) ✓ Verified" header.',
        "Set Decision filter → Denied. Re-run. List collapses from 18 events to 1.",
        "Click the deny row. Event Detail drawer opens.",
        "Point at three fields (in this order): deny_reason = no_active_policy · entry_hash · prev_hash.",
    ]
    for i, item in enumerate(demo2, 1):
        y = step(c, left, y, col_w, i, item)
    y = punchline(
        c,
        left,
        y,
        col_w,
        "\"Each row's hash is computed over the row plus the previous row's hash — the same primitive Git uses. Editing any field anywhere in the chain breaks verification.\"",
    )

    # ── Evidence pack reference (bottom of page 1) ───────────────────────
    eyebrow(c, left, y, "Evidence pack · in marketing/sales/")
    y -= 14
    artifacts = [
        ("range-ventures-deck-2026-05-12.pdf", "13-slide investor narrative. Already sent."),
        (
            "range-ventures-one-pager-2026-05-12.pdf",
            "Single-page tear-sheet for partner forwarding. Already sent.",
        ),
        (
            "ada-dogfood-proof-2026-05-12.pdf",
            "2-page audit-trail evidence pack. Forward when an evaluator asks for proof.",
        ),
        (
            "ada-audit-snapshot-2026-05-12.csv",
            "20 rows, full hashes. Forward to analysts who want to filter and sort.",
        ),
        (
            "ada-audit-snapshot-2026-05-12.json",
            "Same data, machine-readable. For their offline verifier.",
        ),
        ("ada-chain-verify-2026-05-12.json", "Live chain-integrity verdict. Bundle with the JSON."),
    ]
    c.setFont(FONT, 8.5)
    for fname, desc in artifacts:
        c.setFillColor(PURPLE_DEEP)
        c.setFont(FONT_MONO_BOLD, 8)
        c.drawString(left, y, fname)
        c.setFillColor(GREY)
        c.setFont(FONT, 8.5)
        c.drawString(left + 230, y, "— " + desc)
        y -= 11
    y -= 4

    # Refresh command — runnable, copyable
    eyebrow(c, left, y, "Refresh evidence Friday morning")
    y -= 14
    y = code_block(
        c,
        left,
        y,
        col_w,
        [
            "$ cd /Users/jeffleva/Dev/AI-Identity",
            '$ AI_IDENTITY_ADMIN_KEY="levaj2000@gmail.com" \\',
            "    .venv/bin/python marketing/sales/decks/refresh_ada_evidence.py",
        ],
    )

    footer_bar(c, "AI Identity  ·  Demo cheat-sheet  ·  do not share externally", 1, total_pages)
    c.showPage()

    # ── PAGE 2 ───────────────────────────────────────────────────────────
    header_bar(c, "Demo cheat-sheet", "page 2 · optional close + safety net")
    y = PAGE_H - 0.55 * inch - 0.3 * inch

    # Closing move — describe-only, no Terminal
    eyebrow(c, left, y, "Closing move · 30 sec · describe-only, no Terminal", color=PURPLE_DEEP)
    y -= 14
    c.setFillColor(PURPLE_DEEP)
    c.setFont(FONT_BOLD, 13)
    c.drawString(left, y, "The math actually works — and you don't need to trust us.")
    y -= 16
    c.setFillColor(GREY)
    c.setFont(FONT_ITALIC, 9)
    c.drawString(
        left,
        y,
        'The dashboard\'s "Hash Chain ✓ Verified" badge already shows the chain math passing server-side. No need to re-run it live.',
    )
    y -= 14

    closing = [
        'Stay in the Event Detail drawer. Point at "Export Entry as JSON" and "Download Verify Script" buttons.',
        'Read the line under them aloud: "python3 ai_identity_verify.py chain <exported-file>.json".',
        "Then deliver the line below — and DO NOT switch to Terminal live.",
    ]
    for i, item in enumerate(closing, 1):
        y = step(c, left, y, col_w, i, item)
    y -= 2
    y = punchline(
        c,
        left,
        y,
        col_w,
        '"Your security team can run this on an airgapped laptop and get the same VERIFIED verdict — zero trust in this dashboard. I\'ll send the script and a chain export after this call."',
    )

    # Safety net — what to do if something breaks
    eyebrow(c, left, y, "If something breaks live", color=ACCENT_RED)
    y -= 14
    failsafes = [
        (
            "Dashboard slow / won't load",
            'Stop sharing, smile, say "my home internet is being scrappy — let me pull up the static evidence pack instead." Open the dogfood-proof PDF. Same story, same proof.',
        ),
        (
            "Filter shows zero events",
            "Don't panic. Look at the KPI cards — they tell you what's actually there. If TOTAL EVENTS = N > 0, widen the date range. Avoid touching Action Type.",
        ),
        (
            "They ask about the offline verifier",
            "Don't try to demo it. Say: \"Three clicks — export entry, download script, run python3 verify.py chain export.json on an airgapped laptop. I'll send everything you need after this call.\" Move on.",
        ),
        (
            "AI summary panel disagrees with KPIs",
            "Don't open it. It has a known bug in the aggregate counts. Stay on the raw event data.",
        ),
    ]
    for title, body in failsafes:
        c.setFillColor(PURPLE_DEEP)
        c.setFont(FONT_BOLD, 10)
        c.drawString(left, y, title)
        y -= 13
        y = wrapped(c, left + 8, y, col_w - 8, body, size=9.5, color=INK, leading=12)
        y -= 4
    y -= 4

    # Practice plan
    eyebrow(c, left, y, "Tonight · practice plan")
    y -= 14
    practice = [
        "Run Demo 1 + Demo 2 end-to-end three times. Time yourself; should land 4 min total.",
        'Practice the closing line verbatim. "Your security team can run this offline" — say it like you mean it. Don\'t open Terminal.',
        "Refresh evidence pack tomorrow morning (see command on page 1). Verify all four artifacts updated.",
        "Pick ONE sentence from this card you'll deliver verbatim. The rest, your own words.",
    ]
    for i, item in enumerate(practice, 1):
        y = step(c, left, y, col_w, i, item)

    footer_bar(c, "AI Identity  ·  Demo cheat-sheet  ·  do not share externally", 2, total_pages)
    c.showPage()
    c.save()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
