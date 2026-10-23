import pytest
import textwrap

from pixelfont import bdf
from pixelfont.bdf import BdfFont, Glyph


def make_font() -> BdfFont:
    a = Glyph.from_ascii(ord("A"), """
.###.
#...#
#####
#...#
""", advance=6)
    p = Glyph.from_ascii(ord("p"), """
##.
#.#
##.
#..
""", yoff=-1)
    space = Glyph(ord(" "), advance=3)
    return BdfFont(7, 2, {g.codepoint: g for g in (a, p, space)},
                   properties={"COPYRIGHT": '"x"'})


def test_roundtrip_preserves_glyphs_and_metrics():
    font = make_font()
    again = bdf.parse(bdf.dump(font))
    assert (again.ascent, again.descent, again.line_height) == (7, 2, 9)
    assert again.properties == {"COPYRIGHT": '"x"'}
    assert set(again.glyphs) == set(font.glyphs)
    for cp, g in font.glyphs.items():
        h = again.glyphs[cp]
        assert (h.advance, h.width, h.height, h.xoff, h.yoff) == (
            g.advance, g.width, g.height, g.xoff, g.yoff)
        assert h.pixels() == g.pixels()


def test_pixels_use_baseline_coordinates():
    p = make_font().glyphs[ord("p")]
    assert p.bottom == -1 and p.top == 3
    assert (0, -1) in p.pixels() and (2, 1) in p.pixels()


def test_from_ascii_default_advance_is_width_plus_one():
    g = Glyph.from_ascii(ord("i"), "#\n#\n#")
    assert g.advance == 2 and g.name == "i"


def test_parse_tolerates_fontforge_style_header():
    text = textwrap.dedent("""\
        STARTFONT 2.1
        FONT -FontForge-PixelUA-Medium-R-Normal--9-90-72-72-P-60-ISO10646-1
        SIZE 9 72 72
        FONTBOUNDINGBOX 6 9 0 -2
        STARTPROPERTIES 3
        FONT_ASCENT 7
        FONT_DESCENT 2
        FAMILY_NAME "PixelUA"
        ENDPROPERTIES
        CHARS 2
        STARTCHAR .notdef
        ENCODING -1
        DWIDTH 6 0
        BBX 0 0 0 0
        BITMAP
        ENDCHAR
        STARTCHAR afii10056
        ENCODING 1031
        SWIDTH 500 0
        DWIDTH 4 0
        BBX 3 8 0 0
        BITMAP
        A0
        00
        E0
        40
        40
        40
        40
        E0
        ENDCHAR
        ENDFONT
    """)
    font = bdf.parse(text)
    assert list(font.glyphs) == [1031]
    g = font.glyphs[1031]
    assert g.name == "afii10056" and g.advance == 4
    assert g.to_ascii() == "#.#\n...\n###\n.#.\n.#.\n.#.\n.#.\n###"
    assert font.properties == {"FAMILY_NAME": '"PixelUA"'}


def test_dump_derives_strike_size_from_ascent_plus_descent():
    text = bdf.dump(BdfFont(8, 2, {ord("A"): Glyph(ord("A"), advance=4)}))
    assert "SIZE 10 72 72" in text
    assert "PIXEL_SIZE 10" in text and "POINT_SIZE 100" in text
    assert "--10-100-72-72-" in text
    assert "FONT_ASCENT 8" in text and "FONT_DESCENT 2" in text


def test_parse_rejects_strike_size_that_fontforge_would_mangle():
    text = bdf.dump(BdfFont(8, 2)).replace("SIZE 10 72 72", "SIZE 8 72 72").replace("PIXEL_SIZE 10", "PIXEL_SIZE 8")
    with pytest.raises(ValueError, match="FontForge requires"):
        bdf.parse(text)
