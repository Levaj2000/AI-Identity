"""Geometry + text-fit QA for a .pptx, plus an approximate raster render.

LibreOffice Impress is unavailable in this container, so instead of converting
to PDF we read the real package with python-pptx and redraw each slide with
PIL using metric-compatible substitutes:

    Calibri     -> Liberation Sans (Arial metrics; wider than Calibri => conservative)
    Cambria     -> Liberation Serif x 1.08 (Cambria runs wider than Times)
    Courier New -> Liberation Mono (metric-identical)

Overflow flags are therefore pessimistic, never optimistic.
"""
import sys
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Emu

EMU = 914400.0
DPI = 110

FONTS = {
    ("Calibri", False, False): ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 1.0),
    ("Calibri", True, False): ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 1.0),
    ("Calibri", False, True): ("/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf", 1.0),
    ("Calibri", True, True): ("/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf", 1.0),
    ("Cambria", False, False): ("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", 1.08),
    ("Cambria", True, False): ("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf", 1.08),
    ("Cambria", False, True): ("/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf", 1.08),
    ("Cambria", True, True): ("/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf", 1.08),
    ("Courier New", False, False): ("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf", 1.0),
    ("Courier New", True, False): ("/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf", 1.0),
    ("Courier New", False, True): ("/usr/share/fonts/truetype/liberation/LiberationMono-Italic.ttf", 1.0),
    ("Courier New", True, True): ("/usr/share/fonts/truetype/liberation/LiberationMono-BoldItalic.ttf", 1.0),
}
_cache = {}


def load(name, bold, italic, pt):
    key = (name, bold, italic, round(pt, 1))
    if key not in _cache:
        path, factor = FONTS.get((name, bold, italic), FONTS[("Calibri", bold, italic)])
        px = max(1, int(round(pt * DPI / 72.0)))
        _cache[key] = (ImageFont.truetype(path, px), factor)
    return _cache[key]


def px(inches):
    return inches * DPI


def rgb(color_fmt):
    try:
        c = color_fmt.rgb
        return (c[0], c[1], c[2])
    except Exception:
        return None


def prst(shape):
    """Preset geometry name from the shape XML (python-pptx only reports AUTO_SHAPE)."""
    try:
        el = shape._element.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}prstGeom")
        return el.get("prst") or ""
    except Exception:
        return ""


def shape_fill(shape):
    try:
        f = shape.fill
        if f.type is not None and f.type == 1:  # solid
            return rgb(f.fore_color)
    except Exception:
        pass
    return None


def shape_line(shape):
    try:
        ln = shape.line
        if ln.fill.type == 1:
            w = ln.width.inches if ln.width else 0.0
            if w <= 0:
                return None
            return rgb(ln.color), max(1, int(round(px(w))))
    except Exception:
        pass
    return None


def wrap(text, font, factor, max_w_px):
    """Greedy wrap; returns list of (line, width_px)."""
    out = []
    for hard in text.split("\n"):
        if not hard:
            out.append(("", 0))
            continue
        words, line = hard.split(" "), ""
        for w in words:
            trial = w if not line else line + " " + w
            tw = font.getlength(trial) * factor
            if tw <= max_w_px or not line:
                line = trial
            else:
                out.append((line, font.getlength(line) * factor))
                line = w
        out.append((line, font.getlength(line) * factor))
    return out


def main(path):
    prs = Presentation(path)
    sw, sh = prs.slide_width / EMU, prs.slide_height / EMU
    problems = []

    for idx, slide in enumerate(prs.slides, 1):
        bg = (255, 255, 255)
        try:
            b = slide.background.fill
            if b.type == 1:
                bg = rgb(b.fore_color) or bg
        except Exception:
            pass

        img = Image.new("RGB", (int(px(sw)), int(px(sh))), bg)
        d = ImageDraw.Draw(img)
        text_boxes = []

        for shape in slide.shapes:
            if shape.left is None:
                continue
            x, y = shape.left / EMU, shape.top / EMU
            w, h = (shape.width or 0) / EMU, (shape.height or 0) / EMU

            # --- draw the shape body -------------------------------------
            fill = shape_fill(shape)
            line = shape_line(shape)
            is_txbox = shape.has_text_frame and getattr(shape, "text", "") != "" and fill is None and line is None
            if (fill or line) and w > 0:
                box = [px(x), px(y), px(x + w), px(y + max(h, 0.004))]
                if h < 0.01:  # a line/hairline
                    d.line([box[0], box[1], box[2], box[1]], fill=(line[0] if line else (150, 150, 150)),
                           width=(line[1] if line else 1))
                else:
                    st = prst(shape)
                    if "ellipse" in st or "OVAL" in st:
                        d.ellipse(box, fill=fill, outline=line[0] if line else None,
                                  width=line[1] if line else 1)
                    else:
                        r = px(0.06) if "round" in st.lower() else 0
                        d.rounded_rectangle(box, radius=r, fill=fill,
                                            outline=line[0] if line else None,
                                            width=line[1] if line else 1)

            # --- bounds check --------------------------------------------
            if w > 0 and h > 0:
                if x < -0.01 or y < -0.01 or x + w > sw + 0.01 or y + h > sh + 0.01:
                    problems.append(f"slide {idx}: shape out of canvas "
                                    f"({x:.2f},{y:.2f},{w:.2f}x{h:.2f}) '{getattr(shape,'text','')[:40]}'")

            # --- draw the text -------------------------------------------
            if not shape.has_text_frame or not shape.text_frame.text.strip():
                continue

            tf = shape.text_frame
            anchor = str(tf.vertical_anchor or "")
            lines_out, total_h, max_line_w = [], 0.0, 0.0
            for para in tf.paragraphs:
                runs = [r for r in para.runs if r.text]
                if not runs:
                    total_h += px(0.12)
                    lines_out.append(None)
                    continue
                r0 = runs[0]
                name = r0.font.name or "Calibli"
                pt = r0.font.size.pt if r0.font.size else 18
                bold = bool(r0.font.bold)
                ital = bool(r0.font.italic)
                col = rgb(r0.font.color) or (0, 0, 0)
                font, factor = load(name, bold, ital, pt)
                ls = para.line_spacing
                if ls is None:
                    line_h = pt * 1.22 * DPI / 72.0
                elif hasattr(ls, "pt"):          # Length -> exact point spacing
                    line_h = ls.pt * DPI / 72.0
                else:                             # float multiple of line height
                    line_h = pt * float(ls) * 1.22 * DPI / 72.0
                al = str(para.alignment or "")
                txt = "".join(r.text for r in runs)
                for ln, lw in wrap(txt, font, factor, px(w) if w else 9999):
                    lines_out.append((ln, lw, font, col, line_h, al))
                    total_h += line_h
                    max_line_w = max(max_line_w, lw)

            box_h = px(h)
            if anchor.startswith("MIDDLE"):
                cy = px(y) + (box_h - total_h) / 2
            elif anchor.startswith("BOTTOM"):
                cy = px(y) + box_h - total_h
            else:
                cy = px(y)
            start_y = cy

            for item in lines_out:
                if item is None:
                    cy += px(0.12)
                    continue
                ln, lw, font, col, line_h, al = item
                if "CENTER" in al:
                    tx = px(x) + (px(w) - lw) / 2
                elif "RIGHT" in al:
                    tx = px(x) + px(w) - lw
                else:
                    tx = px(x)
                d.text((tx, cy + (line_h - font.size) / 2), ln, font=font, fill=col)
                cy += line_h

            text_boxes.append((px(x), start_y, px(x) + max_line_w, cy, shape.text_frame.text[:38]))

            # text taller than its declared box (only meaningful for real boxes)
            if h > 0 and total_h > box_h + px(0.06):
                problems.append(
                    f"slide {idx}: text taller than box by {(total_h-box_h)/DPI:.2f}\" "
                    f"-> '{tf.text[:52]}'")
            if start_y < px(0.28) or cy > px(sh - 0.22):
                problems.append(
                    f"slide {idx}: text near/past canvas edge (y {start_y/DPI:.2f}\"-{cy/DPI:.2f}\") "
                    f"-> '{tf.text[:52]}'")

        # --- text/text overlap ------------------------------------------
        for i in range(len(text_boxes)):
            for j in range(i + 1, len(text_boxes)):
                a, b = text_boxes[i], text_boxes[j]
                ox = min(a[2], b[2]) - max(a[0], b[0])
                oy = min(a[3], b[3]) - max(a[1], b[1])
                if ox > px(0.04) and oy > px(0.04):
                    problems.append(
                        f"slide {idx}: text overlap {ox/DPI:.2f}\"x{oy/DPI:.2f}\" "
                        f"-> '{a[4]}' / '{b[4]}'")

        img.save(f"slide-{idx}.png")

    print(f"canvas {sw}x{sh}in, {len(prs.slides.__iter__.__self__._sldIdLst)} slides")
    if problems:
        print(f"\n{len(problems)} POTENTIAL ISSUE(S):")
        for p in problems:
            print("  -", p)
    else:
        print("\nNo geometry or text-fit issues detected.")


if __name__ == "__main__":
    main(sys.argv[1])
