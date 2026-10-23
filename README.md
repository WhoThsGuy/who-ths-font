# Who Ths Font (WTFont)

A proportional 8 px pixel font covering Basic Latin and Ukrainian Cyrillic,
built as a TrueType font with square-pixel outlines for use in games and mods.

## Workflow

1. `python -m pixelfont.edit` opens the glyph editor in your browser. Pick a
   character, paint pixels (left button draws, right erases), set the advance
   width, Ctrl+S saves straight into `source/font-8.bdf`.
2. `python -m pixelfont.build` → `build/WhoThsFont-Regular.ttf`
3. `python -m pixelfont.check` lists characters that are still missing or undrawn.
4. `python -m pixelfont.preview` → `build/preview.png` and `build/preview.html`

Setup once:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

The font is designed at 8 px and stays crisp at 16, 24, 32 px and other
integer multiples. Do not use it at sizes in between.

## License

- The font (everything under `source/` and the built TTF) is licensed under the
  [SIL Open Font License 1.1](OFL.txt). You may bundle it with games and mods,
  commercial or not, modify it and redistribute it; derived fonts stay under the
  OFL and must not use the reserved name "Who Ths Font".
- The tooling (`pixelfont/`, `tests/`) is licensed under the [MIT License](LICENSE).
