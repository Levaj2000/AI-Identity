#!/usr/bin/env python3
"""Generate the shareable PDF of the cross-runtime agent visibility doc.

Source of truth: docs/strategy/cosai-ws4-cross-runtime-visibility.md
(reviewer's note already stripped; attestation_list shape). External-safe:
built for the Teryl/David (PayPal) CoSAI thread — no IBM-private material.
Embeds the companion diagram PNG so the file is self-contained.

Run: python3 docs/strategy/build_cross_runtime_visibility_pdf.py
"""

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DIR = "/Users/jeffleva/Dev/AI-Identity/docs/strategy"
OUT = f"{DIR}/cosai-ws4-cross-runtime-visibility.pdf"
DIAGRAM = f"{DIR}/cosai-ws4-cross-runtime-visibility.png"

PURPLE = colors.HexColor("#4B2D7F")
PURPLE_LT = colors.HexColor("#6B4FA0")
LAVENDER = colors.HexColor("#F0E8F8")
INK = colors.HexColor("#2b2b2b")
SUBTLE = colors.HexColor("#5a5a5a")
LINE = colors.HexColor("#d8d2e4")
CODE_BG = colors.HexColor("#241a38")
CODE_FG = colors.HexColor("#EDE7F8")

PAGE_W, PAGE_H = letter

styles = getSampleStyleSheet()
body = ParagraphStyle(
    "body",
    parent=styles["Normal"],
    fontName="Helvetica",
    fontSize=9.6,
    leading=14,
    textColor=INK,
    alignment=TA_LEFT,
    spaceAfter=6,
)
small = ParagraphStyle("small", parent=body, fontSize=8, textColor=SUBTLE, leading=11)
eyebrow = ParagraphStyle(
    "eyebrow",
    parent=body,
    fontName="Helvetica-Bold",
    fontSize=8.5,
    textColor=PURPLE_LT,
    spaceAfter=6,
)
h1 = ParagraphStyle(
    "h1",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=20,
    textColor=PURPLE,
    spaceAfter=2,
    leading=24,
)
tag = ParagraphStyle(
    "tag", parent=body, fontName="Helvetica-Bold", fontSize=11, textColor=INK, spaceAfter=2
)
meta = ParagraphStyle(
    "meta", parent=body, fontName="Helvetica-Oblique", fontSize=8.6, textColor=SUBTLE, spaceAfter=10
)
h2 = ParagraphStyle(
    "h2",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=13,
    textColor=PURPLE,
    spaceBefore=14,
    spaceAfter=5,
)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=4)
CODE = ParagraphStyle(
    "CODE", parent=styles["Code"], fontName="Courier", fontSize=7.6, textColor=CODE_FG, leading=10.6
)
cell = ParagraphStyle("cell", parent=body, fontSize=8.4, leading=11.4, spaceAfter=0)
cell_b = ParagraphStyle("cell_b", parent=cell, fontName="Helvetica-Bold", textColor=PURPLE)


def spaced(text):
    return "&nbsp;&nbsp;&nbsp;".join(" ".join(word) for word in text.split(" "))


def code_block(t):
    panel = Table([[Preformatted(t, CODE)]], colWidths=[7.0 * inch])
    panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("LINEBEFORE", (0, 0), (0, -1), 2.5, PURPLE_LT),
            ]
        )
    )
    return panel


def lav_box(text):
    box = Table([[Paragraph(text, body)]], colWidths=[7.1 * inch])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LAVENDER),
                ("LINEBEFORE", (0, 0), (0, -1), 3, PURPLE),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return box


def styled_table(rows, widths):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LAVENDER),
                ("LINEBELOW", (0, 0), (-1, 0), 0.9, PURPLE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
            + [("LINEBELOW", (0, i), (-1, i), 0.4, LINE) for i in range(1, len(rows))]
        )
    )
    return t


def _page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(PURPLE)
    canvas.rect(0, PAGE_H - 8, PAGE_W, 8, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(SUBTLE)
    canvas.drawString(
        0.7 * inch,
        0.42 * inch,
        "CROSS-RUNTIME AGENT VISIBILITY  ·  CoSAI WS4 TRUST GRAPH  ·  2026-07-16",
    )
    canvas.drawRightString(
        PAGE_W - 0.7 * inch, 0.42 * inch, f"AI IDENTITY · ai-identity.co · PAGE {doc.page}"
    )
    canvas.restoreState()


story = []
story.append(Paragraph(spaced("COSAI WS4 · TRUST GRAPH SIG"), eyebrow))
story.append(Paragraph("Cross-Runtime Agent Visibility", h1))
story.append(
    Paragraph(
        "When an agent enters a runtime you don't control, how do you still see what it's doing?",
        tag,
    )
)
story.append(
    Paragraph(
        "Companion to the WS4 Agent Identity &amp; Governance Interop Map · prompted by the "
        "Trust Graph SIG discussion on 2026-07-16 · draft for the work-stream · Jeff Leva, "
        "AI Identity",
        meta,
    )
)
story.append(HRFlowable(width="100%", color=LINE, thickness=0.8))
story.append(Spacer(1, 8))

story.append(Paragraph("The question", h2))
story.append(
    Paragraph(
        "An agent starts in an instrumented environment — your gateway, your policies, your "
        "telemetry. Then it crosses into another runtime: a hosted platform (Perplexity, a "
        "partner's orchestrator, a SaaS agent host), where it keeps acting. What visibility "
        "survives the crossing?",
        body,
    )
)
story.append(
    Paragraph(
        "This conversation tends to circle, and the reason is that “visibility” blends "
        "<b>three separable problems</b> with different owners, different standards, and — "
        "critically — different limits on what is achievable at all.",
        body,
    )
)

story.append(Paragraph("The three problems", h2))
rows = [
    [
        Paragraph("<b>#</b>", cell_b),
        Paragraph("<b>Problem</b>", cell_b),
        Paragraph("<b>Question it answers</b>", cell_b),
        Paragraph("<b>Interop-map layer</b>", cell_b),
        Paragraph("<b>Where it's being solved</b>", cell_b),
    ],
    [
        Paragraph("1", cell),
        Paragraph("<b>Authority continuity</b>", cell),
        Paragraph(
            "Is the agent on the far side still the same principal, acting under the "
            "same grant, with the same limits?",
            cell,
        ),
        Paragraph("2 — Authority / delegation", cell),
        Paragraph(
            "ODIS (Passport), CMF <font face='Courier'>delegation.chain</font>, "
            "SPIFFE-anchored identity; mandates with scoped limits",
            cell,
        ),
    ],
    [
        Paragraph("2", cell),
        Paragraph("<b>Correlation continuity</b>", cell),
        Paragraph("When records from both sides exist, how do they join into one thread?", cell),
        Paragraph("Cross-cutting plumbing", cell),
        Paragraph(
            "OpenTelemetry context propagation (W3C <font face='Courier'>traceparent"
            "</font> / baggage)",
            cell,
        ),
    ],
    [
        Paragraph("3", cell),
        Paragraph("<b>Emission &amp; evidence</b>", cell),
        Paragraph(
            "Do verifiable records of the far side's actions exist at all — and can two "
            "runtimes' records be stitched into one tamper-evident narrative?",
            cell,
        ),
        Paragraph("5 — Record / evidence", cell),
        Paragraph(
            "OCSF <font face='Courier'>record_integrity</font> profile (ocsf-schema PR #1661)", cell
        ),
    ],
]
story.append(styled_table(rows, [0.3 * inch, 1.25 * inch, 2.15 * inch, 1.25 * inch, 2.15 * inch]))
story.append(Spacer(1, 4))
story.append(
    Paragraph(
        "Before answering any “can we see into runtime X” question, it is worth asking which "
        "of the three is actually meant. They have very different answers.",
        body,
    )
)

story.append(Paragraph("The honest limit first", h2))
story.append(
    Paragraph(
        "<b>You cannot instrument a runtime you do not control.</b> If the foreign runtime emits "
        "nothing, no schema, trace header, or credential format fixes that. Problem 3 splits "
        "accordingly:",
        body,
    )
)
story.append(
    Paragraph(
        "<b>Emission is an adoption problem, not a standards problem.</b> What standards "
        "<i>can</i> do is make cooperation cheap and uniform: a runtime that opts in emits OCSF "
        "events and the records are immediately joinable with everyone else's.",
        bullet,
        bulletText="•",
    )
)
story.append(
    Paragraph(
        "<b>Evidence stitching is a standards problem</b> — and it now has a concrete answer "
        "(below).",
        bullet,
        bulletText="•",
    )
)

story.append(Paragraph("What is achievable unilaterally: boundary evidence", h2))
story.append(
    Paragraph(
        "Even when the far side is dark, the crossing itself happens on your side of the "
        "boundary, and it can be recorded with full fidelity:",
        body,
    )
)
story.append(
    Paragraph(
        "<b>At egress:</b> record the delegation event — which agent, into which runtime, under "
        "which grant, with which limits attached (scope, spend ceiling, expiry). The grant is a "
        "signed artifact, so the <i>terms</i> of the excursion are non-repudiable even if its "
        "interior is not observable.",
        bullet,
        bulletText="•",
    )
)
story.append(
    Paragraph(
        "<b>On return:</b> record what came back and reconcile it against the grant. Limit "
        "enforcement can bind at settlement even where it cannot bind at execution (this is the "
        "mandate pattern: monetary or scope authority that travels with the delegation and is "
        "checked when effects materialize).",
        bullet,
        bulletText="•",
    )
)
story.append(
    lav_box(
        "Boundary evidence is the guaranteed <b>floor</b> — the lower bound that holds with no "
        "dependency on the far side's cooperation, with cooperative emission as the upgrade path "
        "above it. It turns “we lost sight of the agent” into “we hold a verifiable record of "
        "exactly what authority left the building, when, and what returned.”"
    )
)
story.append(Spacer(1, 8))
story.append(Paragraph("Two bounds on that claim, stated plainly:", body))
story.append(
    Paragraph(
        "<b>It covers terms, not conduct.</b> What is non-repudiable at the floor is the "
        "<i>authority</i> under which the agent left — not what it did once outside. Conduct on "
        "the far side sits above the floor, and only cooperation puts it there.",
        bullet,
        bulletText="•",
    )
)
story.append(
    Paragraph(
        "<b>It covers crossings that traverse your boundary.</b> An agent reaching a foreign "
        "runtime by a path the gateway never sees produces no egress record. That is an "
        "enforcement gap rather than an evidence gap, but it is the honest edge of the word "
        "“guaranteed.”",
        bullet,
        bulletText="•",
    )
)

story.append(Paragraph("Where OCSF PR #1661 closes the stitching gap", h2))
story.append(
    Paragraph(
        "The <font face='Courier'>record_integrity</font> profile (merged into OCSF 1.9, 2026-07-17) "
        "gives cooperating runtimes a shared, verifiable evidence shape. Each event carries an "
        "<font face='Courier'>attestation_list</font> — an array of <font face='Courier'>"
        "attestation</font> objects, so independent attesters (the home gateway, the foreign "
        "runtime) each add their own. Three fields on each attestation are precisely the "
        "cross-runtime seam:",
        body,
    )
)
rows = [
    [
        Paragraph("<b>Primitive</b>", cell_b),
        Paragraph("<b>What it does across a runtime boundary</b>", cell_b),
    ],
    [
        Paragraph("<font face='Courier'>chain_uid</font>", cell),
        Paragraph(
            "Stable for the lifetime of the chain — it <b>survives the handoff</b>, so one "
            "query (<font face='Courier'>attestation_list[].chain_uid = X</font>) retrieves "
            "the full cross-runtime narrative from both stores",
            cell,
        ),
    ],
    [
        Paragraph("<font face='Courier'>authority_uid</font>", cell),
        Paragraph(
            "<b>Each runtime attests its own events</b> under its own authority identifier "
            "— the home gateway signs its records, the foreign runtime signs its records; a "
            "verifier checks each credential against the expected authority",
            cell,
        ),
    ],
    [
        Paragraph(
            "<font face='Courier'>prev_event</font> (<font face='Courier'>uid</font>, "
            "<font face='Courier'>type_uid</font>, <font face='Courier'>fingerprint</font>)",
            cell,
        ),
        Paragraph(
            "The first event emitted on the far side fingerprint-references the last event "
            "emitted before the crossing — <b>the seam itself is tamper-evident</b>: "
            "altering, substituting, or deleting either side of the handoff breaks the link",
            cell,
        ),
    ],
]
story.append(styled_table(rows, [1.9 * inch, 5.2 * inch]))
story.append(Spacer(1, 6))

story.append(
    Paragraph(
        "Sketch of a two-runtime chain (shape per the merged #1661 schema; a cross-runtime "
        "chain with per-runtime authorities is a usage pattern, not a prescribed mechanism):",
        body,
    )
)
story.append(
    code_block("""[
  {
    "metadata": { "uid": "aaa-...-001" },
    "attestation_list": [
      {
        "authority_uid": "home-gateway:evidence-anchor:org/...",
        "chain_uid": "89248f7f-...",
        "fingerprint": { "algorithm_id": 3, "serialization_id": 2, "value": "61ea..." },
        "signatures": [ "...home gateway signature..." ]
      }
    ]
  },
  {
    "metadata": { "uid": "bbb-...-002" },
    "attestation_list": [
      {
        "authority_uid": "foreign-runtime:agent-host:tenant/...",
        "chain_uid": "89248f7f-...",
        "fingerprint": { "algorithm_id": 3, "serialization_id": 2, "value": "bb47..." },
        "signatures": [ "...foreign runtime signature..." ],
        "prev_event": {
          "uid": "aaa-...-001",
          "type_uid": 600302,
          "fingerprint": { "algorithm_id": 3, "serialization_id": 2, "value": "61ea..." }
        }
      }
    ]
  }
]""")
)
story.append(Spacer(1, 4))
story.append(
    Paragraph(
        "Because <font face='Courier'>prev_event</font> sits <i>inside</i> the fingerprinted and "
        "signed content, deleting or altering an event in the chain breaks the fingerprint and "
        "signatures of the event that references it — on either side of the boundary.",
        body,
    )
)

# ---- diagram ----
img = Image(DIAGRAM, width=7.1 * inch, height=7.1 * inch * 1980 / 3520)
story.append(Spacer(1, 6))
story.append(
    KeepTogether(
        [
            Paragraph("The picture", h2),
            img,
            Paragraph(
                "Companion diagram — the three lanes crossing the trust boundary, with the "
                "tamper-evident seam and the dark-runtime fallback.",
                small,
            ),
        ]
    )
)

story.append(Paragraph("How the lanes compose (nobody owns all three)", h2))
rows = [
    [
        Paragraph("<b>Lane</b>", cell_b),
        Paragraph("<b>Standard / effort</b>", cell_b),
        Paragraph("<b>Contribution to the crossing</b>", cell_b),
    ],
    [
        Paragraph("Authority", cell),
        Paragraph("ODIS Passport, CMF <font face='Courier'>delegation.chain</font>, SPIFFE", cell),
        Paragraph("The grant travels with the agent as a signed artifact", cell),
    ],
    [
        Paragraph("Correlation", cell),
        Paragraph("OpenTelemetry (W3C <font face='Courier'>traceparent</font>, baggage)", cell),
        Paragraph("The thread that lets two record sets be joined after the fact", cell),
    ],
    [
        Paragraph("Environment trust", cell),
        Paragraph("Hardware / workload attestation (TEE)", cell),
        Paragraph(
            "Raises confidence in a <i>cooperating</i> foreign runtime's interior claims", cell
        ),
    ],
    [
        Paragraph("Enforcement", cell),
        Paragraph("Runtime policy engines (e.g. CPEX/APL)", cell),
        Paragraph("Decides at the boundary and, where deployed, on the far side", cell),
    ],
    [
        Paragraph("Record / evidence", cell),
        Paragraph("OCSF <font face='Courier'>record_integrity</font> (#1661)", cell),
        Paragraph("The durable, independently verifiable narrative both sides emit into", cell),
    ],
]
story.append(styled_table(rows, [1.3 * inch, 2.6 * inch, 3.2 * inch]))

story.append(Paragraph("Where AI Identity fits", h2))
story.append(
    Paragraph(
        "AI Identity operates at the record/evidence layer as a <b>running reference "
        "implementation</b> of the pattern above — the items below are shipped and demonstrable, "
        "not proposed:",
        body,
    )
)
story.append(
    Paragraph(
        "<b>Gateway emitter</b>: produces signed OCSF events at the boundary (the “boundary "
        "evidence” floor), with write-time hash chaining and export-time per-event signatures.",
        bullet,
        bulletText="•",
    )
)
story.append(
    Paragraph(
        "<b>Offline verifier CLI</b>: any third party verifies a chain — including a "
        "cross-runtime one — with no dependency on the producer's infrastructure (current shared "
        "bundle: 174/174 signatures verify against the published JWKS).",
        bullet,
        bulletText="•",
    )
)
story.append(
    Paragraph(
        "<b>Evidence Anchor</b>: signed Merkle checkpoints with per-event inclusion proofs over "
        "event sets — the checkpoint construct for summarizing a chain (or a cross-runtime "
        "excursion) at close.",
        bullet,
        bulletText="•",
    )
)
story.append(
    Paragraph(
        "<b>Mandate Service</b>: scoped monetary authority attached to a delegation, enforced at "
        "execution or settlement — the concrete form of “limits that survive loss of "
        "visibility.”",
        bullet,
        bulletText="•",
    )
)
story.append(
    Paragraph(
        "The schema seam these implement is the same one contributed upstream in PR #1661, so "
        "the pattern is portable: any runtime can emit it, any verifier can check it, and no "
        "part of it is proprietary to AI Identity.",
        body,
    )
)

story.append(Paragraph("Suggested framing for the SIG", h2))
story.append(
    Paragraph(
        "1. Split every “visibility into runtime X” question into authority / correlation / "
        "emission before debating it.",
        bullet,
    )
)
story.append(
    Paragraph(
        "2. Standardize the <b>seam</b> (grant format, trace propagation, evidence shape) — "
        "don't try to standardize the interior of runtimes we don't control.",
        bullet,
    )
)
story.append(
    Paragraph(
        "3. Treat <b>boundary evidence as the guaranteed floor</b> and cooperative emission as "
        "the upgrade path.",
        bullet,
    )
)

story.append(Spacer(1, 10))
story.append(HRFlowable(width="100%", color=LINE, thickness=0.6))
story.append(Spacer(1, 3))
story.append(
    Paragraph(
        "Draft for the CoSAI WS4 Trust Graph work-stream · descriptive, not evaluative — "
        "corrections welcome, each effort owns its own lane · Jeff Leva · jeff@ai-identity.co · "
        "ocsf-schema PR #1661: github.com/ocsf/ocsf-schema/pull/1661",
        small,
    )
)

doc = SimpleDocTemplate(
    OUT,
    pagesize=letter,
    leftMargin=0.7 * inch,
    rightMargin=0.7 * inch,
    topMargin=0.65 * inch,
    bottomMargin=0.7 * inch,
    title="Cross-Runtime Agent Visibility — CoSAI WS4 Trust Graph",
    author="Jeff Leva · AI Identity",
)
doc.build(story, onFirstPage=_page, onLaterPages=_page)
print(f"wrote {OUT}")
