"""Render sample text with the built TTF.

Usage: python -m pixelfont.preview [--scale N]
Writes build/preview.png (Pillow, no antialiasing) and build/preview.html.
Run `python -m pixelfont.build` first.
"""

from __future__ import annotations

import argparse
import html
import sys

from PIL import Image, ImageDraw, ImageFont

from . import bdf
from .config import BUILD_DIR, SOURCE_BDF, load_config

SAMPLE_LINES = [
    "Чуєш їх, доцю, га? Кумедна ж ти, прощайся без ґольфів!",
    "The quick brown fox jumps over the lazy dog.",
    "АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ абвгґдеєжзиіїйклмнопрстуфхцчшщьюя",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz",
    "0123456789 !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ ’«»–—…№",
]


def render_png(ttf_path, out_path, pixel_size: int, line_px: int, scale: int) -> None:
    font = ImageFont.truetype(str(ttf_path), pixel_size * scale)
    pad = 2 * scale
    line_h = line_px * scale
    width = max(int(font.getlength(line)) for line in SAMPLE_LINES) + 2 * pad
    height = line_h * len(SAMPLE_LINES) + 2 * pad
    img = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(img)
    draw.fontmode = "1"  # no antialiasing: every pixel is either ink or paper
    for i, line in enumerate(SAMPLE_LINES):
        draw.text((pad, pad + i * line_h), line, font=font, fill=0)
    img.save(out_path)


def render_html(ttf_name: str, out_path, pixel_size: int) -> None:
    sizes = [pixel_size * k for k in (1, 2, 3, 4)]
    blocks = "\n".join(
        f'<section><h2>{s} px</h2>'
        + "".join(f'<p style="font-size:{s}px">{html.escape(line)}</p>' for line in SAMPLE_LINES)
        + "</section>"
        for s in sizes
    )
    doc = f"""<!doctype html>
<meta charset="utf-8">
<title>{html.escape(ttf_name)} preview</title>
<style>
  @font-face {{ font-family: "Preview"; src: url("{html.escape(ttf_name)}"); }}
  body {{ font-family: "Preview", monospace; margin: 24px; background: #fff; color: #000;
         -webkit-font-smoothing: none; font-smooth: never; }}
  h2 {{ font: 12px system-ui; color: #888; margin: 24px 0 4px; }}
  p {{ margin: 0; line-height: 1.25; white-space: pre; }}
</style>
{blocks}
"""
    out_path.write_text(doc, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=4, help="PNG magnification (default 4)")
    args = ap.parse_args(argv)

    cfg = load_config()
    if not cfg.ttf_path.exists():
        print(f"no {cfg.ttf_path.name} in build/; run python -m pixelfont.build first")
        return 1
    font = bdf.load(SOURCE_BDF)
    png = BUILD_DIR / "preview.png"
    page = BUILD_DIR / "preview.html"
    render_png(cfg.ttf_path, png, cfg.pixel_size, font.ascent + font.descent, args.scale)
    render_html(cfg.ttf_path.name, page, cfg.pixel_size)
    print(f"{png.relative_to(BUILD_DIR.parent)} ({args.scale}x), {page.relative_to(BUILD_DIR.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
