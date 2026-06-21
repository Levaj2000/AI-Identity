"""Human-readable PDF cover letter for compliance export bundles.

Every export ships machine-readable evidence (CSV + JSON) plus this
single ``compliance_report.pdf`` — the "report cover letter" the export
spec calls for (``docs/compliance/export-profiles.md`` §Format: "PDF for
human-readable narratives"). It is what an examiner prints, reads, and
files; the CSV/JSON underneath is what their tooling ingests.

The PDF is written into the bundle *before* ``seal()``, so its SHA-256
is enumerated in the DSSE-signed ``manifest.json`` like every other
artifact — i.e. the cover letter is itself tamper-evident.

``reportlab`` is imported lazily inside :func:`render_cover_letter_pdf`
so that merely importing ``common.compliance`` (e.g. from the gateway or
mandate services) does not require the PDF dependency — only the API
service that actually builds exports pulls it in.
"""

from __future__ import annotations

import datetime
import uuid  # noqa: TC003 — used at runtime in the signature
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# AI Identity Purple — matches the brand used across generated artifacts.
_PURPLE_DEEP = "#4B2D7F"
_PURPLE_MID = "#6B4FA0"
_LAVENDER = "#F0E8F8"
_INK = "#1A1F36"
_GREY = "#6B7280"
_LINE = "#E2E0EE"

# Machine profile id → examiner-facing framework name.
PROFILE_DISPLAY_NAMES = {
    "soc2_tsc_2017": "SOC 2 (Trust Services Criteria, 2017)",
    "eu_ai_act_2024": "EU AI Act (Regulation 2024/1689)",
    "nist_ai_rmf_1_0": "NIST AI Risk Management Framework 1.0",
}


def _fmt_ts(dt: datetime.datetime) -> str:
    """ISO-8601 UTC with a Z suffix — matches the export's date policy."""
    return dt.astimezone(datetime.UTC).strftime("%Y-%m-%d %H:%M:%SZ")


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def render_cover_letter_pdf(
    *,
    profile: str,
    org_id: uuid.UUID,
    export_id: uuid.UUID,
    audit_period_start: datetime.datetime,
    audit_period_end: datetime.datetime,
    built_at: datetime.datetime,
    signer_key_id: str,
    artifacts: Sequence[dict],
) -> bytes:
    """Render the cover letter to PDF bytes.

    ``artifacts`` is the bundle's own artifact list — each a dict with
    ``path``, ``controls`` (list[str]), and ``bytes`` (int). The manifest
    and this PDF are added after, so they are not in the list (the cover
    letter describes the *evidence*, not itself).
    """
    # Lazy import — see module docstring.
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    framework = PROFILE_DISPLAY_NAMES.get(profile, profile)

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "AIIH1",
        parent=styles["Heading1"],
        textColor=colors.HexColor(_PURPLE_DEEP),
        fontSize=20,
        spaceAfter=2,
    )
    kicker = ParagraphStyle(
        "AIIKicker",
        parent=styles["Normal"],
        textColor=colors.HexColor(_PURPLE_MID),
        fontSize=10,
        spaceAfter=14,
    )
    h2 = ParagraphStyle(
        "AIIH2",
        parent=styles["Heading2"],
        textColor=colors.HexColor(_PURPLE_DEEP),
        fontSize=12,
        spaceBefore=14,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "AIIBody",
        parent=styles["Normal"],
        textColor=colors.HexColor(_INK),
        fontSize=9.5,
        leading=14,
        alignment=TA_LEFT,
    )
    small = ParagraphStyle(
        "AIISmall",
        parent=styles["Normal"],
        textColor=colors.HexColor(_GREY),
        fontSize=8,
    )

    story: list = []
    story.append(Paragraph("AI IDENTITY · COMPLIANCE EVIDENCE EXPORT", kicker))
    story.append(Paragraph(framework, h1))
    story.append(Spacer(1, 10))

    # ── Metadata block ────────────────────────────────────────────────
    meta_rows = [
        ["Framework", framework],
        ["Organization", str(org_id)],
        ["Export ID", str(export_id)],
        [
            "Audit period",
            f"{_fmt_ts(audit_period_start)}  to  {_fmt_ts(audit_period_end)}",
        ],
        ["Generated", _fmt_ts(built_at)],
        ["Signing key", signer_key_id],
    ]
    meta_tbl = Table(meta_rows, colWidths=[1.5 * inch, 5.0 * inch])
    meta_tbl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor(_GREY)),
                ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor(_INK)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor(_LINE)),
            ]
        )
    )
    story.append(meta_tbl)

    # ── What this is ──────────────────────────────────────────────────
    story.append(Paragraph("About this export", h2))
    story.append(
        Paragraph(
            "This package contains tamper-evident evidence that AI Identity "
            f"governed this organization's AI agents over the period above, "
            f"mapped to <b>{framework}</b> controls. Every file listed below is "
            "enumerated in <font face='Courier'>manifest.json</font> with its "
            "SHA-256, and the manifest is sealed in a DSSE envelope "
            "(<font face='Courier'>manifest.dsse.json</font>) signed with the "
            "ECDSA P-256 key identified above. An auditor can verify the "
            "package offline — recompute each file's hash, then verify the "
            "manifest signature against the published public key — without "
            "contacting AI Identity.",
            body,
        )
    )

    # ── Evidence inventory ────────────────────────────────────────────
    story.append(Paragraph("Evidence included", h2))
    head = ["Artifact", "Controls", "Size"]
    table_rows = [head]
    for a in sorted(artifacts, key=lambda x: x["path"]):
        controls = ", ".join(a.get("controls") or []) or "—"
        table_rows.append(
            [
                Paragraph(a["path"], small),
                Paragraph(controls, small),
                _fmt_bytes(int(a.get("bytes", 0))),
            ]
        )
    art_tbl = Table(table_rows, colWidths=[2.7 * inch, 2.8 * inch, 0.9 * inch], repeatRows=1)
    art_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_PURPLE_DEEP)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#FFFFFF")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("FONTSIZE", (2, 1), (2, -1), 8),
                ("TEXTCOLOR", (2, 1), (2, -1), colors.HexColor(_GREY)),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(_LAVENDER)]),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor(_PURPLE_MID)),
            ]
        )
    )
    story.append(art_tbl)
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            f"{len(artifacts)} evidence artifact(s). See "
            "<font face='Courier'>manifest.json</font> for the authoritative "
            "list with SHA-256 digests and per-artifact control mappings.",
            small,
        )
    )

    story.append(Spacer(1, 18))
    story.append(
        Paragraph(
            "AI Identity · Compliance Evidence Export · Confidential — prepared "
            "for the named organization and its auditors.",
            small,
        )
    )

    buf = _BytesSink()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        leftMargin=0.8 * inch,
        rightMargin=0.8 * inch,
        title=f"AI Identity — {framework} Compliance Export",
        author="AI Identity",
    )
    doc.build(story)
    return buf.getvalue()


class _BytesSink:
    """Minimal file-like sink so reportlab writes into memory, not disk."""

    def __init__(self) -> None:
        self._chunks: list[bytes] = []

    def write(self, b: bytes) -> int:
        self._chunks.append(b)
        return len(b)

    def getvalue(self) -> bytes:
        return b"".join(self._chunks)
