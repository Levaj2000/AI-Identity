"""Render the Evidence Anchor reference-implementation notes as an AI Identity Purple PDF.

Clean, externally-shareable version (the internal reviewer note in the .md is
intentionally omitted here). Source: docs/forensics/evidence-anchor-reference-notes.md
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
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

DEEP = colors.HexColor("#4B2D7F")
LIGHT = colors.HexColor("#6B4FA0")
LAVENDER = colors.HexColor("#F0E8F8")
CODEBG = colors.HexColor("#F6F2FB")
INK = colors.HexColor("#2A2A33")
GRAY = colors.HexColor("#6B6B78")
WHITE = colors.white

OUT = "marketing/partner/ai-identity-evidence-anchor-reference-notes.pdf"
DOCNAME = "Evidence Anchor — Reference Notes"
DATE = "June 23, 2026"
ss = getSampleStyleSheet()


def mkstyle(name, **kw):
    base = kw.pop("parent", ss["Normal"])
    return ParagraphStyle(name, parent=base, **kw)


body = mkstyle(
    "body", fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=INK, spaceAfter=6
)
eyebrow = mkstyle("eyebrow", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=LIGHT)
h1 = mkstyle("h1", fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=DEEP, spaceAfter=4)
h2 = mkstyle(
    "h2",
    fontName="Helvetica-Bold",
    fontSize=11.5,
    leading=15,
    textColor=DEEP,
    spaceBefore=11,
    spaceAfter=3,
)
code = mkstyle("code", fontName="Courier", fontSize=7.6, leading=9.8, textColor=INK)
cell = mkstyle("cell", fontName="Helvetica", fontSize=8.4, leading=11, textColor=INK)
cellb = mkstyle("cellb", parent=cell, fontName="Courier", textColor=DEEP)
cellh = mkstyle("cellh", fontName="Helvetica-Bold", fontSize=8.4, leading=11, textColor=WHITE)
cover_title = mkstyle("ct", fontName="Helvetica-Bold", fontSize=25, leading=29, textColor=WHITE)
cover_sub = mkstyle(
    "cs", fontName="Helvetica", fontSize=12.5, leading=17, textColor=colors.HexColor("#D9CCEC")
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


def _bodypage(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DEEP)
    canvas.rect(0, letter[1] - 7, letter[0], 7, stroke=0, fill=1)
    canvas.restoreState()
    _footer(canvas, doc)


def _coverpage(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DEEP)
    canvas.rect(0, 0, letter[0], letter[1], stroke=0, fill=1)
    canvas.setFillColor(LIGHT)
    canvas.rect(0, 0, 14, letter[1], stroke=0, fill=1)
    canvas.restoreState()


def codeblock(text, width=7.0):
    pre = Preformatted(text, code)
    t = Table([[pre]], colWidths=[width * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CODEBG),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9CCEC")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def callout(html):
    t = Table([[Paragraph(html, mkstyle("co", parent=body, spaceAfter=0))]], colWidths=[7.0 * inch])
    t.setStyle(
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
    return t


def field_table(rows):
    data = [[Paragraph("Field", cellh), Paragraph("Meaning", cellh)]]
    for k, v in rows:
        data.append([Paragraph(k, cellb), Paragraph(v, cell)])
    t = Table(data, colWidths=[1.9 * inch, 5.1 * inch], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, 0), DEEP),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LAVENDER]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#DAD0EC")),
            ]
        )
    )
    return t


story = []

# Cover
story += [
    NextPageTemplate("body"),
    Spacer(1, 2.5 * inch),
    Paragraph(
        "REFERENCE IMPLEMENTATION  ·  FORENSIC EVIDENCE",
        mkstyle("ce", parent=eyebrow, textColor=colors.HexColor("#C9B6E8")),
    ),
    Spacer(1, 10),
    Paragraph("Evidence Anchor", cover_title),
    Spacer(1, 6),
    Paragraph("Public-key-verifiable inclusion proofs for OCSF audit events", cover_sub),
    Spacer(1, 0.6 * inch),
    Paragraph("Prepared for &nbsp;·&nbsp; OCSF data-storage-patterns discussion", cover_meta),
    Paragraph(f"Date &nbsp;·&nbsp; {DATE}", cover_meta),
    Paragraph(
        "Scope &nbsp;·&nbsp; Public-safe: checkpoint format + offline verifier "
        "(as shipped in Case File bundles)",
        cover_meta,
    ),
    PageBreak(),
]

# Page 2
story += [
    Paragraph("EVIDENCE ANCHOR  ·  WHY IT'S RELEVANT HERE", eyebrow),
    Spacer(1, 3),
    Paragraph("Integrity verification that reads no storage at all.", h1),
    Spacer(1, 6),
    callout(
        "<b>Relevance to the storage debate:</b> verification reads <i>no database and no "
        "storage layout</i> — only an exported signed checkpoint and a proof. So how you store "
        "OCSF events (one wide table vs. per-class / per-source tables) is <b>orthogonal</b> to "
        "how you prove them. Choose storage purely on query performance."
    ),
    Spacer(1, 8),
    Paragraph("1 · The problem it solves", h2),
    Paragraph(
        "Our OCSF audit events form a per-org, append-only <b>hash chain</b>: each event carries "
        "a per-event hash (<font face='Courier'>entry_hash</font>) over its canonical record and "
        "the prior event's hash. That gives tamper-evidence, but independent verification of a "
        "single event is awkward — proving one event means re-walking the chain from a trusted "
        "tip (<b>O(N)</b>), and the chain hash is <b>keyed</b> (secret-dependent), so the only "
        "party who can recompute it is one you'd also trust to forge it.",
        body,
    ),
    Paragraph("2 · The anchor (design in one paragraph)", h2),
    Paragraph(
        "A scheduled worker batches the per-event <font face='Courier'>entry_hash</font> values "
        "and builds a <b>Merkle tree (RFC 6962)</b>, then signs the <b>root once</b> with "
        "<b>ECDSA-P256</b> in a <b>DSSE</b> envelope; the public key is published via <b>JWKS</b>. "
        "A signed checkpoint commits an entire batch; any single event gets an "
        "<b>O(log N) inclusion proof</b> verifiable with <b>only SHA-256 + the public key</b> — "
        "no database, no shared secret. It is a verification layer on top of the chain.",
        body,
    ),
    Spacer(1, 2),
    codeblock(
        "events --> entry_hash[] --> Merkle tree (RFC 6962) --> root\n"
        "                                                       |  sign once (ECDSA-P256, DSSE, JCS)\n"
        "                                                       v\n"
        "                                             signed checkpoint --> JWKS public key\n"
        "\n"
        "verify 1 event:  SHA-256(proof) + ECDSA(pubkey) = committed?   (O(log N), offline)"
    ),
    PageBreak(),
]

# Page 3 — formats
story += [
    Paragraph("FORMATS  ·  CHECKPOINT + INCLUSION PROOF", eyebrow),
    Spacer(1, 3),
    Paragraph("The signed checkpoint and the proof", h1),
    Spacer(1, 6),
    Paragraph("3 · Signed checkpoint (MerkleCheckpointV1)", h2),
    Paragraph(
        "Payload is JSON, canonicalized with <b>RFC 8785 (JCS)</b>, wrapped in a <b>DSSE</b> "
        "envelope. Signature is over <font face='Courier'>PAE(payloadType, payload)</font> "
        "(length-prefixed domain separation).",
        body,
    ),
    field_table(
        [
            ("schema_version", "1 — verifiers reject unknown versions"),
            ("org_id", "tenant whose chain the batch was drawn from (per-org root)"),
            ("tree_size", "number of leaves (events) under the root"),
            ("merkle_root", "SHA-256 hex of the RFC 6962 root over the batch's entry_hashes"),
            ("first/last_audit_id", "inclusive id range of the committed batch"),
            ("signed_at", "RFC 3339 (Z) signing time"),
            ("signer_key_id", "KMS key-version resource path; pins the key across rotations"),
        ]
    ),
    Spacer(1, 5),
    Paragraph("<b>checkpoints.json</b> entry:", body),
    codeblock(
        "{\n"
        '  "merkle_root": "<sha256-hex>",\n'
        '  "envelope": {\n'
        '    "payloadType": "application/vnd.ai-identity.anchor-checkpoint+json",\n'
        '    "payload": "<base64(JCS-canonical checkpoint JSON)>",\n'
        '    "signatures": [{ "keyid": "<signer_key_id>",\n'
        '                     "sig": "<base64(DER ECDSA-P256)>" }]\n'
        "  }\n"
        "}"
    ),
    Spacer(1, 6),
    Paragraph("4 · inclusion-proofs.json", h2),
    codeblock(
        "{\n"
        '  "proofs": [\n'
        '    { "audit_id": 84213,\n'
        '      "entry_hash": "<sha256-hex>",     // the leaf value\n'
        '      "index": 17,                       // position in the tree\n'
        '      "tree_size": 256,\n'
        '      "merkle_root": "<sha256-hex>",     // which checkpoint it proves against\n'
        '      "proof": ["<sha256-hex>", "..."]   // RFC 6962 audit path, ~log2(N) hashes\n'
        "    }\n"
        "  ],\n"
        '  "pending": [ /* exported events not yet anchored to a checkpoint */ ]\n'
        "}"
    ),
    Spacer(1, 4),
    Paragraph(
        "A multi-class incident is simply <b>N entries in <font face='Courier'>proofs</font></b> "
        "— one O(log N) inclusion proof per event. <font face='Courier'>pending</font> makes "
        "coverage explicit for events newer than the last checkpoint.",
        body,
    ),
    PageBreak(),
]

# Page 4 — verification + scope
story += [
    Paragraph("VERIFICATION  ·  OFFLINE, ANY LANGUAGE", eyebrow),
    Spacer(1, 3),
    Paragraph("What an outside verifier actually runs", h1),
    Spacer(1, 6),
    Paragraph("5 · Bundle layout", h2),
    codeblock(
        "evidence-anchor/\n"
        "  checkpoints.json        # signed checkpoints (DSSE envelopes)\n"
        "  inclusion-proofs.json   # per-event proofs + pending list"
    ),
    Spacer(1, 6),
    Paragraph("6 · Offline verification (RFC 6962)", h2),
    codeblock(
        "leaf_hash(d)    = SHA-256(0x00 || d)        # d = bytes.fromhex(entry_hash)\n"
        "node_hash(l, r) = SHA-256(0x01 || l || r)"
    ),
    Spacer(1, 4),
    Paragraph(
        "Two offline steps: <b>(1)</b> verify the DSSE/ECDSA-P256 checkpoint signature with the "
        "JWKS public key and bind the signed root to the proof's root; <b>(2)</b> run the RFC 6962 "
        "§2.1.1 audit-path check — fold <font face='Courier'>leaf_hash(entry_hash)</font> up "
        "through the proof and confirm it equals <font face='Courier'>merkle_root</font>. "
        "O(log N), SHA-256 only.",
        body,
    ),
    Paragraph(
        "The reference verifier ships inside every bundle (Python stdlib + cryptography; no "
        "network, no DB, no secret):",
        body,
    ),
    codeblock(
        "ai_identity_verify inclusion-proof \\\n"
        "  --checkpoints evidence-anchor/checkpoints.json \\\n"
        "  --proofs      evidence-anchor/inclusion-proofs.json \\\n"
        "  --jwks        ai-identity-public-keys.json     # or --pubkey signer.pem\n"
        "# -> INCLUSION VERIFIED - N event(s) provably committed."
    ),
    Spacer(1, 8),
    Paragraph("7 · Why it matters for storage patterns", h2),
    Paragraph(
        "The verification path touches <b>no storage</b> — not the table layout, not an index, "
        "not a join. So single-wide-table vs. per-class/per-source is independent of integrity "
        "verification; splitting tables for query performance does not weaken proof-of-custody. "
        "It does <b>not</b> make multi-table queries faster — it's orthogonal — but it removes "
        "integrity verification as a <i>constraint</i> on the storage decision.",
        body,
    ),
    Paragraph("8 · Scope — what it does and doesn't claim", h2),
]
for li in [
    "<b>Does:</b> prove inclusion + integrity of each event (committed under a signed root, "
    "untampered), independently, with a public key, O(log N) per event.",
    "<b>Doesn't:</b> by itself attest the causal <i>ordering</i> between events — that linkage is the "
    "underlying hash chain. A multi-class incident is verified as a set of independent inclusion proofs.",
    "Recent events are <font face='Courier'>pending</font> until the next checkpoint (anchoring runs "
    "on a cadence, not synchronously).",
    "Roots are <b>per-org</b> (tenant isolation). The anchor sits on top of the keyed chain and needs "
    "none of its secret to verify.",
]:
    story.append(Paragraph(f"&bull;&nbsp;&nbsp;{li}", mkstyle("li", parent=body, spaceAfter=3)))
story += [
    Spacer(1, 6),
    Paragraph(
        "References: RFC 6962 (Certificate Transparency) · RFC 8785 (JCS) · DSSE · OCSF.",
        mkstyle("ref", parent=body, textColor=GRAY),
    ),
]

doc = BaseDocTemplate(
    OUT,
    pagesize=letter,
    leftMargin=0.75 * inch,
    rightMargin=0.75 * inch,
    topMargin=0.7 * inch,
    bottomMargin=0.8 * inch,
    title="AI Identity — Evidence Anchor Reference Notes",
    author="AI Identity",
)
cover_f = Frame(0.95 * inch, 0.8 * inch, letter[0] - 1.7 * inch, letter[1] - 1.6 * inch, id="cover")
body_f = Frame(0.75 * inch, 0.8 * inch, letter[0] - 1.5 * inch, letter[1] - 1.6 * inch, id="body")
doc.addPageTemplates(
    [
        PageTemplate(id="cover", frames=[cover_f], onPage=_coverpage),
        PageTemplate(id="body", frames=[body_f], onPage=_bodypage),
    ]
)
doc.build(story)
print("wrote", OUT)
