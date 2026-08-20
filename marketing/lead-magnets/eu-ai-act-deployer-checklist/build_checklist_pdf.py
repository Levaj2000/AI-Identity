"""
Generator for the EU AI Act Deployer Evidence Checklist lead magnet.

Companion download for the blog post in
marketing/blog/eu-ai-act-deployer-evidence/ — the artifact behind
ai-identity.co/eu-ai-act-checklist.

Output: 6-page A4 PDF.
Re-run: python3 build_checklist_pdf.py
"""

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Brand palette — aligned with landing page + Midnight Executive theme
# (same values as marketing/linkedin/build_carousel.py)
NAVY = HexColor("#0B1E3F")
NAVY_CARD = HexColor("#12294D")
NAVY_RULE = HexColor("#1E3A68")
ICE = HexColor("#A6DAFF")
ICE_MUTED = HexColor("#B8C7DD")
WHITE = HexColor("#FFFFFF")
AMBER = HexColor("#F59E0B")

W, H = A4  # 595 x 842 pt
MARGIN_L = 56
MARGIN_R = 48
MARGIN_T = 64
MARGIN_B = 56
ACCENT_W = 10
CONTENT_L = MARGIN_L
CONTENT_R = W - MARGIN_R
CONTENT_W = CONTENT_R - CONTENT_L

FONT = "Helvetica"
FONT_B = "Helvetica-Bold"
FONT_O = "Helvetica-Oblique"
FONT_M = "Courier"

TOTAL_PAGES = 6

DISCLAIMER = (
    "Engineering aid, not legal advice. Verify article citations against the OJ text with counsel."
)


def draw_background(c: canvas.Canvas, page_num: int) -> None:
    c.setFillColor(NAVY)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(AMBER)
    c.rect(0, 0, ACCENT_W, H, fill=1, stroke=0)
    c.setFillColor(ICE_MUTED)
    c.setFont(FONT, 8)
    c.drawString(CONTENT_L, 30, "ai-identity.co")
    c.drawRightString(CONTENT_R, 30, f"{page_num} / {TOTAL_PAGES}")
    if page_num > 1:
        c.setFont(FONT_O, 7)
        c.drawCentredString(W / 2 + 10, 30, DISCLAIMER)


def wrap(c: canvas.Canvas, text: str, font: str, size: int, max_w: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for w in words:
        trial = " ".join(current + [w])
        if c.stringWidth(trial, font, size) <= max_w:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines


def draw_wrapped(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    font: str,
    size: int,
    max_w: float,
    leading: float,
    color=WHITE,
) -> float:
    c.setFillColor(color)
    c.setFont(font, size)
    for line in wrap(c, text, font, size, max_w):
        c.drawString(x, y, line)
        y -= leading
    return y


def heading(c: canvas.Canvas, kicker: str, title: str, y: float) -> float:
    c.setFillColor(AMBER)
    c.setFont(FONT_B, 10)
    c.drawString(CONTENT_L, y, kicker.upper())
    y -= 24
    y = draw_wrapped(c, title, CONTENT_L, y, FONT_B, 21, CONTENT_W, 26, WHITE)
    y -= 4
    c.setStrokeColor(NAVY_RULE)
    c.setLineWidth(1)
    c.line(CONTENT_L, y, CONTENT_R, y)
    return y - 22


# ---------------------------------------------------------------- page 1: cover
def page_cover(c: canvas.Canvas) -> None:
    draw_background(c, 1)
    c.setFillColor(ICE)
    c.setFont(FONT_B, 13)
    c.drawString(CONTENT_L, H - 130, "AI IDENTITY")
    c.setFillColor(ICE_MUTED)
    c.setFont(FONT, 13)
    c.drawString(
        CONTENT_L + c.stringWidth("AI IDENTITY", FONT_B, 13) + 8,
        H - 130,
        "— Every agent leaves a trace.",
    )

    y = H - 300
    c.setFillColor(AMBER)
    c.setFont(FONT_B, 11)
    c.drawString(CONTENT_L, y, "FOR TEAMS THAT RUN AGENTS, NOT TRAIN MODELS")
    y -= 44
    for line in ["The EU AI Act", "Deployer Evidence", "Checklist"]:
        c.setFillColor(WHITE)
        c.setFont(FONT_B, 40)
        c.drawString(CONTENT_L, y, line)
        y -= 46

    y -= 10
    y = draw_wrapped(
        c,
        "The records Articles 12 and 26 require, the questions a market surveillance "
        "authority will ask, and a worksheet to find out where each record lives today.",
        CONTENT_L,
        y,
        FONT,
        13,
        CONTENT_W - 60,
        19,
        ICE_MUTED,
    )

    y -= 36
    c.setFillColor(NAVY_CARD)
    c.roundRect(CONTENT_L, y - 74, CONTENT_W, 88, 8, fill=1, stroke=0)
    c.setFillColor(ICE)
    c.setFont(FONT_B, 12)
    c.drawString(CONTENT_L + 20, y - 10, "Why now")
    draw_wrapped(
        c,
        "On 2 August 2026 the high-risk obligations under Annex III and the deployer "
        "duties under Article 26 became applicable. The six-month log-retention clock "
        "is already running — records cannot be backfilled.",
        CONTENT_L + 20,
        y - 30,
        FONT,
        10.5,
        CONTENT_W - 40,
        15,
        ICE_MUTED,
    )

    c.setFillColor(ICE_MUTED)
    c.setFont(FONT_O, 9)
    c.drawString(CONTENT_L, 78, "August 2026 edition · Regulation (EU) 2024/1689")
    c.setFont(FONT_O, 8)
    c.drawString(CONTENT_L, 62, DISCLAIMER)
    c.showPage()


# ------------------------------------------------- page 2: deployer lane + timeline
def page_deployer(c: canvas.Canvas) -> None:
    draw_background(c, 2)
    y = heading(
        c,
        "The deployer lane",
        "You run agents. That makes you a deployer — and the deployer duties get the least airtime.",
        H - MARGIN_T,
    )

    y = draw_wrapped(
        c,
        "Most EU AI Act content is written for model providers: GPAI documentation, training "
        "data summaries, conformity assessments. If your company runs AI agents rather than "
        "trains models, you are a deployer under the Act. Your obligations are shorter to "
        "list — and they are the ones your team will be asked to evidence first.",
        CONTENT_L,
        y,
        FONT,
        10.5,
        CONTENT_W,
        15.5,
        ICE_MUTED,
    )
    y -= 18

    milestones = [
        ("2 Feb 2025", "Prohibited practices apply.", False),
        ("2 Aug 2025", "General-purpose AI model rules apply.", False),
        (
            "2 Aug 2026",
            "General application: Annex III high-risk obligations and the Article 26 deployer duties. This is the one that lands on agent operators.",
            True,
        ),
        ("2 Aug 2027", "Annex I product-safety high-risk systems.", False),
    ]
    c.setFillColor(ICE)
    c.setFont(FONT_B, 12)
    c.drawString(CONTENT_L, y, "The staged timeline")
    y -= 20
    rail_x = CONTENT_L + 6
    for date, text, hot in milestones:
        c.setFillColor(AMBER if hot else NAVY_RULE)
        c.circle(rail_x, y + 3, 4, fill=1, stroke=0)
        c.setFillColor(AMBER if hot else ICE)
        c.setFont(FONT_B, 10.5)
        c.drawString(rail_x + 16, y, date)
        ny = draw_wrapped(
            c,
            text,
            rail_x + 100,
            y,
            FONT_B if hot else FONT,
            10.5,
            CONTENT_R - (rail_x + 100),
            15,
            WHITE if hot else ICE_MUTED,
        )
        if text is not milestones[-1][1]:
            c.setStrokeColor(NAVY_RULE)
            c.setLineWidth(1.5)
            c.line(rail_x, y - 4, rail_x, ny + 10)
        y = ny - 14

    y -= 6
    c.setFillColor(ICE)
    c.setFont(FONT_B, 12)
    c.drawString(CONTENT_L, y, "What Article 26 actually asks of you")
    y -= 20
    duties = [
        (
            "Art. 26(1)",
            "Operate each system per the provider's instructions — which means a record of how each agent was configured, and when that changed.",
        ),
        (
            "Art. 26(2)",
            "Assign human oversight: a named function with the competence and authority to intervene, and a record that intervention happened when it should have.",
        ),
        (
            "Art. 26(5)",
            "Monitor operation, and inform the provider or authorities when something looks like a serious incident.",
        ),
        (
            "Art. 26(6)",
            "Retain the automatically generated logs for at least six months — longer where other EU or national law says so.",
        ),
    ]
    for art, text in duties:
        c.setFillColor(AMBER)
        c.setFont(FONT_B, 10.5)
        c.drawString(CONTENT_L, y, art)
        y = draw_wrapped(
            c, text, CONTENT_L + 78, y, FONT, 10.5, CONTENT_R - (CONTENT_L + 78), 15, ICE_MUTED
        )
        y -= 10

    draw_wrapped(
        c,
        "Behind these sits Article 12: high-risk systems must automatically record events over "
        "their lifetime, at a level that makes the system's behavior traceable. That is where "
        "the records in this checklist come from.",
        CONTENT_L,
        y - 4,
        FONT_O,
        10.5,
        CONTENT_W,
        15.5,
        ICE,
    )
    c.showPage()


# ------------------------------------------------------- page 3: the evidence test
def page_evidence_test(c: canvas.Canvas) -> None:
    draw_background(c, 3)
    y = heading(c, "The evidence test", "Why ordinary logs don't clear the bar", H - MARGIN_T)

    y = draw_wrapped(
        c,
        "A market surveillance authority — or your own counsel, after an incident — asks about "
        "a decision one of your agents made in March:",
        CONTENT_L,
        y,
        FONT,
        10.5,
        CONTENT_W,
        15.5,
        ICE_MUTED,
    )
    y -= 14
    c.setFillColor(NAVY_CARD)
    c.roundRect(CONTENT_L, y - 40, CONTENT_W, 52, 8, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FONT_B, 14)
    c.drawString(
        CONTENT_L + 20, y - 12, '"How do you know this record wasn\'t edited after the fact?"'
    )
    y -= 62

    y = draw_wrapped(
        c,
        "If the answer involves the phrase “our vendor's dashboard,” that isn't evidence — it's a "
        "relationship. Application logs in a SaaS console are mutable rows in someone else's "
        "database. They can be complete, well-intentioned, and beautifully searchable, and still "
        "prove nothing, because nothing about them lets a third party verify that the sequence "
        "of events is intact. If you can't verify it offline, it's not evidence.",
        CONTENT_L,
        y,
        FONT,
        10.5,
        CONTENT_W,
        15.5,
        ICE_MUTED,
    )
    y -= 20

    c.setFillColor(ICE)
    c.setFont(FONT_B, 12)
    c.drawString(CONTENT_L, y, "Five questions to ask before an authority does")
    y -= 22

    questions = [
        ("1", "Can you produce March's records without logging in to any vendor's dashboard?"),
        (
            "2",
            "Can a third party verify the sequence of events is intact — offline, without trusting you or your vendor?",
        ),
        (
            "3",
            "Which of your agents fall under an Annex III high-risk category? Is that a query today, or a quarterly archaeology project?",
        ),
        (
            "4",
            "Who approved the last high-impact agent action — and where is the approval, denial, or expiry recorded?",
        ),
        (
            "5",
            "If your logging vendor disappeared tomorrow, would the evidence you owe under Article 26(6) survive?",
        ),
    ]
    for num, text in questions:
        c.setFillColor(AMBER)
        c.setFont(FONT_B, 13)
        c.drawString(CONTENT_L, y, num)
        ny = draw_wrapped(
            c, text, CONTENT_L + 24, y, FONT, 11, CONTENT_R - (CONTENT_L + 24), 15.5, WHITE
        )
        c.setStrokeColor(NAVY_RULE)
        c.setLineWidth(0.75)
        c.line(CONTENT_L + 24, ny + 4, CONTENT_R, ny + 4)
        y = ny - 14

    draw_wrapped(
        c,
        "A “no” on any of these is not a compliance-tool gap. It is a records gap — and records, "
        "unlike policy documents, cannot be written late.",
        CONTENT_L,
        y,
        FONT_O,
        10.5,
        CONTENT_W,
        15.5,
        ICE,
    )
    c.showPage()


# ---------------------------------------------------------- pages 4-5: the worksheet
CHECK_ROWS = [
    (
        "Automatic event records",
        "Art. 12(1)",
        "Every agent decision recorded automatically over the system's lifetime — not just errors.",
    ),
    (
        "Traceable agent identity",
        "Art. 12",
        "Each record names which agent acted, for whom, and with what outcome.",
    ),
    (
        "Tamper-evidence",
        "Art. 12(4)",
        "A third party can verify offline that the record sequence is intact (e.g. hash-chained events, signed attestations).",
    ),
    (
        "Configuration record",
        "Art. 26(1)",
        "How each agent was configured against the provider's instructions — and when that changed.",
    ),
    (
        "Human oversight record",
        "Art. 14 / 26(2)",
        "A named oversight function, plus the full approval trail: approved, denied, and auto-expired.",
    ),
    (
        "Monitoring & incidents",
        "Art. 26(5)",
        "Operational monitoring with an escalation path to the provider or authorities for serious incidents.",
    ),
    (
        "Log retention",
        "Art. 19 / 26(6)",
        "Automatically generated logs kept at least six months; longer where other law applies.",
    ),
    (
        "Risk classification inventory",
        "Annex III",
        "An Annex III category (or explicit not-in-scope) attached to every agent, queryable on demand.",
    ),
    (
        "Capability disclosures",
        "Art. 13",
        "What each agent could do at each point in the period — descriptions and capability sets over time.",
    ),
    (
        "Policy change history",
        "Art. 9",
        "The rules agents ran under, with their full change history as risk management evolves.",
    ),
]


def worksheet_page(c: canvas.Canvas, page_num: int, rows, first: bool) -> None:
    draw_background(c, page_num)
    if first:
        y = heading(c, "The worksheet", "Ten records the Act expects you to produce", H - MARGIN_T)
        y = draw_wrapped(
            c,
            "For each record: write down where it lives today, then answer the only question that "
            "makes it evidence — could someone verify it without trusting the system that produced it?",
            CONTENT_L,
            y,
            FONT,
            10.5,
            CONTENT_W,
            15.5,
            ICE_MUTED,
        )
        y -= 16
    else:
        y = heading(
            c, "The worksheet", "Ten records the Act expects you to produce (cont.)", H - MARGIN_T
        )

    for name, art, desc in rows:
        card_h = 96
        c.setFillColor(NAVY_CARD)
        c.roundRect(CONTENT_L, y - card_h, CONTENT_W, card_h, 6, fill=1, stroke=0)
        # checkbox
        c.setStrokeColor(ICE)
        c.setLineWidth(1.2)
        c.rect(CONTENT_L + 16, y - 28, 13, 13, fill=0, stroke=1)
        c.setFillColor(WHITE)
        c.setFont(FONT_B, 11.5)
        c.drawString(CONTENT_L + 40, y - 24, name)
        c.setFillColor(AMBER)
        c.setFont(FONT_B, 9.5)
        c.drawRightString(CONTENT_R - 16, y - 24, art)
        draw_wrapped(c, desc, CONTENT_L + 40, y - 42, FONT, 9.5, CONTENT_W - 56, 13, ICE_MUTED)
        # fill-in lines
        line_y = y - card_h + 18
        c.setFillColor(ICE_MUTED)
        c.setFont(FONT_O, 8.5)
        c.drawString(CONTENT_L + 40, line_y, "Where it lives today:")
        lbl_w = c.stringWidth("Where it lives today:", FONT_O, 8.5)
        c.setStrokeColor(NAVY_RULE)
        c.setLineWidth(0.75)
        c.line(CONTENT_L + 44 + lbl_w, line_y - 1, CONTENT_L + 330, line_y - 1)
        c.setFont(FONT_O, 8.5)
        c.drawString(CONTENT_L + 344, line_y, "Verifiable offline?  Y / N")
        y -= card_h + 12
    c.showPage()


# ------------------------------------------------ page 6: evidence set + honest limits
def page_evidence_set(c: canvas.Canvas) -> None:
    draw_background(c, 6)
    y = heading(
        c,
        "What good looks like",
        "One bundle, one article per artifact, verifiable without us",
        H - MARGIN_T,
    )

    y = draw_wrapped(
        c,
        "This is the artifact set our EU AI Act export profile produces for a reporting period — "
        "generated from hash-chained audit records and checkable with an open CLI, no account "
        "on our side required:",
        CONTENT_L,
        y,
        FONT,
        10.5,
        CONTENT_W,
        15.5,
        ICE_MUTED,
    )
    y -= 12

    # ASCII only — the built-in PDF fonts have no box-drawing glyphs
    tree = [
        "eu_ai_act_2024_export/",
        "|- manifest.json                    DSSE-signed index of the bundle",
        "|- annex_iv_documentation.json      Annex IV technical documentation",
        "|- access_log.csv                   Art. 12 - every agent decision in period",
        "|- attestations/<session>.dsse.json Art. 12(4) - signed session attestations",
        "|- human_oversight_log.csv          Art. 14 / 26(2) - approvals, denials, expiries",
        "|- agent_risk_classification.csv    Annex III category per agent",
        "|- policy_change_log.csv            Art. 9 - risk-management change history",
        "'- capability_disclosures.csv       Art. 13 - per-agent capabilities over time",
    ]
    box_h = len(tree) * 13 + 24
    c.setFillColor(HexColor("#081630"))
    c.roundRect(CONTENT_L, y - box_h, CONTENT_W, box_h, 6, fill=1, stroke=0)
    ty = y - 20
    for i, line in enumerate(tree):
        c.setFillColor(ICE if i == 0 else ICE_MUTED)
        c.setFont(FONT_M, 8.2)
        c.drawString(CONTENT_L + 16, ty, line)
        ty -= 13
    y -= box_h + 24

    c.setFillColor(ICE)
    c.setFont(FONT_B, 12)
    c.drawString(CONTENT_L, y, "Two things we deliberately don't claim")
    y -= 20
    limits = [
        (
            "Article 10 data governance is the provider's problem.",
            "Upstream training-data governance sits outside a deployer platform's visibility. Our Annex IV export says so explicitly rather than fabricating evidence to fill the section.",
        ),
        (
            "There is no EU AI Act certificate to wave.",
            "Conformity assessment bodies are still standing up. What can exist today is architecture that produces the required records in the required shape — and an export a regulator can verify without trusting the vendor.",
        ),
    ]
    for title, text in limits:
        c.setFillColor(WHITE)
        c.setFont(FONT_B, 10.5)
        y = draw_wrapped(c, title, CONTENT_L, y, FONT_B, 10.5, CONTENT_W, 15, WHITE)
        y = draw_wrapped(c, text, CONTENT_L, y, FONT, 10, CONTENT_W, 14.5, ICE_MUTED)
        y -= 12

    # CTA card
    c.setFillColor(NAVY_CARD)
    c.roundRect(CONTENT_L, y - 96, CONTENT_W, 104, 8, fill=1, stroke=0)
    c.setFillColor(AMBER)
    c.setFont(FONT_B, 12)
    c.drawString(CONTENT_L + 20, y - 14, "The six-month clock is already running")
    draw_wrapped(
        c,
        "The logs you must produce next February are the ones your agents are generating right "
        "now. If the worksheet left blanks in the “verifiable offline” column, that is the gap to "
        "close first. See how AI Identity produces this evidence set from per-agent identity, "
        "fail-closed policy, and hash-chained audit trails:",
        CONTENT_L + 20,
        y - 34,
        FONT,
        10,
        CONTENT_W - 40,
        14.5,
        ICE_MUTED,
    )
    c.setFillColor(ICE)
    c.setFont(FONT_B, 12)
    c.drawString(CONTENT_L + 20, y - 86, "ai-identity.co  ·  ai-identity.co/eu-ai-act-checklist")
    c.showPage()


def main() -> None:
    out = Path(__file__).parent / "eu-ai-act-deployer-evidence-checklist.pdf"
    c = canvas.Canvas(str(out), pagesize=A4)
    c.setTitle("The EU AI Act Deployer Evidence Checklist — AI Identity")
    c.setAuthor("AI Identity")
    c.setSubject(
        "The records Articles 12 and 26 require of AI agent deployers, and a worksheet to locate each one."
    )
    page_cover(c)
    page_deployer(c)
    page_evidence_test(c)
    worksheet_page(c, 4, CHECK_ROWS[:5], first=True)
    worksheet_page(c, 5, CHECK_ROWS[5:], first=False)
    page_evidence_set(c)
    c.save()
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
