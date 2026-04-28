"""
Generator for LinkedIn PDF carousels.

Current deck: "Traditional IAM vs. context-aware policy + signed attestations"
Output: 9-slide PDF at 4:5 aspect ratio (1200x1500 pt).

Re-run: python3 build_carousel.py
"""

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

# Brand palette — aligned with landing page + Midnight Executive theme
NAVY = HexColor("#0B1E3F")
NAVY_CARD = HexColor("#12294D")
NAVY_RULE = HexColor("#1E3A68")
ICE = HexColor("#A6DAFF")
ICE_MUTED = HexColor("#B8C7DD")
WHITE = HexColor("#FFFFFF")
AMBER = HexColor("#F59E0B")

# Canvas — 4:5 LinkedIn carousel
W, H = 1200, 1500
MARGIN_L = 120
MARGIN_R = 100
MARGIN_T = 140
MARGIN_B = 120
ACCENT_W = 24
CONTENT_L = MARGIN_L
CONTENT_R = W - MARGIN_R
CONTENT_W = CONTENT_R - CONTENT_L

FONT = "Helvetica"
FONT_B = "Helvetica-Bold"


def draw_background(c: canvas.Canvas, slide_num: int, total: int) -> None:
    c.setFillColor(NAVY)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    # Left accent bar
    c.setFillColor(AMBER)
    c.rect(0, 0, ACCENT_W, H, fill=1, stroke=0)
    # Footer
    c.setFillColor(ICE_MUTED)
    c.setFont(FONT, 18)
    c.drawString(CONTENT_L, 60, "ai-identity.co")
    c.drawRightString(CONTENT_R, 60, f"{slide_num} / {total}")


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
    color,
    max_w: float,
    leading_ratio: float = 1.25,
) -> float:
    """Draw wrapped text top-anchored at y. Returns y of next line below block."""
    c.setFillColor(color)
    c.setFont(font, size)
    leading = size * leading_ratio
    lines = wrap(c, text, font, size, max_w)
    cur = y
    for line in lines:
        c.drawString(x, cur, line)
        cur -= leading
    return cur


def slide_hook(c: canvas.Canvas) -> None:
    draw_background(c, 1, 9)
    # Eyebrow
    c.setFillColor(AMBER)
    c.setFont(FONT_B, 22)
    c.drawString(CONTENT_L, H - MARGIN_T, "AI AGENT IDENTITY")
    # Big headline
    y = H - MARGIN_T - 120
    y = draw_wrapped(
        c, "Your AI agent just moved $50K.", CONTENT_L, y, FONT_B, 84, WHITE, CONTENT_W, 1.1
    )
    y -= 40
    y = draw_wrapped(
        c, "Can you prove who told it to?", CONTENT_L, y, FONT_B, 84, ICE, CONTENT_W, 1.1
    )
    # Lower caption
    c.setFillColor(ICE_MUTED)
    c.setFont(FONT, 26)
    c.drawString(CONTENT_L, 240, "9 slides on why traditional IAM breaks for AI agents  →")


def slide_problem(c: canvas.Canvas) -> None:
    draw_background(c, 2, 9)
    c.setFillColor(AMBER)
    c.setFont(FONT_B, 22)
    c.drawString(CONTENT_L, H - MARGIN_T, "THE PROBLEM")
    y = H - MARGIN_T - 100
    y = draw_wrapped(
        c, "Traditional IAM was built for humans.", CONTENT_L, y, FONT_B, 62, WHITE, CONTENT_W, 1.15
    )
    y -= 60
    y = draw_wrapped(
        c,
        "Not for agents that delegate, chain tools, and act at machine speed.",
        CONTENT_L,
        y,
        FONT,
        32,
        ICE,
        CONTENT_W,
        1.35,
    )
    y -= 40
    y = draw_wrapped(
        c,
        "RBAC evaluates at login — then disappears. Permissions are granted to a role, not to an intent. The agent drifts. You can't attribute outcome to principal.",
        CONTENT_L,
        y,
        FONT,
        28,
        ICE_MUTED,
        CONTENT_W,
        1.45,
    )


def draw_card(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    body: str,
) -> None:
    c.setFillColor(NAVY_CARD)
    c.roundRect(x, y, w, h, 12, fill=1, stroke=0)
    # Amber left rule inside card
    c.setFillColor(AMBER)
    c.rect(x, y, 6, h, fill=1, stroke=0)
    # Label
    c.setFillColor(AMBER)
    c.setFont(FONT_B, 20)
    c.drawString(x + 30, y + h - 44, label)
    # Body
    c.setFillColor(WHITE)
    c.setFont(FONT, 24)
    lines = wrap(c, body, FONT, 24, w - 60)
    cur = y + h - 90
    for line in lines:
        c.drawString(x + 30, cur, line)
        cur -= 30


def slide_what_breaks(c: canvas.Canvas) -> None:
    draw_background(c, 3, 9)
    c.setFillColor(AMBER)
    c.setFont(FONT_B, 22)
    c.drawString(CONTENT_L, H - MARGIN_T, "WHAT BREAKS")
    y = H - MARGIN_T - 100
    y = draw_wrapped(
        c,
        "Three things break when agents meet RBAC.",
        CONTENT_L,
        y,
        FONT_B,
        52,
        WHITE,
        CONTENT_W,
        1.15,
    )
    # Three stacked cards
    card_h = 200
    gap = 30
    cards = [
        ("COMPLIANCE", 'EU AI Act Article 12 demands provenance. "Agent did X" isn\'t provenance.'),
        (
            "SECURITY",
            "No cryptographic chain from the human principal through the agent to the tool call.",
        ),
        (
            "FORENSICS",
            "When something goes wrong, you can't prove who authorized what — or even that anyone did.",
        ),
    ]
    # Stack top-down from y-80
    top = y - 80
    for i, (label, body) in enumerate(cards):
        draw_card(c, CONTENT_L, top - (card_h + gap) * i - card_h, CONTENT_W, card_h, label, body)


def slide_context_policy(c: canvas.Canvas) -> None:
    draw_background(c, 4, 9)
    c.setFillColor(AMBER)
    c.setFont(FONT_B, 22)
    c.drawString(CONTENT_L, H - MARGIN_T, "THE ANSWER — PART 1")
    y = H - MARGIN_T - 100
    y = draw_wrapped(c, "Context-aware policy.", CONTENT_L, y, FONT_B, 72, WHITE, CONTENT_W, 1.1)
    y -= 30
    y = draw_wrapped(
        c, "Evaluate every action. Not just login.", CONTENT_L, y, FONT_B, 34, ICE, CONTENT_W, 1.25
    )
    y -= 60
    bullets = [
        "Who is the human principal behind this agent?",
        "What's the intent — and the risk?",
        "What data sensitivity? Which tool is being called?",
        "Decision happens at the action, with full context.",
    ]
    c.setFillColor(WHITE)
    c.setFont(FONT, 30)
    for b in bullets:
        c.setFillColor(AMBER)
        c.circle(CONTENT_L + 12, y + 10, 6, fill=1, stroke=0)
        c.setFillColor(WHITE)
        y = draw_wrapped(c, b, CONTENT_L + 40, y, FONT, 30, WHITE, CONTENT_W - 40, 1.35)
        y -= 20


def slide_attestations(c: canvas.Canvas) -> None:
    draw_background(c, 5, 9)
    c.setFillColor(AMBER)
    c.setFont(FONT_B, 22)
    c.drawString(CONTENT_L, H - MARGIN_T, "THE ANSWER — PART 2")
    y = H - MARGIN_T - 100
    y = draw_wrapped(c, "Signed attestations.", CONTENT_L, y, FONT_B, 72, WHITE, CONTENT_W, 1.1)
    y -= 30
    y = draw_wrapped(
        c, "Cryptographic proof, per action.", CONTENT_L, y, FONT_B, 34, ICE, CONTENT_W, 1.25
    )
    y -= 60
    bullets = [
        "Every decision gets a signed attestation.",
        "Chain of delegation: human → agent → sub-agent → tool.",
        "Verifiable offline, post-hoc, by auditors.",
        "Non-repudiable — the principal's key signed it.",
    ]
    for b in bullets:
        c.setFillColor(AMBER)
        c.circle(CONTENT_L + 12, y + 10, 6, fill=1, stroke=0)
        c.setFillColor(WHITE)
        y = draw_wrapped(c, b, CONTENT_L + 40, y, FONT, 30, WHITE, CONTENT_W - 40, 1.35)
        y -= 20


def slide_compare(c: canvas.Canvas) -> None:
    draw_background(c, 6, 9)
    c.setFillColor(AMBER)
    c.setFont(FONT_B, 22)
    c.drawString(CONTENT_L, H - MARGIN_T, "SIDE BY SIDE")
    y = H - MARGIN_T - 100
    y = draw_wrapped(
        c,
        "RBAC vs. context-aware + attestations.",
        CONTENT_L,
        y,
        FONT_B,
        46,
        WHITE,
        CONTENT_W,
        1.15,
    )
    y -= 50

    # Column layout
    col1_x = CONTENT_L
    col2_x = CONTENT_L + 320
    col3_x = CONTENT_L + 680

    # Header row
    c.setFillColor(ICE_MUTED)
    c.setFont(FONT_B, 22)
    c.drawString(col1_x, y, "")
    c.setFillColor(AMBER)
    c.drawString(col2_x, y, "TRADITIONAL IAM")
    c.setFillColor(ICE)
    c.drawString(col3_x, y, "CONTEXT-AWARE")
    y -= 20
    # Divider
    c.setStrokeColor(NAVY_RULE)
    c.setLineWidth(2)
    c.line(CONTENT_L, y, CONTENT_R, y)
    y -= 50

    rows = [
        ("Evaluation", "At login", "Every action"),
        ("Context", "Role", "Principal, intent, risk, data"),
        ("Proof", "Logs (repudiable)", "Signed attestations"),
        ("Audit", '"Agent did X"', "Alice → Agent → Tool, signed"),
        ("Offline verify", "No", "Yes"),
    ]
    c.setFont(FONT, 24)
    for label, a, b in rows:
        c.setFillColor(ICE_MUTED)
        c.setFont(FONT_B, 22)
        c.drawString(col1_x, y, label)
        c.setFillColor(WHITE)
        c.setFont(FONT, 22)
        for line in wrap(c, a, FONT, 22, 340):
            c.drawString(col2_x, y, line)
            y -= 28
        c.setFillColor(ICE)
        for line in wrap(c, b, FONT, 22, 360):
            c.drawString(col3_x, y, line)
        y -= 64
        c.setStrokeColor(NAVY_RULE)
        c.setLineWidth(1)
        c.line(CONTENT_L, y + 22, CONTENT_R, y + 22)


def slide_unlocks(c: canvas.Canvas) -> None:
    draw_background(c, 7, 9)
    c.setFillColor(AMBER)
    c.setFont(FONT_B, 22)
    c.drawString(CONTENT_L, H - MARGIN_T, "WHAT THIS UNLOCKS")
    y = H - MARGIN_T - 100
    y = draw_wrapped(
        c, "Compliance, without the scramble.", CONTENT_L, y, FONT_B, 52, WHITE, CONTENT_W, 1.15
    )
    card_h = 200
    gap = 30
    cards = [
        (
            "EU AI ACT",
            "Article 12 logging — provenance captured at the action, not reconstructed from logs.",
        ),
        ("SOC 2", "Human-to-machine traceability for every privileged action an agent takes."),
        (
            "INCIDENT FORENSICS",
            'Signed chain of delegation preserved. Answer "who authorized this?" in seconds.',
        ),
    ]
    top = y - 80
    for i, (label, body) in enumerate(cards):
        draw_card(c, CONTENT_L, top - (card_h + gap) * i - card_h, CONTENT_W, card_h, label, body)


def slide_model(c: canvas.Canvas) -> None:
    draw_background(c, 8, 9)
    c.setFillColor(AMBER)
    c.setFont(FONT_B, 22)
    c.drawString(CONTENT_L, H - MARGIN_T, "THE MODEL")
    y = H - MARGIN_T - 100
    y = draw_wrapped(c, "Three layers. Built in.", CONTENT_L, y, FONT_B, 60, WHITE, CONTENT_W, 1.15)
    y -= 60
    layers = [
        ("1", "IDENTITY", "Who is the human principal behind the agent?"),
        ("2", "POLICY", "Can they, right now, perform this specific action?"),
        ("3", "ATTESTATION", "Cryptographic proof of every decision."),
    ]
    card_h = 180
    gap = 28
    top = y
    for i, (num, label, body) in enumerate(layers):
        cy = top - (card_h + gap) * i - card_h
        c.setFillColor(NAVY_CARD)
        c.roundRect(CONTENT_L, cy, CONTENT_W, card_h, 12, fill=1, stroke=0)
        # Big number
        c.setFillColor(AMBER)
        c.setFont(FONT_B, 96)
        c.drawString(CONTENT_L + 30, cy + 40, num)
        # Label
        c.setFillColor(ICE)
        c.setFont(FONT_B, 30)
        c.drawString(CONTENT_L + 180, cy + card_h - 60, label)
        # Body
        c.setFillColor(WHITE)
        c.setFont(FONT, 24)
        for j, line in enumerate(wrap(c, body, FONT, 24, CONTENT_W - 220)):
            c.drawString(CONTENT_L + 180, cy + card_h - 100 - j * 32, line)


def slide_cta(c: canvas.Canvas) -> None:
    draw_background(c, 9, 9)
    c.setFillColor(AMBER)
    c.setFont(FONT_B, 22)
    c.drawString(CONTENT_L, H - MARGIN_T, "SEE IT IN ACTION")
    y = H - MARGIN_T - 100
    y = draw_wrapped(
        c,
        "Context-aware policy and signed attestations for AI agents.",
        CONTENT_L,
        y,
        FONT_B,
        46,
        WHITE,
        CONTENT_W,
        1.2,
    )
    y -= 60
    c.setFillColor(ICE)
    c.setFont(FONT_B, 28)
    c.drawString(CONTENT_L, y, "Read:")
    y -= 44
    c.setFillColor(WHITE)
    c.setFont(FONT, 26)
    c.drawString(CONTENT_L + 40, y, "•  Forensic trust model — ai-identity.co/forensics")
    y -= 40
    c.drawString(CONTENT_L + 40, y, "•  EU AI Act checklist — ai-identity.co/eu-ai-act-checklist")
    y -= 40
    c.drawString(CONTENT_L + 40, y, "•  How it works — ai-identity.co/how-it-works")
    y -= 80
    c.setFillColor(ICE)
    c.setFont(FONT_B, 28)
    c.drawString(CONTENT_L, y, "Follow:")
    y -= 44
    c.setFillColor(WHITE)
    c.setFont(FONT_B, 32)
    c.drawString(CONTENT_L + 40, y, "AI Identity")
    c.setFillColor(ICE_MUTED)
    c.setFont(FONT, 22)
    c.drawString(CONTENT_L + 40, y - 36, "for more on AI agent identity, policy, and forensics.")


def main() -> None:
    out = Path(__file__).parent / "2026-04-20-context-aware-policy-vs-iam.pdf"
    c = canvas.Canvas(str(out), pagesize=(W, H))
    c.setTitle("Traditional IAM vs. Context-Aware Policy + Signed Attestations")
    c.setAuthor("AI Identity")

    for slide_fn in (
        slide_hook,
        slide_problem,
        slide_what_breaks,
        slide_context_policy,
        slide_attestations,
        slide_compare,
        slide_unlocks,
        slide_model,
        slide_cta,
    ):
        slide_fn(c)
        c.showPage()

    c.save()
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
