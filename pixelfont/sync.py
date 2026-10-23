"""Add an empty slot to the BDF for every charset.txt codepoint it lacks.

Usage: python -m pixelfont.sync
Run after extending charset.txt so the new characters show up in FontForge
ready to draw. Existing glyphs are left untouched; nothing is ever removed.
"""

from __future__ import annotations

import sys

from . import bdf
from .bdf import BdfFont, Glyph
from .config import SOURCE_BDF, load_charset

DEFAULT_ADVANCE = 4
DEFAULT_ASCENT = 8
DEFAULT_DESCENT = 2


def sync(font: BdfFont, charset: list[int]) -> list[int]:
    added = []
    for cp in charset:
        if cp not in font.glyphs:
            advance = 3 if chr(cp).isspace() else DEFAULT_ADVANCE
            font.glyphs[cp] = Glyph(cp, advance)
            added.append(cp)
    return added


def main(argv: list[str] | None = None) -> int:
    if SOURCE_BDF.exists():
        font = bdf.load(SOURCE_BDF)
    else:
        font = BdfFont(DEFAULT_ASCENT, DEFAULT_DESCENT)
        print(f"creating {SOURCE_BDF.name} (ascent {DEFAULT_ASCENT}, descent {DEFAULT_DESCENT})")
    added = sync(font, load_charset())
    bdf.save(font, SOURCE_BDF)
    print(f"added {len(added)} empty slot(s); {len(font.glyphs)} glyphs total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
