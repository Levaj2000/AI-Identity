"""Build polished PDF content pack: DeepSeek as Exhibit A.

AI Identity Purple template (deep purple cover, purple top-bar pages,
eyebrow + H1, lavender callouts, footer with brand/date/page).
"""

from datetime import date

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

OUT = "/Users/jeffleva/Dev/AI-Identity/marketing/blog/deepseek-exhibit-a/DeepSeek_Exhibit_A.pdf"

# Brand palette
PURPLE_DEEP = HexColor("#4B2D7F")
PURPLE_MID = HexColor("#6B4FA0")
PURPLE_SOFT = HexColor("#A78BFA")
LAVENDER_BG = HexColor("#F0E8F8")
LAVENDER_LINE = HexColor("#D9C9EE")
AMBER = HexColor("#F59E0B")
INK = HexColor("#1F1B2E")
INK_SOFT = HexColor("#4B4A5A")
INK_MUTED = HexColor("#7A7990")
PAGE_BG = white

DOC_TITLE = "DeepSeek as Exhibit A"
DOC_SUB = "Why AI Needs Identity and Forensics"
TODAY = date.today().strftime("%B %d, %Y")
BRAND = "AI Identity  ·  ai-identity.co"

PAGE_W, PAGE_H = LETTER
MARGIN_L = 0.75 * inch
MARGIN_R = 0.75 * inch
MARGIN_T = 1.05 * inch
MARGIN_B = 0.85 * inch

# ---------- styles ----------
styles = getSampleStyleSheet()


def S(name, **kw):  # noqa: N802 — single-letter shorthand for paragraph-style factory, used inline 16+ times
    base = {
        "fontName": "Helvetica",
        "fontSize": 10.5,
        "leading": 15,
        "textColor": INK,
        "spaceAfter": 6,
    }
    base.update(kw)
    return ParagraphStyle(name, **base)


eyebrow_st = S(
    "eyebrow",
    fontName="Helvetica-Bold",
    fontSize=8.5,
    leading=12,
    textColor=PURPLE_MID,
    spaceAfter=4,
)
h1_st = S(
    "h1", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=PURPLE_DEEP, spaceAfter=10
)
h2_st = S(
    "h2",
    fontName="Helvetica-Bold",
    fontSize=14,
    leading=18,
    textColor=PURPLE_DEEP,
    spaceAfter=6,
    spaceBefore=10,
)
h3_st = S(
    "h3",
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=15,
    textColor=PURPLE_MID,
    spaceAfter=4,
    spaceBefore=6,
)
body_st = S("body", fontSize=10.5, leading=15.5, textColor=INK, spaceAfter=7)
body_just = S(
    "bodyj", fontSize=10.5, leading=15.5, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=7
)
caption_st = S("cap", fontSize=8.5, leading=11, textColor=INK_MUTED, fontName="Helvetica-Oblique")
callout_st = S("call", fontSize=10, leading=14, textColor=PURPLE_DEEP, fontName="Helvetica-Bold")
callout_body = S("callb", fontSize=10, leading=14, textColor=INK)
mono_st = S("mono", fontName="Courier", fontSize=9, leading=12, textColor=PURPLE_DEEP)
quote_st = S(
    "quote",
    fontSize=11,
    leading=16,
    textColor=INK,
    fontName="Helvetica-Oblique",
    leftIndent=14,
    spaceAfter=8,
)
tag_st = S(
    "tag", fontSize=8.5, leading=10, textColor=white, fontName="Helvetica-Bold", alignment=TA_CENTER
)
link_st = S("link", fontSize=9, leading=12, textColor=PURPLE_MID)


# ---------- page chrome ----------
def draw_content_chrome(c, doc):
    # white page background (defensive)
    c.setFillColor(white)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    # thin purple top bar (matches weekly deck)
    c.setFillColor(PURPLE_DEEP)
    c.rect(0, PAGE_H - 0.10 * inch, PAGE_W, 0.10 * inch, stroke=0, fill=1)
    # footer text (no rule, matches weekly deck)
    c.setFont("Helvetica", 8.5)
    c.setFillColor(INK_MUTED)
    c.drawString(MARGIN_L, 0.42 * inch, f"AI Identity  ·  DeepSeek: Exhibit A  ·  {TODAY}")
    c.drawRightString(PAGE_W - MARGIN_R, 0.42 * inch, f"{doc.page} / 3")


def draw_cover_chrome(c, doc):
    # full-bleed deep purple
    c.setFillColor(PURPLE_DEEP)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    # left accent bar (lighter purple, ~14px = 0.195")
    c.setFillColor(PURPLE_SOFT)
    c.rect(0, 0, 0.195 * inch, PAGE_H, stroke=0, fill=1)


# ---------- doc setup ----------
doc = BaseDocTemplate(
    OUT,
    pagesize=LETTER,
    leftMargin=MARGIN_L,
    rightMargin=MARGIN_R,
    topMargin=MARGIN_T,
    bottomMargin=MARGIN_B,
    title=DOC_TITLE,
    author="AI Identity",
)

content_frame = Frame(
    MARGIN_L,
    MARGIN_B,
    PAGE_W - MARGIN_L - MARGIN_R,
    PAGE_H - MARGIN_T - MARGIN_B,
    id="content",
    leftPadding=0,
    rightPadding=0,
    topPadding=0,
    bottomPadding=0,
)

cover_frame = Frame(
    MARGIN_L,
    MARGIN_B,
    PAGE_W - MARGIN_L - MARGIN_R,
    PAGE_H - MARGIN_T - MARGIN_B,
    id="cover",
    leftPadding=0,
    rightPadding=0,
    topPadding=0,
    bottomPadding=0,
)

doc.addPageTemplates(
    [
        PageTemplate(id="cover", frames=[cover_frame], onPage=draw_cover_chrome),
        PageTemplate(id="content", frames=[content_frame], onPage=draw_content_chrome),
    ]
)


# ---------- helpers ----------
def callout(title, body_text):
    inner = [
        Paragraph(title, callout_st),
        Spacer(1, 3),
        Paragraph(body_text, callout_body),
    ]
    t = Table([[inner]], colWidths=[PAGE_W - MARGIN_L - MARGIN_R])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LAVENDER_BG),
                ("BOX", (0, 0), (-1, -1), 0, LAVENDER_BG),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LINEBEFORE", (0, 0), (0, -1), 4, PURPLE_DEEP),
            ]
        )
    )
    return t


def three_card_row(items):
    """items: list of (label, body) — 3 cards."""
    cells = []
    for label, body in items:
        cell = [
            Paragraph(
                f'<font color="#F59E0B">{label}</font>',
                S(
                    "cl",
                    fontName="Helvetica-Bold",
                    fontSize=9,
                    textColor=AMBER,
                    leading=11,
                    spaceAfter=4,
                ),
            ),
            Paragraph(body, S("cb", fontSize=10, leading=13, textColor=INK)),
        ]
        cells.append(cell)
    col_w = (PAGE_W - MARGIN_L - MARGIN_R - 16) / 3
    t = Table([cells], colWidths=[col_w] * 3)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LAVENDER_BG),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBEFORE", (1, 0), (-1, -1), 0.5, white),
            ]
        )
    )
    return t


def eyebrow(text):
    return Paragraph(text.upper(), eyebrow_st)


def h1(text):
    return Paragraph(text, h1_st)


def h2(text):
    return Paragraph(text, h2_st)


def h3(text):
    return Paragraph(text, h3_st)


def p(text):
    return Paragraph(text, body_st)


def pj(text):
    return Paragraph(text, body_just)


def hr(color=LAVENDER_LINE, thickness=0.5, space=8):
    t = Table([[""]], colWidths=[PAGE_W - MARGIN_L - MARGIN_R], rowHeights=[thickness])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color)]))
    return KeepTogether([Spacer(1, space), t, Spacer(1, space)])


# ---------- cover page flowables ----------
def cover_block():
    # Use a stack of Paragraphs with white text on purple bg
    eyebrow_w = ParagraphStyle("ew", parent=eyebrow_st, textColor=PURPLE_SOFT)
    h1_w = ParagraphStyle(
        "h1w", fontName="Helvetica-Bold", fontSize=46, leading=50, textColor=white, spaceAfter=14
    )
    sub_w = ParagraphStyle(
        "subw",
        fontName="Helvetica",
        fontSize=20,
        leading=26,
        textColor=HexColor("#E6DCFB"),
        spaceAfter=20,
    )
    deck_w = ParagraphStyle(
        "dkw",
        fontName="Helvetica",
        fontSize=12.5,
        leading=18,
        textColor=HexColor("#D9C9EE"),
        spaceAfter=24,
    )
    date_w = ParagraphStyle(
        "dtw",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=PURPLE_SOFT,
        spaceAfter=6,
    )
    foot_w = ParagraphStyle(
        "ftw", fontName="Helvetica", fontSize=9, leading=12, textColor=HexColor("#D9C9EE")
    )

    items = []
    items.append(Spacer(1, 0.2 * inch))
    items.append(Paragraph("AI IDENTITY  ·  CONTENT PACK  ·  ISSUE 01", eyebrow_w))
    items.append(Spacer(1, 0.15 * inch))
    items.append(Paragraph("Exhibit A", h1_w))
    items.append(Paragraph("DeepSeek and the AI Trust Gap", sub_w))
    items.append(
        Paragraph(
            "Why every powerful model now needs an identity, a policy, "
            "and a paper trail — and why one app's headlines point at "
            "an industry-wide deployment problem.",
            deck_w,
        )
    )

    # Three cards on cover
    card_lbl = ParagraphStyle(
        "clbl",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=AMBER,
        leading=12,
        spaceAfter=4,
        alignment=TA_CENTER,
    )
    card_bod = ParagraphStyle(
        "cbod",
        fontName="Helvetica",
        fontSize=10.5,
        textColor=white,
        leading=14,
        alignment=TA_CENTER,
    )

    def card(lbl, body):
        return [Paragraph(lbl, card_lbl), Paragraph(body, card_bod)]

    col_w = (PAGE_W - MARGIN_L - MARGIN_R - 24) / 3
    tcards = Table(
        [
            [
                card("WHO", "acted on the data?"),
                card("POLICY", "was applied?"),
                card("PROOF", "remains afterward?"),
            ]
        ],
        colWidths=[col_w] * 3,
    )
    tcards.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), Color(1, 1, 1, alpha=0.08)),
                ("BOX", (0, 0), (0, 0), 0.6, PURPLE_SOFT),
                ("BOX", (1, 0), (1, 0), 0.6, PURPLE_SOFT),
                ("BOX", (2, 0), (2, 0), 0.6, PURPLE_SOFT),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    items.append(tcards)
    items.append(Spacer(1, 0.45 * inch))

    # amber rule
    amber_rule = Table([[""]], colWidths=[2.0 * inch], rowHeights=[1.4])
    amber_rule.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), AMBER)]))
    items.append(amber_rule)
    items.append(Spacer(1, 6))
    items.append(Paragraph(TODAY.upper(), date_w))
    items.append(Spacer(1, 4))
    author_lbl = ParagraphStyle(
        "aul", fontName="Helvetica", fontSize=9, leading=11, textColor=PURPLE_SOFT, spaceAfter=2
    )
    author_val = ParagraphStyle(
        "auv", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=white, spaceAfter=2
    )
    items.append(Paragraph("AUTHORED BY", author_lbl))
    items.append(Paragraph("Jeff Leva  —  Founder, AI Identity", author_val))
    items.append(Paragraph("ai-identity.co", foot_w))
    return items


# ---------- build story ----------
story = []

# COVER
story.append(NextPageTemplate("content"))  # all pages AFTER cover switch to content
story.extend(cover_block())
story.append(PageBreak())

# --- Page 1: Article ---
story.append(eyebrow("Feature Essay  ·  4 min read"))
story.append(h1("DeepSeek as Exhibit A: Why AI Needs Identity and Forensics"))
byline_st = ParagraphStyle(
    "by", fontName="Helvetica", fontSize=10, leading=14, textColor=INK_MUTED, spaceAfter=14
)
story.append(
    Paragraph(
        f'By <b><font color="#4B2D7F">Jeff Leva</font></b> — Founder, AI Identity  ·  {TODAY}',
        byline_st,
    )
)
story.append(
    Paragraph(
        "DeepSeek is a useful narrative hook for a larger point: advanced AI systems are being "
        "adopted faster than trust, security, and evidence frameworks are being built around them. "
        "The strongest conclusion is not that one product looks risky — it is that the current AI "
        "market still treats many powerful models like ordinary software components even when they "
        "can access sensitive data, execute workflows, and influence real-world decisions.",
        body_just,
    )
)

story.append(h2("Why DeepSeek raised alarms"))
story.append(
    pj(
        "DeepSeek drew scrutiny because multiple analyses described a combination of privacy, "
        "security, and governance concerns — not one isolated flaw. Reported concerns include "
        "extensive data collection, storage of user data on servers in China, legal access risks "
        "tied to Chinese law, and technical weaknesses in mobile app security controls."
    )
)
story.append(
    pj(
        "Several reviews also noted that DeepSeek's apps appeared to gather broad categories of "
        "information — chat content, device details, usage patterns. In practical terms, users "
        "cannot treat prompts as disposable when those prompts may contain business ideas, "
        "internal code, customer data, or operational context."
    )
)

story.append(h2("The real issue is not only privacy"))
story.append(
    pj(
        "Privacy is the most visible concern, but the bigger issue is trust across the full "
        "lifecycle of an AI interaction. Once a model is integrated into real work, organizations "
        "need to know which model acted, what data it saw, what tools it invoked, what policy "
        "should have applied, and what evidence remains after the fact."
    )
)
story.append(
    pj(
        "That is where many AI deployments break down. Traditional SaaS security assumes a user, "
        "an application, and a log trail. Agentic AI introduces probabilistic behavior, dynamic "
        "tool use, prompt-injection exposure, and third-party model dependencies that blur "
        "accountability. A breach or misuse event is harder to reconstruct when the system lacks "
        "strong identity, policy enforcement, and tamper-evident records."
    )
)

story.append(
    callout(
        "Why this matters",
        "Logs are not evidence. If your incident response depends on trusting a vendor's own "
        "records, you do not have a forensic posture — you have a relationship.",
    )
)

story.append(PageBreak())

# --- Page 2: continued ---
story.append(eyebrow("Feature Essay  ·  Continued"))
story.append(h2("Why identity matters"))
story.append(
    pj(
        "Identity answers a basic but underappreciated question: <i>who, exactly, performed an "
        "action.</i> In human systems, that question is handled through accounts, roles, "
        "credentials, and access controls. In agentic systems, those same primitives are often "
        "incomplete or missing."
    )
)
story.append(
    pj(
        "Without durable agent identity, every model call starts to look anonymous after the "
        "fact. That makes it difficult to separate an authorized workflow from a hijacked one, "
        "a policy-approved action from a prompt-injected action, or a legitimate orchestration "
        "step from an unsafe escalation."
    )
)

story.append(h2("Why forensics matters"))
story.append(
    pj(
        "Forensics is what turns activity into evidence. Logging alone is not enough when an "
        "organization needs to investigate a sensitive event, brief leadership, support legal "
        "review, or demonstrate compliance to an auditor."
    )
)
story.append(
    pj(
        "A credible AI forensics layer should preserve a verifiable chain of events: which "
        "identity initiated the task, what context was present, what policy was evaluated, what "
        "outputs were produced, and whether the record can be independently validated later. "
        "When that chain does not exist, incident response depends too heavily on trust in the "
        "vendor's own records and explanations."
    )
)

story.append(h2("What DeepSeek illustrates for the market"))
story.append(
    pj(
        "DeepSeek is best understood as a warning sign for the broader AI ecosystem. The lesson "
        "is not that one vendor is imperfect; it is that organizations are rushing powerful AI "
        "capabilities into workflows before they have established model governance, data-handling "
        "boundaries, approved deployment patterns, and reliable forensic evidence."
    )
)
story.append(
    pj(
        "The pattern will repeat with other models, open-weight systems, wrappers, and agent "
        "frameworks unless buyers demand stronger control planes around identity, policy, and "
        "auditability. The industry does not only need safer models — it needs infrastructure "
        "that makes AI actions <b>attributable, governable, and investigable</b>."
    )
)

story.append(h2("Practical guidance"))
story.append(h3("For individuals"))
story.append(
    pj(
        "Assume that any prompt sent to an untrusted AI service may be retained, analyzed, or "
        "exposed beyond the original interaction. Sensitive work, proprietary code, credentials, "
        "financial records, legal material, and regulated data should stay out of services with "
        "unresolved privacy or security concerns."
    )
)
story.append(h3("For organizations"))
story.append(
    pj(
        "Treat external AI models as untrusted execution components unless they are wrapped in "
        "enterprise controls: clear model approval standards, prompt and output handling rules, "
        "strong identity, policy enforcement, monitoring, and tamper-evident audit trails."
    )
)

# --- Closing ---
story.append(Spacer(1, 8))
story.append(h2("The bottom line"))

closing_st = ParagraphStyle(
    "closing",
    fontName="Helvetica-Oblique",
    fontSize=11.5,
    leading=17,
    textColor=INK,
    spaceAfter=10,
    alignment=TA_JUSTIFY,
)
story.append(
    Paragraph(
        "DeepSeek didn't break AI security. It revealed what was already broken: every "
        "powerful model deployed without identity, policy, or evidence is one incident "
        "away from looking just as risky.",
        closing_st,
    )
)
story.append(
    Paragraph(
        "The industry doesn't only need safer models. It needs infrastructure that makes AI "
        "actions <b>attributable, governable, and investigable.</b>",
        closing_st,
    )
)

story.append(Spacer(1, 6))
story.append(
    callout(
        "From AI Identity",
        "That infrastructure is what we're building — durable identity and tamper-evident "
        "forensics for every agent and model call, so when something goes wrong you don't "
        "have to trust a vendor's logs. You have your own.<br/><br/>"
        "Learn more at <b><font color='#4B2D7F'>ai-identity.co</font></b>.",
    )
)

doc.build(story)
print(f"WROTE: {OUT}")
