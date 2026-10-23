"""BDF + font.toml -> TrueType font with square-pixel outlines.

Usage: python -m pixelfont.build  (writes build/<Family>-<Style>.ttf)
"""

from __future__ import annotations

import sys

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable

from . import bdf
from .bdf import BdfFont, Glyph, glyph_name
from .config import BUILD_DIR, SOURCE_BDF, Config, load_config
from .trace import trace


def _outline(pixels: set[tuple[int, int]], scale: int):
    pen = TTGlyphPen(None)
    for contour in trace(pixels):
        pen.moveTo((contour[0][0] * scale, contour[0][1] * scale))
        for x, y in contour[1:]:
            pen.lineTo((x * scale, y * scale))
        pen.closePath()
    return pen.glyph()


def _notdef(font: BdfFont) -> Glyph:
    """Hollow box, cap height tall, so missing characters are visible."""
    width, height = 4, max(font.ascent, 2)
    pixels = {(x, y) for x in range(width) for y in range(height)
              if x in (0, width - 1) or y in (0, height - 1)}
    return Glyph.from_pixels(0, pixels, advance=width + 1)


def build_font(cfg: Config, font: BdfFont) -> TTFont:
    scale = cfg.scale  # em comes from font.toml; the BDF only knows ascent/descent

    order = [".notdef"]
    glyphs = {}
    metrics = {}
    cmap: dict[int, str] = {}

    def add(name: str, g: Glyph) -> None:
        pixels = g.pixels()
        glyphs[name] = _outline(pixels, scale)
        lsb = min((x for x, _ in pixels), default=0) * scale
        metrics[name] = (g.advance * scale, lsb)

    add(".notdef", _notdef(font))
    for g in font.sorted_glyphs():
        name = glyph_name(g.codepoint)  # ignore BDF names: FontForge may use afii/legacy ones
        order.append(name)
        cmap[g.codepoint] = name
        add(name, g)

    ascent, descent = font.ascent * scale, font.descent * scale

    def top_of(cp: int) -> int:
        g = font.glyphs.get(cp)
        return g.top * scale if g and not g.is_empty else 0

    fb = FontBuilder(cfg.upm, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ascent, descent=-descent, lineGap=0)
    fb.setupNameTable({
        "familyName": cfg.family,
        "styleName": cfg.style,
        "psName": cfg.ps_name,
        "fullName": f"{cfg.family} {cfg.style}",
        "uniqueFontIdentifier": f"{cfg.ps_name}:{cfg.version}",
        "version": f"Version {cfg.version}",
        "copyright": cfg.copyright,
    })
    fb.setupOS2(
        version=4,
        sTypoAscender=ascent, sTypoDescender=-descent, sTypoLineGap=0,
        usWinAscent=ascent, usWinDescent=descent,
        fsSelection=(1 << 6) | (1 << 7),  # REGULAR | USE_TYPO_METRICS
        fsType=0,
        sxHeight=top_of(ord("x")), sCapHeight=top_of(ord("H")),
        achVendID="PXUA",
    )
    fb.setupPost()

    head = fb.font["head"]
    head.flags |= 1 << 3  # force ppem to integers: keeps the pixel grid exact
    head.lowestRecPPEM = cfg.pixel_size

    gasp = newTable("gasp")
    gasp.version = 1
    gasp.gaspRange = {0xFFFF: 0x0F if cfg.antialias else 0x00}
    fb.font["gasp"] = gasp
    return fb.font


def main(argv: list[str] | None = None) -> int:
    cfg = load_config()
    font = bdf.load(SOURCE_BDF)
    ttf = build_font(cfg, font)
    BUILD_DIR.mkdir(exist_ok=True)
    ttf.save(cfg.ttf_path)
    drawn = sum(1 for g in font.glyphs.values() if not g.is_empty)
    print(f"{cfg.ttf_path.relative_to(BUILD_DIR.parent)}: {len(font.glyphs)} glyphs, {drawn} drawn")
    return 0


if __name__ == "__main__":
    sys.exit(main())
