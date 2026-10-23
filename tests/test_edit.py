from pixelfont.bdf import BdfFont, Glyph
from pixelfont.config import load_charset, load_config
from pixelfont.edit import apply_json, font_to_json


def test_json_roundtrip_keeps_pixels_and_advance():
    cfg = load_config()
    font = BdfFont(8, 2, {ord("A"): Glyph.from_ascii(ord("A"), "#.#\n###\n#.#"),
                          ord(" "): Glyph(ord(" "), advance=3)})
    data = font_to_json(font, cfg, load_charset())
    assert data["ascent"] == 8 and data["guides"]["cap_height"] == cfg.cap_height
    assert data["glyphs"]["65"]["advance"] == 4
    assert data["glyphs"]["65"]["pixels"] == [[0, 0], [0, 1], [0, 2], [1, 1], [2, 0], [2, 1], [2, 2]]

    back = BdfFont(8, 2)
    changed = apply_json(back, {"glyphs": data["glyphs"]})
    assert sorted(changed) == [32, 65]
    assert back.glyphs[65].pixels() == font.glyphs[65].pixels()
    assert back.glyphs[65].advance == 4 and back.glyphs[32].advance == 3


def test_apply_json_rejects_bad_advance():
    import pytest
    with pytest.raises(ValueError):
        apply_json(BdfFont(8, 2), {"glyphs": {"65": {"advance": 0, "pixels": []}}})
