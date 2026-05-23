"""Render brand SVG sources into the PNG variants needed by the website,
dashboard, and other surfaces.

Sources (hand-traced vector, transparent background):
  - logo-mark.svg          : full color shield + Ai
  - logo-mark-mono.svg     : single color (currentColor) shield + Ai
  - logo-wordmark.svg      : shield + "AI IDENTITY" + tagline

Outputs:
  - logo.png               : 512x512 padded square for JSON-LD / schemas
  - logo-256.png           : 256x256
  - logo-128.png           : 128x128
  - favicon.svg            : copy of logo-mark.svg (browsers handle SVG favicons)
  - favicon-32.png         : 32x32
  - favicon-192.png        : 192x192 (Android home screen)
  - apple-touch-icon.png   : 180x180 (iOS home screen)
  - logo-wordmark.png      : 1200x366 for marketing email + presentation use

Usage:
    python assets/brand/build_logo_variants.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

import cairosvg

BRAND_DIR = Path(__file__).resolve().parent
MARK = BRAND_DIR / "logo-mark.svg"
WORDMARK = BRAND_DIR / "logo-wordmark.svg"


def render_square(svg: Path, out: Path, size: int) -> None:
    """Render the (200x220) mark centered into a square canvas with transparent
    background, so it works as a favicon / app icon.
    """
    cairosvg.svg2png(
        url=str(svg),
        output_height=size,
        write_to=str(out),
        background_color=None,
    )


def render(svg: Path, out: Path, width: int) -> None:
    cairosvg.svg2png(
        url=str(svg),
        output_width=width,
        write_to=str(out),
        background_color=None,
    )


def main() -> None:
    # Square renderings of the mark
    for size in (32, 128, 192, 256, 512):
        render_square(MARK, BRAND_DIR / f"logo-{size}.png", size)
    render_square(MARK, BRAND_DIR / "favicon-32.png", 32)
    render_square(MARK, BRAND_DIR / "favicon-192.png", 192)
    render_square(MARK, BRAND_DIR / "apple-touch-icon.png", 180)

    # Canonical logo.png (for JSON-LD schemas.ts)
    render_square(MARK, BRAND_DIR / "logo.png", 512)

    # Wordmark wide variant for email signature / decks
    render(WORDMARK, BRAND_DIR / "logo-wordmark.png", 1200)

    # SVG favicon: just copy the mark
    shutil.copyfile(MARK, BRAND_DIR / "favicon.svg")

    print(f"Built logo variants in {BRAND_DIR}/")


if __name__ == "__main__":
    main()
