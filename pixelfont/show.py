"""Print glyphs from the BDF as ASCII grids.

Usage: python -m pixelfont.show Ї A U+0490 ...
       python -m pixelfont.show --all      (every glyph, drawn or not)
       python -m pixelfont.show --missing  (glyphs in charset.txt still empty)

Each cell shows the full line box: rows from FONT_ASCENT-1 down to -FONT_DESCENT,
the baseline marked with ---, and a | after the advance width.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata

from . import bdf
from .bdf import BdfFont, Glyph
from .config import SOURCE_BDF, load_charset, parse_char_arg


def render(font: BdfFont, g: Glyph) -> str:
    pixels = g.pixels()
    right = max(g.advance, max((x + 1 for x, _ in pixels), default=0))
    top = max(font.ascent, g.top)
    bottom = min(-font.descent, g.bottom)
    ch = chr(g.codepoint)
    shown = ch if ch.isprintable() and not ch.isspace() else ""
    lines = [f"U+{g.codepoint:04X} {shown} {unicodedata.name(ch, '?')}  "
             f"advance {g.advance}  bbx {g.width}x{g.height} at ({g.xoff},{g.yoff})"]
    for y in range(top - 1, bottom - 1, -1):
        row = "".join("#" if (x, y) in pixels else "." for x in range(right))
        row = row[:g.advance] + "|" + row[g.advance:]
        lines.append(f"{y:3d} {row}")
        if y == 0:
            lines.append("    " + "-" * (right + 1))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("chars", nargs="*", help="characters or U+XXXX codepoints")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--missing", action="store_true")
    args = ap.parse_args(argv)

    font = bdf.load(SOURCE_BDF)
    if args.missing:
        missing = [cp for cp in load_charset()
                   if cp not in font.glyphs or (font.glyphs[cp].is_empty and not chr(cp).isspace())]
        print(f"{len(missing)} not drawn: " + " ".join(chr(cp) if chr(cp).isprintable() else f"U+{cp:04X}" for cp in missing))
        return 0
    codepoints = sorted(font.glyphs) if args.all else [parse_char_arg(a) for a in args.chars]
    if not codepoints:
        ap.print_usage()
        return 1
    for cp in codepoints:
        g = font.glyphs.get(cp)
        print(render(font, g) if g else f"U+{cp:04X}: not in {SOURCE_BDF.name}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
