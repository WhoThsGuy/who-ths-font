"""Round-trip the source BDF through FontForge, the editor Artem draws in.

Skipped when FontForge is not installed. Guards the one contract that matters
for editing: FontForge must open the file without complaint and give back the
same pixels, advances and line metrics.
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from pixelfont import bdf
from pixelfont.config import SOURCE_BDF

FFPYTHON = next((p for p in (
    Path(r"C:/Program Files/FontForgeBuilds/bin/ffpython.exe"),
    Path(r"C:/Program Files (x86)/FontForgeBuilds/bin/ffpython.exe"),
) if p.exists()), None) or shutil.which("ffpython")

pytestmark = pytest.mark.skipif(FFPYTHON is None, reason="FontForge (ffpython) not installed")


def test_fontforge_opens_and_reexports_identically(tmp_path):
    out = tmp_path / "rt.bdf"
    script = textwrap.dedent(f"""
        import fontforge
        f = fontforge.open({str(SOURCE_BDF)!r})
        print("SIZES", f.bitmapSizes, f.ascent, f.descent)
        f.generate({str(out)!r})
    """)
    proc = subprocess.run([str(FFPYTHON), "-c", script], capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert "PIXEL_SIZE" not in proc.stderr, proc.stderr  # "Various specifications ... do not match"

    src = bdf.load(SOURCE_BDF)
    line_height = src.line_height
    assert f"SIZES ({line_height},) {src.ascent * 1000 // line_height} {src.descent * 1000 // line_height}" in proc.stdout

    exported = next(tmp_path.glob("rt*.bdf"))  # FontForge appends the strike size: rt-10.bdf
    back = bdf.load(exported)
    assert (back.ascent, back.descent) == (src.ascent, src.descent)
    assert set(back.glyphs) == set(src.glyphs)
    for cp, g in src.glyphs.items():
        h = back.glyphs[cp]
        assert h.pixels() == g.pixels(), f"U+{cp:04X} pixels changed"
        assert h.advance == g.advance, f"U+{cp:04X} advance changed"
