"""Generate the AI Identity OG image (1200x630) with the new forensics-led positioning.

Brand:
- Background: rgb(4,7,13)
- Accent:     rgb(166,218,255)
- Body text:  rgb(213,219,230)

Usage:
    python landing-page/scripts/build_og_image.py
"""

from __future__ import annotations

import io
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = (4, 7, 13)
ACCENT = (166, 218, 255)
TEXT = (213, 219, 230)
MUTED = (140, 152, 170)

OUT = Path(__file__).resolve().parents[1] / "public" / "images" / "og-image.png"
LOGO_MARK_SVG = Path(__file__).resolve().parents[2] / "assets" / "brand" / "logo-mark.svg"

HELVETICA_BOLD = "/System/Library/Fonts/HelveticaNeue.ttc"
GEORGIA_ITALIC = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
HELVETICA = "/System/Library/Fonts/HelveticaNeue.ttc"


def load(font_path: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_path, size=size, index=index)


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img, "RGBA")

    # Subtle radial vignette (cheap approximation with concentric ellipses)
    for i in range(40, 0, -1):
        alpha = int(2 + i * 0.6)
        pad = int(i * 18)
        draw.ellipse(
            (-pad, -pad, W + pad, H + pad),
            outline=None,
            fill=(166, 218, 255, alpha) if i > 35 else None,
        )

    # Recreate cleaner background since vignette overdid it
    img2 = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img2, "RGBA")

    # Top-left brand lockup: shield mark + wordmark
    logo_height = 64
    logo_png_bytes = cairosvg.svg2png(
        url=str(LOGO_MARK_SVG),
        output_height=logo_height,
        background_color=None,
    )
    logo_img = Image.open(io.BytesIO(logo_png_bytes)).convert("RGBA")
    logo_x, logo_y = 70, 60
    img2.paste(logo_img, (logo_x, logo_y), logo_img)

    # Wordmark next to the shield
    wm_font = load(HELVETICA_BOLD, 32, index=10)  # Medium
    draw.text(
        (logo_x + logo_img.width + 16, logo_y + 16),
        "AI Identity",
        font=wm_font,
        fill=TEXT,
    )

    # Badge — "AI AGENT FORENSICS"
    badge_font = load(HELVETICA_BOLD, 22, index=1)  # Bold
    bx, by = 80, 200
    badge_text = "AI AGENT FORENSICS"
    bw = draw.textlength(badge_text, font=badge_font)
    pad_x = 18
    draw.rounded_rectangle(
        (bx - 2, by - 4, bx + bw + pad_x * 2, by + 38),
        radius=24,
        fill=(166, 218, 255, 26),
        outline=(166, 218, 255, 90),
        width=1,
    )
    draw.text((bx + pad_x, by + 3), badge_text, font=badge_font, fill=ACCENT)

    # Headline — multi-line
    head_font = load(HELVETICA_BOLD, 84, index=1)  # Bold
    italic_font = load(GEORGIA_ITALIC, 100)

    line1 = "Every AI Agent"
    line2_pre = "Leaves a "
    line2_italic = "Trace"

    draw.text((80, 270), line1, font=head_font, fill=TEXT)

    # second line — bold prefix + italic accent
    y2 = 370
    draw.text((80, y2), line2_pre, font=head_font, fill=TEXT)
    pre_w = draw.textlength(line2_pre, font=head_font)
    # Italic accent in serif
    draw.text((80 + pre_w, y2 - 6), line2_italic, font=italic_font, fill=ACCENT)

    # Subhead / strap
    body_font = load(HELVETICA, 26, index=0)
    sub = "Forensic-grade audit trails for autonomous AI."
    sub2 = "Replay any incident. Prove every action. Verify offline."
    draw.text((80, 510), sub, font=body_font, fill=MUTED)
    draw.text((80, 548), sub2, font=body_font, fill=MUTED)

    # Bottom-right: domain mark
    domain_font = load(HELVETICA, 22, index=0)
    domain = "ai-identity.co"
    dw = draw.textlength(domain, font=domain_font)
    draw.text((W - 80 - dw, H - 55), domain, font=domain_font, fill=(120, 135, 155))

    # Subtle bottom accent line
    draw.rectangle((0, H - 4, W, H), fill=(166, 218, 255, 60))

    img2.save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
