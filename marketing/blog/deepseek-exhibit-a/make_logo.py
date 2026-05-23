"""Generate 300x300 LinkedIn newsletter logos for 'Exhibit A'.

Outputs three variants so Jeff can pick:
  exhibit_a_logo_mark.png       — Big 'A' monogram, deep purple bg
  exhibit_a_logo_stamp.png      — 'EXHIBIT A' stamp-style, deep purple bg
  exhibit_a_logo_tricolumn.png  — Three-card 'Who/Policy/Proof' motif
"""

import glob
import os

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = "/Users/jeffleva/Dev/AI-Identity/marketing/blog/deepseek-exhibit-a"
os.makedirs(OUT_DIR, exist_ok=True)

PURPLE_DEEP = (75, 45, 127)  # #4B2D7F
PURPLE_MID = (107, 79, 160)  # #6B4FA0
PURPLE_SOFT = (167, 139, 250)  # #A78BFA
LAVENDER = (240, 232, 248)  # #F0E8F8
AMBER = (245, 158, 11)  # #F59E0B
WHITE = (255, 255, 255)

SIZE = 300


# Find decent fonts on macOS
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


FONT_BOLD_HEAVY = ["HelveticaNeue.ttc", "Helvetica.ttc", "Arial Bold.ttf", "Arial.ttf"]
FONT_SERIF = ["Georgia Bold.ttf", "Georgia.ttf", "Times New Roman Bold.ttf", "Times.ttc"]


# ---------- variant 1: bold 'A' monogram ----------
def make_mark():
    img = Image.new("RGB", (SIZE, SIZE), PURPLE_DEEP)
    d = ImageDraw.Draw(img)
    # Left lighter-purple accent bar (matches brand)
    d.rectangle([0, 0, 14, SIZE], fill=PURPLE_SOFT)
    # Big serif 'A'
    f_a = find_font(FONT_SERIF, 240)
    text = "A"
    bbox = d.textbbox((0, 0), text, font=f_a)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (SIZE - tw) // 2 - bbox[0] + 6
    y = (SIZE - th) // 2 - bbox[1] - 8
    d.text((x, y), text, font=f_a, fill=WHITE)
    # Tiny eyebrow under A
    f_eb = find_font(FONT_BOLD_HEAVY, 14)
    eb = "EXHIBIT A"
    ebb = d.textbbox((0, 0), eb, font=f_eb)
    ew = ebb[2] - ebb[0]
    d.text(((SIZE - ew) // 2, 252), eb, font=f_eb, fill=PURPLE_SOFT)
    # Amber underline
    d.rectangle([(SIZE - 60) // 2, 274, (SIZE + 60) // 2, 277], fill=AMBER)
    out = os.path.join(OUT_DIR, "exhibit_a_logo_mark.png")
    img.save(out, "PNG")
    return out


# ---------- variant 2: stamp-style ----------
def make_stamp():
    img = Image.new("RGB", (SIZE, SIZE), PURPLE_DEEP)
    d = ImageDraw.Draw(img)
    # Inner border (stamp feel)
    margin = 22
    d.rectangle([margin, margin, SIZE - margin, SIZE - margin], outline=PURPLE_SOFT, width=2)
    # Top eyebrow
    f_eb = find_font(FONT_BOLD_HEAVY, 16)
    eb = "AI IDENTITY"
    ebb = d.textbbox((0, 0), eb, font=f_eb)
    ew = ebb[2] - ebb[0]
    d.text(((SIZE - ew) // 2, 56), eb, font=f_eb, fill=PURPLE_SOFT)
    # Center bold title
    f_t = find_font(FONT_BOLD_HEAVY, 56)
    t1 = "EXHIBIT"
    t1b = d.textbbox((0, 0), t1, font=f_t)
    t1w = t1b[2] - t1b[0]
    d.text(((SIZE - t1w) // 2, 100), t1, font=f_t, fill=WHITE)
    # Big A
    f_a = find_font(FONT_SERIF, 96)
    t2 = "A"
    t2b = d.textbbox((0, 0), t2, font=f_a)
    t2w = t2b[2] - t2b[0]
    d.text(((SIZE - t2w) // 2, 156), t2, font=f_a, fill=AMBER)
    # Amber rule
    d.rectangle([(SIZE - 90) // 2, 244, (SIZE + 90) // 2, 247], fill=AMBER)
    # Bottom tag
    f_bt = find_font(FONT_BOLD_HEAVY, 12)
    bt = "BY JEFF LEVA"
    btb = d.textbbox((0, 0), bt, font=f_bt)
    btw = btb[2] - btb[0]
    d.text(((SIZE - btw) // 2, 258), bt, font=f_bt, fill=PURPLE_SOFT)
    out = os.path.join(OUT_DIR, "exhibit_a_logo_stamp.png")
    img.save(out, "PNG")
    return out


# ---------- variant 3: three-column 'Who/Policy/Proof' ----------
def make_tricolumn():
    img = Image.new("RGB", (SIZE, SIZE), PURPLE_DEEP)
    d = ImageDraw.Draw(img)
    # Left bar
    d.rectangle([0, 0, 12, SIZE], fill=PURPLE_SOFT)
    # Title top
    f_t = find_font(FONT_BOLD_HEAVY, 36)
    t = "EXHIBIT A"
    tb = d.textbbox((0, 0), t, font=f_t)
    tw = tb[2] - tb[0]
    d.text(((SIZE - tw) // 2, 56), t, font=f_t, fill=WHITE)
    # Subtitle
    f_s = find_font(FONT_BOLD_HEAVY, 11)
    s = "IDENTITY  ·  POLICY  ·  PROOF"
    sb = d.textbbox((0, 0), s, font=f_s)
    sw = sb[2] - sb[0]
    d.text(((SIZE - sw) // 2, 102), s, font=f_s, fill=PURPLE_SOFT)
    # Three cards
    card_y, card_h = 138, 90
    pad = 18
    avail = SIZE - 12 - pad * 2
    cw = (avail - 2 * 10) // 3
    labels = ["WHO", "POLICY", "PROOF"]
    f_cl = find_font(FONT_BOLD_HEAVY, 14)
    f_cb = find_font(FONT_BOLD_HEAVY, 11)
    x0 = 12 + pad
    for i, lbl in enumerate(labels):
        x = x0 + i * (cw + 10)
        # translucent fill emulated as slightly lighter purple
        d.rectangle(
            [x, card_y, x + cw, card_y + card_h], outline=PURPLE_SOFT, width=1, fill=(95, 65, 145)
        )
        lb = d.textbbox((0, 0), lbl, font=f_cl)
        lw = lb[2] - lb[0]
        d.text((x + (cw - lw) // 2, card_y + 22), lbl, font=f_cl, fill=AMBER)
        # body
        body = {"WHO": "acted?", "POLICY": "applied?", "PROOF": "remains?"}[lbl]
        bb = d.textbbox((0, 0), body, font=f_cb)
        bw = bb[2] - bb[0]
        d.text((x + (cw - bw) // 2, card_y + 52), body, font=f_cb, fill=WHITE)
    # bottom brand
    f_br = find_font(FONT_BOLD_HEAVY, 11)
    br = "AI  IDENTITY"
    brb = d.textbbox((0, 0), br, font=f_br)
    brw = brb[2] - brb[0]
    d.text(((SIZE - brw) // 2, 254), br, font=f_br, fill=PURPLE_SOFT)
    # amber underline
    d.rectangle([(SIZE - 50) // 2, 274, (SIZE + 50) // 2, 277], fill=AMBER)
    out = os.path.join(OUT_DIR, "exhibit_a_logo_tricolumn.png")
    img.save(out, "PNG")
    return out


paths = [make_mark(), make_stamp(), make_tricolumn()]
for p in paths:
    print("WROTE:", p)
