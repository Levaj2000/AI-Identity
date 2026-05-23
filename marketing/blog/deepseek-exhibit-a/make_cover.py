"""LinkedIn article cover for 'Exhibit A — DeepSeek and the AI Trust Gap'.

Tight composition: everything important sits inside the left/center safe zone
so LinkedIn's article-editor crop doesn't kill content.

Outputs:
  DeepSeek_Exhibit_A_cover.png         1200x627 (LinkedIn article hero)
  DeepSeek_Exhibit_A_cover_square.png  1200x1200 (square share / repost tile)
"""

import glob
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = "/Users/jeffleva/Dev/AI-Identity/marketing/blog/deepseek-exhibit-a"

PURPLE_DEEP = (75, 45, 127)
PURPLE_DARK = (45, 27, 78)
PURPLE_MID = (107, 79, 160)
PURPLE_SOFT = (167, 139, 250)
LAVENDER = (217, 201, 238)
AMBER = (245, 158, 11)
INK_DARK = (20, 12, 38)
WHITE = (255, 255, 255)
ICE = (230, 220, 251)


def find_font(candidates, size):
    paths = [
        "/System/Library/Fonts",
        "/System/Library/Fonts/Supplemental",
        "/Library/Fonts",
    ]
    for c in candidates:
        for p in paths:
            for hit in glob.glob(f"{p}/{c}"):
                try:
                    return ImageFont.truetype(hit, size)
                except Exception:
                    pass
    return ImageFont.load_default()


SANS_BOLD = ["HelveticaNeue.ttc", "Helvetica.ttc", "Arial Bold.ttf"]
SANS = ["HelveticaNeue.ttc", "Helvetica.ttc", "Arial.ttf"]
SERIF_BOLD = ["Georgia Bold.ttf", "Georgia.ttf", "Times New Roman Bold.ttf"]


def grad_bg(w, h):
    img = Image.new("RGB", (w, h), PURPLE_DEEP)
    px = img.load()
    for y in range(h):
        t = y / h
        r = int(PURPLE_DEEP[0] * (1 - t) + PURPLE_DARK[0] * t)
        g = int(PURPLE_DEEP[1] * (1 - t) + PURPLE_DARK[1] * t)
        b = int(PURPLE_DEEP[2] * (1 - t) + PURPLE_DARK[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def add_grain(img, opacity=10):
    w, h = img.size
    noise = Image.new("L", (w, h))
    nd = noise.load()
    for y in range(h):
        for x in range(w):
            nd[x, y] = random.randint(0, 255)
    noise = noise.filter(ImageFilter.GaussianBlur(0.6))
    rgba = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    rgba_d = rgba.load()
    nl = noise.load()
    for y in range(h):
        for x in range(w):
            v = nl[x, y]
            rgba_d[x, y] = (255, 255, 255, int(opacity * (v / 255)))
    return Image.alpha_composite(img.convert("RGBA"), rgba).convert("RGB")


def text_size(d, text, font):
    b = d.textbbox((0, 0), text, font=font)
    return b[2] - b[0], b[3] - b[1], b


# ---------- 1200x627 hero (LinkedIn article cover) ----------
def build_hero():
    W, H = 1200, 627  # noqa: N806 — canvas dimensions, conventional shorthand
    img = grad_bg(W, H)
    img = add_grain(img, opacity=10)
    d = ImageDraw.Draw(img, "RGBA")

    # Left accent bar
    d.rectangle([0, 0, 16, H], fill=PURPLE_SOFT)

    # Decorative right-side faint "EXHIBIT A" wordmark (won't matter if cropped)
    f_ghost = find_font(SERIF_BOLD, 220)
    ghost_text = "A"
    gw, gh, gb = text_size(d, ghost_text, f_ghost)
    d.text((W - gw - 60, H - gh - 120), ghost_text, font=f_ghost, fill=(167, 139, 250, 38))

    # Soft amber accent dot (top-right decorative)
    d.ellipse([W - 220, -120, W + 60, 160], fill=(245, 158, 11, 28))

    # ---- HERO TEXT (left 75% safe zone) ----
    LEFT = 60  # noqa: N806 — layout constant, conventional uppercase
    # Eyebrow
    f_eb = find_font(SANS_BOLD, 18)
    d.text((LEFT, 60), "AI IDENTITY  ·  ISSUE 01  ·  EXHIBIT A", font=f_eb, fill=PURPLE_SOFT)

    # Amber EXHIBIT A tag
    tag_x, tag_y = LEFT, 96
    f_tag = find_font(SANS_BOLD, 20)
    tag_text = "  EXHIBIT  A  ·  01  "
    tw, th, _ = text_size(d, tag_text, f_tag)
    d.rectangle([tag_x, tag_y, tag_x + tw + 8, tag_y + th + 14], fill=AMBER)
    d.text((tag_x + 4, tag_y + 4), tag_text, font=f_tag, fill=INK_DARK)

    # Title (big serif) — left-aligned, two lines
    f_t = find_font(SERIF_BOLD, 78)
    d.text((LEFT, 168), "DeepSeek and the", font=f_t, fill=WHITE)
    d.text((LEFT, 254), "AI Trust Gap.", font=f_t, fill=WHITE)

    # Sub-deck
    f_sub = find_font(SANS, 21)
    d.text((LEFT + 2, 362), "Why every powerful model now needs an identity,", font=f_sub, fill=ICE)
    d.text((LEFT + 2, 391), "a policy, and a paper trail.", font=f_sub, fill=ICE)

    # Tagline strip (newsletter mission)
    f_tl = find_font(SANS_BOLD, 14)
    d.text((LEFT + 2, 438), "MAKING AI AGENTS ACCOUNTABLE", font=f_tl, fill=AMBER)
    d.rectangle([LEFT + 2, 458, LEFT + 2 + 50, 461], fill=AMBER)

    # Three chips — under the tagline, left-aligned, compact
    chip_y = 488
    chip_h = 52
    chip_gap = 12
    chips = [("WHO", "acted?"), ("POLICY", "applied?"), ("PROOF", "remains?")]
    f_chip_l = find_font(SANS_BOLD, 13)
    f_chip_b = find_font(SANS, 15)
    chip_x = LEFT
    for lbl, body in chips:
        lw, _, _ = text_size(d, lbl, f_chip_l)
        bw, _, _ = text_size(d, body, f_chip_b)
        cw = 22 + lw + 12 + bw + 22
        d.rounded_rectangle(
            [chip_x, chip_y, chip_x + cw, chip_y + chip_h],
            radius=12,
            outline=PURPLE_SOFT,
            width=1,
            fill=(255, 255, 255, 22),
        )
        d.text((chip_x + 20, chip_y + 18), lbl, font=f_chip_l, fill=AMBER)
        d.text((chip_x + 20 + lw + 12, chip_y + 16), body, font=f_chip_b, fill=WHITE)
        chip_x += cw + chip_gap

    # Footer byline (bottom-left so it never clips)
    f_by = find_font(SANS_BOLD, 14)
    d.text((LEFT, H - 36), "BY JEFF LEVA  ·  AI-IDENTITY.CO", font=f_by, fill=PURPLE_SOFT)

    out = os.path.join(OUT_DIR, "DeepSeek_Exhibit_A_cover.png")
    img.save(out, "PNG")
    return out


# ---------- 1200x1200 square ----------
def build_square():
    W, H = 1200, 1200  # noqa: N806 — canvas dimensions, conventional shorthand
    img = grad_bg(W, H)
    img = add_grain(img, opacity=10)
    d = ImageDraw.Draw(img, "RGBA")

    d.rectangle([0, 0, 22, H], fill=PURPLE_SOFT)

    # Faint background 'A'
    f_ghost = find_font(SERIF_BOLD, 520)
    gw, gh, gb = text_size(d, "A", f_ghost)
    d.text((W - gw - 40, H - gh - 60), "A", font=f_ghost, fill=(167, 139, 250, 30))

    LEFT = 92  # noqa: N806 — layout constant, conventional uppercase
    f_eb = find_font(SANS_BOLD, 22)
    d.text((LEFT, 140), "AI IDENTITY  ·  ISSUE 01", font=f_eb, fill=PURPLE_SOFT)

    tag_x, tag_y = LEFT, 188
    f_tag = find_font(SANS_BOLD, 26)
    tag_text = "  EXHIBIT  A  "
    tw, th, _ = text_size(d, tag_text, f_tag)
    d.rectangle([tag_x, tag_y, tag_x + tw + 10, tag_y + th + 16], fill=AMBER)
    d.text((tag_x + 5, tag_y + 5), tag_text, font=f_tag, fill=INK_DARK)

    f_t = find_font(SERIF_BOLD, 110)
    d.text((LEFT, 290), "DeepSeek", font=f_t, fill=WHITE)
    d.text((LEFT, 410), "and the", font=f_t, fill=WHITE)
    d.text((LEFT, 530), "AI Trust Gap.", font=f_t, fill=WHITE)

    f_sub = find_font(SANS, 30)
    d.text((LEFT + 2, 700), "Why every powerful model now needs an identity,", font=f_sub, fill=ICE)
    d.text((LEFT + 2, 740), "a policy, and a paper trail.", font=f_sub, fill=ICE)

    # tagline
    f_tl = find_font(SANS_BOLD, 18)
    d.text((LEFT + 2, 808), "MAKING AI AGENTS ACCOUNTABLE", font=f_tl, fill=AMBER)
    d.rectangle([LEFT + 2, 832, LEFT + 2 + 70, 836], fill=AMBER)

    # chips
    chip_y = 880
    chip_h = 78
    chips = [("WHO", "acted?"), ("POLICY", "applied?"), ("PROOF", "remains?")]
    f_chip_l = find_font(SANS_BOLD, 18)
    f_chip_b = find_font(SANS, 20)
    chip_x = LEFT
    for lbl, body in chips:
        lw, _, _ = text_size(d, lbl, f_chip_l)
        bw, _, _ = text_size(d, body, f_chip_b)
        cw = 32 + lw + 18 + bw + 32
        d.rounded_rectangle(
            [chip_x, chip_y, chip_x + cw, chip_y + chip_h],
            radius=18,
            outline=PURPLE_SOFT,
            width=1,
            fill=(255, 255, 255, 22),
        )
        d.text((chip_x + 28, chip_y + 28), lbl, font=f_chip_l, fill=AMBER)
        d.text((chip_x + 28 + lw + 18, chip_y + 26), body, font=f_chip_b, fill=WHITE)
        chip_x += cw + 18

    f_by = find_font(SANS_BOLD, 22)
    d.text((LEFT, H - 80), "BY JEFF LEVA  ·  AI-IDENTITY.CO", font=f_by, fill=PURPLE_SOFT)
    d.rectangle([LEFT, H - 90, LEFT + 220, H - 87], fill=AMBER)

    out = os.path.join(OUT_DIR, "DeepSeek_Exhibit_A_cover_square.png")
    img.save(out, "PNG")
    return out


paths = [build_hero(), build_square()]
for p in paths:
    print("WROTE:", p)
