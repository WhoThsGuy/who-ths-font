"""Browser-based glyph editor for the BDF source.

Usage: python -m pixelfont.edit [--port 8765] [--no-browser]
Serves pixelfont/editor.html on localhost and two JSON endpoints:
  GET  /api/font   the whole font (metrics, guides, charset, glyph pixels)
  POST /api/save   {"glyphs": {"<codepoint>": {"advance": n, "pixels": [[x, y], ...]}}}
Saving rewrites source/font-8.bdf through bdf.save, so the file stays canonical.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import unicodedata
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import bdf
from .bdf import BdfFont, Glyph
from .config import SOURCE_BDF, Config, load_charset, load_config

EDITOR_HTML = Path(__file__).with_name("editor.html")


def font_to_json(font: BdfFont, cfg: Config, charset: list[int]) -> dict:
    glyphs = {}
    for cp, g in font.glyphs.items():
        glyphs[str(cp)] = {
            "advance": g.advance,
            "pixels": [list(p) for p in sorted(g.pixels())],
            "name": unicodedata.name(chr(cp), f"U+{cp:04X}"),
        }
    return {
        "ascent": font.ascent,
        "descent": font.descent,
        "pixel_size": cfg.pixel_size,
        "guides": {"cap_height": cfg.cap_height, "x_height": cfg.x_height},
        "charset": charset,
        "glyphs": glyphs,
        "source": SOURCE_BDF.name,
    }


def apply_json(font: BdfFont, data: dict) -> list[int]:
    """Replace the glyphs listed in ``data["glyphs"]``; returns their codepoints."""
    changed = []
    for key, g in data.get("glyphs", {}).items():
        cp = int(key)
        advance = int(g["advance"])
        if advance <= 0:
            raise ValueError(f"U+{cp:04X}: advance must be positive")
        pixels = {(int(x), int(y)) for x, y in g.get("pixels", [])}
        font.glyphs[cp] = Glyph.from_pixels(cp, pixels, advance)
        changed.append(cp)
    return changed


class Editor:
    def __init__(self, cfg: Config, source: Path, charset: list[int]):
        self.cfg, self.source, self.charset = cfg, source, charset
        self.lock = threading.Lock()

    def get_font(self) -> dict:
        with self.lock:
            return font_to_json(bdf.load(self.source), self.cfg, self.charset)

    def save(self, data: dict) -> dict:
        with self.lock:
            font = bdf.load(self.source)  # re-read so header/properties stay intact
            changed = apply_json(font, data)
            bdf.save(font, self.source)
            drawn = sum(1 for cp in self.charset
                        if cp in font.glyphs and not font.glyphs[cp].is_empty)
        return {"ok": True, "changed": changed, "drawn": drawn, "required": len(self.charset)}


def make_handler(editor: Editor):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, ctype: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, obj) -> None:
            self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")

        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/index.html"):
                self._send(200, EDITOR_HTML.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/font":
                self._json(200, editor.get_font())
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/save":
                self._json(404, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8"))
                self._json(200, editor.save(data))
            except (ValueError, KeyError, TypeError) as exc:
                self._json(400, {"ok": False, "error": str(exc)})

        def log_message(self, fmt, *args) -> None:  # quieter console
            if len(args) >= 2 and "/api/save" in str(args[0]) and str(args[1]) == "200":
                sys.stderr.write("saved %s\n" % editor.source.name)

    return Handler


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)

    editor = Editor(load_config(), SOURCE_BDF, load_charset())
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(editor))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"editing {SOURCE_BDF.relative_to(SOURCE_BDF.parent.parent)} at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
