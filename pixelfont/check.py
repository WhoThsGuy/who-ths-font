"""Sanity checks for the BDF source and the font built from it.

Usage: python -m pixelfont.check   (exit 1 on any problem)
"""

from __future__ import annotations

import sys
import unicodedata

from . import bdf
from .bdf import BdfFont
from .build import build_font
from .config import SOURCE_BDF, Config, load_charset, load_config


def _label(cp: int) -> str:
    ch = chr(cp)
    name = unicodedata.name(ch, "?")
    return f"U+{cp:04X} {ch if ch.isprintable() and not ch.isspace() else ''} ({name})"


def run(cfg: Config, font: BdfFont, charset: list[int]) -> list[str]:
    errors: list[str] = []
    for cp in charset:
        g = font.glyphs.get(cp)
        if g is None:
            errors.append(f"missing glyph {_label(cp)}")
            continue
        if g.is_empty and not chr(cp).isspace():
            errors.append(f"not drawn yet: {_label(cp)}")
        if g.advance <= 0:
            errors.append(f"advance must be positive: {_label(cp)} has {g.advance}")
        if not g.is_empty:
            if g.top > font.ascent:
                errors.append(f"{_label(cp)} rises to {g.top}, above FONT_ASCENT {font.ascent}")
            if g.bottom < -font.descent:
                errors.append(f"{_label(cp)} descends to {g.bottom}, below FONT_DESCENT -{font.descent}")

    ttf = build_font(cfg, font)
    cmap = ttf.getBestCmap()
    for cp in charset:
        if cp in font.glyphs and cp not in cmap:
            errors.append(f"built font lacks cmap entry for {_label(cp)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    cfg = load_config()
    font = bdf.load(SOURCE_BDF)
    charset = load_charset()
    errors = run(cfg, font, charset)
    for e in errors:
        print(f"ERROR: {e}")
    extra = sorted(set(font.glyphs) - set(charset))
    if extra:
        print(f"note: {len(extra)} glyph(s) in BDF beyond charset.txt: "
              + " ".join(f"U+{cp:04X}" for cp in extra))
    drawn = sum(1 for cp in charset if cp in font.glyphs and not font.glyphs[cp].is_empty)
    print(f"{'FAIL' if errors else 'OK'}: {drawn}/{len(charset)} required glyphs drawn, "
          f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
