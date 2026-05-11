#!/usr/bin/env python3
"""Render an AI Identity whitepaper Markdown source to a publication-ready PDF.

Strips internal-only sections before rendering:
  * "## What to watch for" reviewer's note
  * "## Appendix B: Internal traceability"

Supports a small markdown subset sufficient for our whitepapers:
  headings, paragraphs, bold/italic inline, links, hyphen bullets, pipe tables,
  horizontal rules.

Usage:
    python3 scripts/render_whitepaper_pdf.py \
        marketing/whitepapers/2026-05-pqc-readiness-ai-identity.md
"""

from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Brand palette (AI Identity navy / ice / amber)
NAVY = colors.HexColor("#0B1F3A")
ICE = colors.HexColor("#4A8FBF")
ICE_SOFT = colors.HexColor("#A8D5F0")
AMBER = colors.HexColor("#F2A93B")
RULE = colors.HexColor("#C9CCD1")
MUTED = colors.HexColor("#5B6470")
BODY = colors.HexColor("#1A1F2A")


def make_styles() -> dict[str, ParagraphStyle]:
    body = ParagraphStyle(
        name="Body",
        fontName="Times-Roman",
        fontSize=10.5,
        leading=15,
        textColor=BODY,
        alignment=TA_LEFT,
        spaceAfter=8,
    )
    return {
        "Body": body,
        "Italic": ParagraphStyle("Italic", parent=body, fontName="Times-Italic"),
        "Lead": ParagraphStyle("Lead", parent=body, fontSize=11.5, leading=17, spaceAfter=14),
        "Subtitle": ParagraphStyle(
            "Subtitle",
            parent=body,
            fontName="Helvetica-Oblique",
            fontSize=12,
            textColor=MUTED,
            spaceAfter=6,
        ),
        "Title": ParagraphStyle(
            "Title",
            parent=body,
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=NAVY,
            spaceAfter=10,
        ),
        "H1": ParagraphStyle(
            "H1",
            parent=body,
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=NAVY,
            spaceBefore=18,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "H2": ParagraphStyle(
            "H2",
            parent=body,
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=NAVY,
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "H3": ParagraphStyle(
            "H3",
            parent=body,
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=NAVY,
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "Meta": ParagraphStyle(
            "Meta",
            parent=body,
            fontSize=9,
            textColor=MUTED,
            spaceAfter=2,
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=body,
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=NAVY,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=body,
            fontSize=9.5,
            leading=12,
        ),
        "Bullet": ParagraphStyle(
            "Bullet",
            parent=body,
            leftIndent=14,
            bulletIndent=2,
            spaceAfter=4,
        ),
    }


# ── Markdown → reportlab inline conversion ───────────────────────────────


def inline_md(text: str) -> str:
    """Convert a single line of inline markdown to reportlab rich-text XML."""
    # Code spans first (preserve verbatim)
    parts: list[str] = []
    last = 0
    for m in re.finditer(r"`([^`]+)`", text):
        parts.append(escape(text[last : m.start()]))
        parts.append(f'<font name="Courier" size="9.5">{escape(m.group(1))}</font>')
        last = m.end()
    parts.append(escape(text[last:]))
    text = "".join(parts)

    # Links [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<link href="{m.group(2)}" color="#4A8FBF"><u>{m.group(1)}</u></link>',
        text,
    )
    # Bold then italic
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![*])\*([^*\n]+)\*(?![*])", r"<i>\1</i>", text)
    return text


# ── Strip internal-only sections ─────────────────────────────────────────


INTERNAL_SECTION_HEADERS = {
    "## What to watch for",
    "## Appendix B: Internal traceability",
}


def strip_internal(md: str) -> str:
    out: list[str] = []
    skipping = False
    for line in md.splitlines():
        # Check for any internal header (match prefix to handle " (reviewer's note — strip before publication)")
        if line.startswith("## "):
            stripped = line.split("(")[0].strip()
            skipping = stripped in INTERNAL_SECTION_HEADERS
            if skipping:
                continue
        if not skipping:
            out.append(line)
    # Trim trailing rule + whitespace produced by stripping tail sections.
    while out and out[-1].strip() in ("", "---"):
        out.pop()
    return "\n".join(out) + "\n"


# ── Markdown block parser ────────────────────────────────────────────────


def parse_blocks(md: str) -> list[tuple[str, object]]:
    """Tokenise into a sequence of (kind, payload) blocks."""
    blocks: list[tuple[str, object]] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        # Blank
        if not line:
            i += 1
            continue

        # Horizontal rule
        if line.strip() == "---":
            blocks.append(("hr", None))
            i += 1
            continue

        # Headings
        m = re.match(r"^(#{1,3}) +(.*)$", line)
        if m:
            level = len(m.group(1))
            blocks.append((f"h{level}", m.group(2).strip()))
            i += 1
            continue

        # Tables (a line that starts with `|`, has a separator row of `|---|...|`)
        if (
            line.startswith("|")
            and i + 1 < len(lines)
            and re.match(r"^\s*\|[\s\-:|]+\|\s*$", lines[i + 1])
        ):
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row_line = lines[i].strip()
                if re.match(r"^\|[\s\-:|]+\|$", row_line):
                    i += 1
                    continue
                cells = [c.strip() for c in row_line.strip("|").split("|")]
                rows.append(cells)
                i += 1
            blocks.append(("table", rows))
            continue

        # Bullets
        if re.match(r"^[-*] +", line):
            items: list[str] = []
            while i < len(lines) and re.match(r"^[-*] +", lines[i].rstrip()):
                items.append(re.sub(r"^[-*] +", "", lines[i].rstrip()))
                i += 1
            blocks.append(("ul", items))
            continue

        # Paragraph (until blank line / heading / bullet / table / hr)
        para: list[str] = [line]
        i += 1
        while i < len(lines):
            nxt = lines[i].rstrip()
            if (
                not nxt
                or re.match(r"^(#{1,3}) ", nxt)
                or re.match(r"^[-*] ", nxt)
                or nxt.startswith("|")
                or nxt.strip() == "---"
            ):
                break
            para.append(nxt)
            i += 1
        blocks.append(("p", " ".join(para)))

    return blocks


# ── Render blocks → reportlab flowables ──────────────────────────────────


def render(blocks: list[tuple[str, object]], styles: dict[str, ParagraphStyle]):
    flow: list = []
    saw_title = False
    for kind, payload in blocks:
        if kind == "h1" and not saw_title:
            flow.append(Paragraph(inline_md(payload), styles["Title"]))
            saw_title = True
            continue
        if kind == "h1":
            flow.append(Paragraph(inline_md(payload), styles["H1"]))
        elif kind == "h2":
            flow.append(Paragraph(inline_md(payload), styles["H2"]))
        elif kind == "h3":
            flow.append(Paragraph(inline_md(payload), styles["H3"]))
        elif kind == "p":
            # Treat italic-only paragraphs as Lead/subtitle (rare; styled below).
            text = payload
            # Detect the subtitle block right after the title (single italic-wrapped sentence).
            if (
                len(flow) <= 3
                and text.startswith("*")
                and text.endswith("*")
                and not text.startswith("**")
            ):
                flow.append(Paragraph(inline_md(text), styles["Subtitle"]))
            else:
                flow.append(Paragraph(inline_md(text), styles["Body"]))
        elif kind == "ul":
            items = [
                ListItem(Paragraph(inline_md(t), styles["Bullet"]), leftIndent=14) for t in payload
            ]
            flow.append(
                ListFlowable(
                    items,
                    bulletType="bullet",
                    leftIndent=14,
                    bulletFontName="Helvetica",
                    bulletFontSize=8,
                )
            )
            flow.append(Spacer(1, 4))
        elif kind == "table":
            rows = payload
            data = []
            for ri, row in enumerate(rows):
                style = styles["TableHeader"] if ri == 0 else styles["TableCell"]
                data.append([Paragraph(inline_md(c), style) for c in row])
            tbl = Table(data, repeatRows=1, hAlign="LEFT")
            tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0F4F8")),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.75, NAVY),
                        ("LINEBELOW", (0, -1), (-1, -1), 0.5, RULE),
                        ("INNERGRID", (0, 1), (-1, -1), 0.25, RULE),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            flow.append(Spacer(1, 4))
            flow.append(tbl)
            flow.append(Spacer(1, 10))
        elif kind == "hr":
            flow.append(Spacer(1, 6))
            flow.append(HRFlowable(width="100%", thickness=0.5, color=RULE))
            flow.append(Spacer(1, 6))
    return flow


# ── Page chrome (header rule + footer page numbers) ──────────────────────


def make_page_chrome(doc_title: str):
    def _on_page(canvas, doc):
        canvas.saveState()
        # Footer
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            doc.leftMargin,
            0.5 * inch,
            doc_title,
        )
        canvas.drawRightString(
            LETTER[0] - doc.rightMargin,
            0.5 * inch,
            f"Page {doc.page}",
        )
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.25)
        canvas.line(
            doc.leftMargin,
            0.65 * inch,
            LETTER[0] - doc.rightMargin,
            0.65 * inch,
        )
        canvas.restoreState()

    return _on_page


# ── Main ─────────────────────────────────────────────────────────────────


def _doc_title_from_blocks(blocks: list[tuple[str, object]]) -> str:
    """Use the first H1 as the document title; fall back to a generic label."""
    for kind, payload in blocks:
        if kind == "h1" and isinstance(payload, str):
            return payload.strip()
    return "AI Identity Document"


def render_pdf(md_path: Path, pdf_path: Path | None = None) -> Path:
    md = md_path.read_text(encoding="utf-8")
    md = strip_internal(md)
    styles = make_styles()
    blocks = parse_blocks(md)
    flow = render(blocks, styles)

    title = _doc_title_from_blocks(blocks)
    footer_label = (
        f"AI Identity · {title}" if not title.lower().startswith("ai identity") else title
    )

    pdf_path = pdf_path or md_path.with_suffix(".pdf")
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=LETTER,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.85 * inch,
        title=title,
        author="AI Identity",
    )
    chrome = make_page_chrome(footer_label)
    doc.build(flow, onFirstPage=chrome, onLaterPages=chrome)
    return pdf_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: render_whitepaper_pdf.py <path-to-markdown> [<output-pdf>]")
    src = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
    result = render_pdf(src, out)
    print(f"wrote {result}")
