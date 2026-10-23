from fontTools.ttLib import TTFont

from pixelfont import bdf, check
from pixelfont.build import build_font
from pixelfont.config import SOURCE_BDF, load_charset, load_config
from pixelfont.trace import signed_area


def contours_of(ttf: TTFont, name: str):
    glyf = ttf["glyf"]
    coords, ends, _ = glyf[name].getCoordinates(glyf)
    start = 0
    for end in ends:
        yield [tuple(p) for p in coords[start:end + 1]]
        start = end + 1


def test_source_builds_and_covers_charset():
    cfg = load_config()
    font = bdf.load(SOURCE_BDF)
    ttf = build_font(cfg, font)
    cmap = ttf.getBestCmap()
    assert set(load_charset()) <= set(cmap)
    assert ttf["head"].unitsPerEm == cfg.upm
    assert ttf["head"].flags & (1 << 3)
    assert ttf["gasp"].gaspRange == {0xFFFF: 0}


def test_drawn_glyphs_have_scaled_clockwise_outlines():
    cfg = load_config()
    font = bdf.load(SOURCE_BDF)
    ttf = build_font(cfg, font)
    cmap = ttf.getBestCmap()
    drawn = [g for g in font.glyphs.values() if not g.is_empty]
    assert drawn, "the starter BDF should contain at least one drawn glyph"
    for g in drawn:
        name = cmap[g.codepoint]
        contours = list(contours_of(ttf, name))
        assert contours
        assert any(signed_area(c) < 0 for c in contours)  # at least one outer
        for c in contours:
            assert all(x % cfg.scale == 0 and y % cfg.scale == 0 for x, y in c)
        assert ttf["hmtx"][name][0] == g.advance * cfg.scale


def test_line_metrics_come_from_bdf():
    cfg = load_config()
    font = bdf.load(SOURCE_BDF)
    ttf = build_font(cfg, font)
    assert ttf["hhea"].ascent == font.ascent * cfg.scale
    assert ttf["hhea"].descent == -font.descent * cfg.scale
    assert ttf["OS/2"].sTypoAscender == font.ascent * cfg.scale


def test_check_reports_missing_and_out_of_bounds():
    cfg = load_config()
    font = bdf.load(SOURCE_BDF)
    charset = load_charset()
    assert not [e for e in check.run(cfg, font, charset) if not e.startswith("not drawn yet")]

    del font.glyphs[ord("A")]
    tall = bdf.Glyph.from_ascii(ord("B"), "#\n" * (font.ascent + 1))
    font.glyphs[ord("B")] = tall
    errors = check.run(cfg, font, charset)
    assert any("missing glyph U+0041" in e for e in errors)
    assert any("U+0042" in e and "above FONT_ASCENT" in e for e in errors)
