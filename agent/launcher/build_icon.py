"""Generate a macOS .icns icon for Ada (purple gradient + white A).

Outputs `<repo>/agent/launcher/ada.icns`. Used by `build_launcher.sh` to
construct `Launch Ada.app`. Requires Pillow:

    .venv/bin/pip install Pillow
"""

import os
import subprocess
import sys
import tempfile

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    sys.stderr.write("Pillow is required. Install with: .venv/bin/pip install Pillow\n")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_ICNS = os.path.join(HERE, "ada.icns")


def find_font(size):
    candidates = [
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def render(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded-square background with diagonal gradient (accent-500 → accent-700).
    radius = int(size * 0.225)
    top = (139, 92, 246, 255)  # #8b5cf6
    bot = (109, 40, 217, 255)  # #6d28d9

    # Mask for rounded square.
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size, size), radius=radius, fill=255)

    # Build gradient image then paste with mask.
    grad = Image.new("RGBA", (size, size))
    gd = ImageDraw.Draw(grad)
    for y in range(size):
        t = y / max(1, size - 1)
        # Diagonal feel: bias by x at sample time below.
        gd.line([(0, y), (size, y)], fill=lerp(top, bot, t))
    # Add subtle diagonal highlight.
    hl = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    for x in range(size):
        a = int(40 * (1 - x / size))
        hd.line([(x, 0), (x, size)], fill=(255, 255, 255, a))
    grad = Image.alpha_composite(grad, hl)

    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg.paste(grad, (0, 0), mask)

    # Outer soft shadow under the square (only matters at larger sizes).
    if size >= 64:
        shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            (0, int(size * 0.04), size, size + int(size * 0.04)),
            radius=radius,
            fill=(0, 0, 0, 90),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(size * 0.025))
        out = Image.alpha_composite(shadow, bg)
    else:
        out = bg

    # The 'A'.
    draw = ImageDraw.Draw(out)
    font_size = int(size * 0.62)
    font = find_font(font_size)
    text = "A"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1] - int(size * 0.02)

    # Subtle text shadow.
    if size >= 64:
        shadow_layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
        ImageDraw.Draw(shadow_layer).text(
            (tx, ty + max(1, int(size * 0.01))),
            text,
            font=font,
            fill=(0, 0, 0, 90),
        )
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(size * 0.008))
        out = Image.alpha_composite(out, shadow_layer)
        draw = ImageDraw.Draw(out)

    draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))
    return out


def main():
    with tempfile.TemporaryDirectory() as td:
        iconset = os.path.join(td, "ada.iconset")
        os.makedirs(iconset)
        # Apple's iconutil expects this exact set of filenames.
        spec = [
            (16, "icon_16x16.png"),
            (32, "icon_16x16@2x.png"),
            (32, "icon_32x32.png"),
            (64, "icon_32x32@2x.png"),
            (128, "icon_128x128.png"),
            (256, "icon_128x128@2x.png"),
            (256, "icon_256x256.png"),
            (512, "icon_256x256@2x.png"),
            (512, "icon_512x512.png"),
            (1024, "icon_512x512@2x.png"),
        ]
        cache: dict[int, Image.Image] = {}
        for size, name in spec:
            if size not in cache:
                cache[size] = render(size)
            cache[size].save(os.path.join(iconset, name), "PNG")
        subprocess.run(
            ["iconutil", "-c", "icns", "-o", OUT_ICNS, iconset],
            check=True,
        )
        print(f"wrote {OUT_ICNS} ({os.path.getsize(OUT_ICNS)} bytes)")


if __name__ == "__main__":
    main()
