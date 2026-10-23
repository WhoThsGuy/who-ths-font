# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A proportional 8 px pixel font (Basic Latin + Ukrainian Cyrillic), shipped as a TTF with
square-pixel outlines for games and mods. Glyphs are drawn in the repo's own browser editor
(`python -m pixelfont.edit`); this repo turns the drawing into a font, checks it, and renders
previews. Everything is the `pixelfont` Python package: CLI modules plus one HTML page.

## Source of truth

- `source/font-8.bdf` is the only glyph source. It is plain text (one hex row per pixel row), so
  it can be edited by the editor, by hand, or by Claude directly. FontForge can open it too
  (strike "10 pixel", export is named `<name>-10.bdf`), but Artem found FontForge unusable, so
  it is only a compatibility target, not the workflow. `*.sfd` files are gitignored scratch.
- The BDF strike size (`SIZE`, `PIXEL_SIZE`, the XLFD pixel field) is always
  `FONT_ASCENT + FONT_DESCENT` (currently 10): FontForge requires that and silently zeroes the
  descent otherwise. `bdf.dump` derives it, `bdf.parse` rejects a mismatch. The em (8 px) is a
  separate number that lives only in `font.toml`; the BDF never knows it.
- `[guides]` in `font.toml` (cap_height, x_height) only draws guide lines in the editor.
- `source/charset.txt` lists required codepoints (`U+XXXX` first on each line). `check` fails
  while any of them is missing or still empty.
- `font.toml` holds what BDF cannot: family/style name, version, UPM, `antialias`.
- Line metrics (`FONT_ASCENT`/`FONT_DESCENT`) live in the BDF header and flow into the TTF.
  Do not hardcode them anywhere else. Current starter metrics: ascent 8, descent 2, cap height 7,
  x-height 5, diacritics on Й/Ї use row 7.
- `build/` is generated and gitignored.

## Commands

Use the venv interpreter (`.venv\Scripts\python.exe`, or activate it). Python ≥ 3.11 is required
for `tomllib`.

```
pip install -r requirements.txt
python -m pixelfont.edit             # glyph editor at http://127.0.0.1:8765, saves into the BDF
python -m pixelfont.build            # BDF -> build/WhoThsFont-Regular.ttf
python -m pixelfont.check            # charset coverage + metrics sanity; exit 1 on problems
python -m pixelfont.preview          # build/preview.png (4x, aliased) + build/preview.html
python -m pixelfont.show Ї A U+0490  # print glyphs as ASCII grids with baseline and advance
python -m pixelfont.show --missing   # which required characters are still undrawn
python -m pixelfont.sync             # add empty BDF slots for new charset.txt entries
python -m pytest -q                  # all tests
python -m pytest tests/test_trace.py -k hole
```

`preview` needs a prior `build`. `check` builds in memory and does not write the TTF.

## Pipeline

`bdf.py` parses the BDF into `Glyph` objects whose `pixels()` are in glyph space (baseline y=0,
y up). `trace.py` turns a pixel set into non-overlapping contours: every pixel contributes four
clockwise edges, shared edges cancel, the rest are chained; outer contours come out clockwise and
holes counter-clockwise, as TrueType's non-zero fill expects. At a corner where two pixels touch
diagonally the walk always turns right so the squares stay separate contours. `build.py` scales
those contours by `upm / pixel_size` (1024 / 8 = 128 units per pixel) and assembles the font with
`fontTools.fontBuilder.FontBuilder`, sets `head.flags` bit 3 (integer ppem) and writes a `gasp`
table that disables antialiasing unless `antialias = true`.

`edit.py` is a stdlib `http.server` serving `editor.html` (vanilla JS, no dependencies) with two
endpoints: `GET /api/font` (metrics, guides, charset, pixels per glyph) and `POST /api/save`
(changed glyphs only). Save re-reads the BDF, replaces those glyphs via `Glyph.from_pixels` and
writes it back, so the header and unknown properties survive. The page renders the sample strip
from the pixel data itself, no TTF needed.

Glyph names in the TTF are derived from codepoints (`A`, `uni0407`), never taken from the BDF, because
FontForge exports legacy `afii` names for Cyrillic.

## Rules

- Never downscale. The font is designed at 8 px and is crisp only at integer multiples (16, 24, 32).
  Changing the base size means redrawing, not resizing.
- Adding a character: append it to `charset.txt`, run `sync`, draw it, run `check`.
- Never edit the BDF `SIZE`/`PIXEL_SIZE` lines by hand; change `FONT_ASCENT`/`FONT_DESCENT` and
  re-save through `bdf.save` (e.g. `python -m pixelfont.sync`) so the header stays consistent.
- Tests build the real `source/font-8.bdf`; keep at least one drawn glyph in it. One test
  round-trips the file through FontForge's `ffpython` and is skipped when it is not installed.
