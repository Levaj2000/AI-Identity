"""Cover art for "The Paper Trail Went Public" (LinkedIn article, 2026-08).

Uses the AI Identity Purple system (purple gradient, grain, amber tag, serif
headline, three chips, byline). Deliberately carries NO newsletter branding:
the Exhibit A masthead, the "ISSUE 03" eyebrow, and the ghost 'A' are gone,
since the Buttondown newsletter was retired and this ships as a standalone
LinkedIn article. The hero's watermark is the release version instead; the
square drops it entirely (see build_square).

Outputs (both left untracked — they exceed the repo's 500KB pre-commit limit;
regenerate with `python make_cover.py`):
  paper_trail_cover.png         1200x627   LinkedIn article hero
  paper_trail_cover_square.png  1200x1200  square share / repost tile
"""

import glob
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

PURPLE_DEEP = (75, 45, 127)
PURPLE_DARK = (45, 27, 78)
PURPLE_SOFT = (167, 139, 250)
AMBER = (245, 158, 11)
INK_DARK = (20, 12, 38)
WHITE = (255, 255, 255)
ICE = (230, 220, 251)

SANS_BOLD = ["HelveticaNeue.ttc", "Helvetica.ttc", "Arial Bold.ttf"]
SANS = ["HelveticaNeue.ttc", "Helvetica.ttc", "Arial.ttf"]
SERIF_BOLD = ["Georgia Bold.ttf", "Georgia.ttf", "Times New Roman Bold.ttf"]

EYEBROW = "AI IDENTITY  ·  OPEN STANDARDS"
TAG = "  OCSF  1.9.0  ·  SHIPPED  "
GHOST = "1.9"
TAGLINE = "MAKING AI AGENTS ACCOUNTABLE"
BYLINE = "BY JEFF LEVA  ·  AI-IDENTITY.CO"

# The three pieces that landed, in the order the article argues them.
CHIPS = [("IDENTITY", "who acted"), ("PROOF", "unaltered"), ("OPEN", "anyone verifies")]


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


def draw_chips(d, chips, x0, y0, height, pad_x, gap, label_font, body_font, radius):
    """Row of outlined chips. Returns the x cursor after the last chip."""
    x = x0
    for lbl, body in chips:
        lw, _, _ = text_size(d, lbl, label_font)
        bw, _, _ = text_size(d, body, body_font)
        cw = pad_x + lw + gap + bw + pad_x
        d.rounded_rectangle(
            [x, y0, x + cw, y0 + height],
            radius=radius,
            outline=PURPLE_SOFT,
            width=1,
            fill=(255, 255, 255, 22),
        )
        d.text((x + pad_x - 2, y0 + height // 2 - 8), lbl, font=label_font, fill=AMBER)
        d.text((x + pad_x - 2 + lw + gap, y0 + height // 2 - 10), body, font=body_font, fill=WHITE)
        x += cw + gap
    return x


# ---------- 1200x627 hero ----------
def build_hero():
    w, h = 1200, 627
    img = add_grain(grad_bg(w, h), opacity=10)
    d = ImageDraw.Draw(img, "RGBA")

    d.rectangle([0, 0, 16, h], fill=PURPLE_SOFT)

    # Ghost version number, bottom-right
    f_ghost = find_font(SERIF_BOLD, 200)
    gw, gh, _ = text_size(d, GHOST, f_ghost)
    d.text((w - gw - 60, h - gh - 130), GHOST, font=f_ghost, fill=(167, 139, 250, 34))

    d.ellipse([w - 220, -120, w + 60, 160], fill=(245, 158, 11, 28))

    left = 60
    d.text((left, 60), EYEBROW, font=find_font(SANS_BOLD, 18), fill=PURPLE_SOFT)

    f_tag = find_font(SANS_BOLD, 20)
    tw, th, _ = text_size(d, TAG, f_tag)
    d.rectangle([left, 96, left + tw + 8, 96 + th + 14], fill=AMBER)
    d.text((left + 4, 100), TAG, font=f_tag, fill=INK_DARK)

    f_t = find_font(SERIF_BOLD, 76)
    d.text((left, 168), "The Paper Trail", font=f_t, fill=WHITE)
    d.text((left, 252), "Went Public.", font=f_t, fill=WHITE)

    f_sub = find_font(SANS, 21)
    d.text((left + 2, 360), "Agent attestation shipped in an open standard.", font=f_sub, fill=ICE)
    d.text((left + 2, 389), "Not in our product.", font=f_sub, fill=ICE)

    d.text((left + 2, 438), TAGLINE, font=find_font(SANS_BOLD, 14), fill=AMBER)
    d.rectangle([left + 2, 458, left + 52, 461], fill=AMBER)

    draw_chips(
        d,
        CHIPS,
        left,
        488,
        52,
        22,
        12,
        find_font(SANS_BOLD, 13),
        find_font(SANS, 15),
        12,
    )

    d.text((left, h - 36), BYLINE, font=find_font(SANS_BOLD, 14), fill=PURPLE_SOFT)

    out = os.path.join(OUT_DIR, "paper_trail_cover.png")
    img.save(out, "PNG", optimize=True)
    return out


# ---------- 1200x1200 square ----------
def build_square():
    w, h = 1200, 1200
    img = add_grain(grad_bg(w, h), opacity=10)
    d = ImageDraw.Draw(img, "RGBA")

    d.rectangle([0, 0, 22, h], fill=PURPLE_SOFT)

    # No ghost numeral here: the square tile already carries a three-line
    # headline, subhead, tagline and chip row, and the watermark collided with
    # the chips at every size worth reading. The hero has the negative space.
    d.ellipse([w - 300, -160, w + 80, 220], fill=(245, 158, 11, 22))

    left = 92
    d.text((left, 140), EYEBROW, font=find_font(SANS_BOLD, 22), fill=PURPLE_SOFT)

    f_tag = find_font(SANS_BOLD, 26)
    tw, th, _ = text_size(d, TAG, f_tag)
    d.rectangle([left, 188, left + tw + 10, 188 + th + 16], fill=AMBER)
    d.text((left + 5, 193), TAG, font=f_tag, fill=INK_DARK)

    f_t = find_font(SERIF_BOLD, 104)
    d.text((left, 300), "The Paper", font=f_t, fill=WHITE)
    d.text((left, 414), "Trail Went", font=f_t, fill=WHITE)
    d.text((left, 528), "Public.", font=f_t, fill=WHITE)

    f_sub = find_font(SANS, 29)
    d.text((left + 2, 700), "Agent attestation shipped in an", font=f_sub, fill=ICE)
    d.text((left + 2, 740), "open standard. Not in our product.", font=f_sub, fill=ICE)

    d.text((left + 2, 808), TAGLINE, font=find_font(SANS_BOLD, 18), fill=AMBER)
    d.rectangle([left + 2, 832, left + 72, 836], fill=AMBER)

    draw_chips(
        d,
        CHIPS,
        left,
        880,
        78,
        32,
        18,
        find_font(SANS_BOLD, 18),
        find_font(SANS, 20),
        18,
    )

    d.text((left, h - 80), BYLINE, font=find_font(SANS_BOLD, 22), fill=PURPLE_SOFT)
    d.rectangle([left, h - 90, left + 220, h - 87], fill=AMBER)

    out = os.path.join(OUT_DIR, "paper_trail_cover_square.png")
    img.save(out, "PNG", optimize=True)
    return out


if __name__ == "__main__":
    for path in (build_hero(), build_square()):
        print("WROTE:", path)
