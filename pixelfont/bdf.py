"""Minimal BDF 2.1 reader/writer.

The BDF file is the font's source of truth. Only the fields the build needs are
modelled; unknown properties are preserved so FontForge round-trips survive.

Coordinates: a glyph's pixels are reported in "glyph space" with the baseline at
y=0 and y growing upwards, matching TrueType. The BDF BITMAP block lists rows
top-first, so row 0 of the bitmap is the glyph's topmost pixel row.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fontTools import agl


def glyph_name(codepoint: int) -> str:
    """Adobe Glyph List name when there is one, else ``uniXXXX``."""
    return agl.UV2AGL.get(codepoint) or f"uni{codepoint:04X}"


@dataclass
class Glyph:
    codepoint: int
    advance: int
    width: int = 0
    height: int = 0
    xoff: int = 0
    yoff: int = 0
    rows: list[list[bool]] = field(default_factory=list)  # top row first
    name: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            self.name = glyph_name(self.codepoint)
        if len(self.rows) != self.height or any(len(r) != self.width for r in self.rows):
            raise ValueError(f"{self.name}: bitmap does not match BBX {self.width}x{self.height}")

    @classmethod
    def from_ascii(cls, codepoint: int, art: str, advance: int | None = None,
                   xoff: int = 0, yoff: int = 0, on: str = "#") -> "Glyph":
        """Build a glyph from an ASCII grid; ``on`` marks a filled pixel.

        ``yoff`` is the y of the bottom row (0 = sits on the baseline,
        negative = descends below it). ``advance`` defaults to width + 1.
        """
        lines = art.strip("\n").splitlines()
        width = max((len(ln) for ln in lines), default=0)
        rows = [[c == on for c in ln.ljust(width)] for ln in lines]
        if advance is None:
            advance = width + 1
        return cls(codepoint, advance, width, len(rows), xoff, yoff, rows)

    @classmethod
    def from_pixels(cls, codepoint: int, pixels: set[tuple[int, int]],
                    advance: int) -> "Glyph":
        """Build a glyph from glyph-space pixel coordinates; BBX is tight."""
        if not pixels:
            return cls(codepoint, advance)
        xs = [x for x, _ in pixels]
        ys = [y for _, y in pixels]
        xoff, yoff = min(xs), min(ys)
        width, height = max(xs) - xoff + 1, max(ys) - yoff + 1
        rows = [[(xoff + c, yoff + height - 1 - r) in pixels for c in range(width)]
                for r in range(height)]
        return cls(codepoint, advance, width, height, xoff, yoff, rows)

    def pixels(self) -> set[tuple[int, int]]:
        """Filled pixels in glyph space (baseline y=0, y up)."""
        out: set[tuple[int, int]] = set()
        for r, row in enumerate(self.rows):
            y = self.yoff + self.height - 1 - r
            for c, on in enumerate(row):
                if on:
                    out.add((self.xoff + c, y))
        return out

    @property
    def is_empty(self) -> bool:
        return not any(any(row) for row in self.rows)

    @property
    def top(self) -> int:
        """One above the highest filled row (0 for an empty glyph)."""
        return max((y for _, y in self.pixels()), default=-1) + 1

    @property
    def bottom(self) -> int:
        """Lowest filled row (0 for an empty glyph)."""
        return min((y for _, y in self.pixels()), default=0)

    def to_ascii(self, on: str = "#", off: str = ".") -> str:
        return "\n".join("".join(on if p else off for p in row) for row in self.rows)


@dataclass
class BdfFont:
    """A bitmap strike. FontForge requires the strike's pixel size to equal
    ascent + descent, so the BDF SIZE/PIXEL_SIZE fields are always derived from
    those two and never stored separately. The em of the built TTF is a
    different number and lives in font.toml.
    """

    ascent: int
    descent: int
    glyphs: dict[int, Glyph] = field(default_factory=dict)
    font_name: str = ""
    properties: dict[str, str] = field(default_factory=dict)  # verbatim, minus the ones we own

    OWNED_PROPERTIES = ("FONT_ASCENT", "FONT_DESCENT", "PIXEL_SIZE", "POINT_SIZE",
                        "RESOLUTION_X", "RESOLUTION_Y", "CHARSET_REGISTRY", "CHARSET_ENCODING")

    @property
    def line_height(self) -> int:
        return self.ascent + self.descent

    def sorted_glyphs(self) -> list[Glyph]:
        return [self.glyphs[cp] for cp in sorted(self.glyphs)]


# --------------------------------------------------------------------------- parse

def parse(text: str) -> BdfFont:
    lines = text.splitlines()
    i = 0
    pixel_size = None
    bbox_h = bbox_y = None
    font_name = ""
    props: dict[str, str] = {}
    glyphs: dict[int, Glyph] = {}

    while i < len(lines):
        t = lines[i].split()
        if not t:
            i += 1
            continue
        key = t[0]
        if key == "FONT":
            font_name = lines[i][len("FONT"):].strip()
        elif key == "SIZE":
            pt, ydpi = int(t[1]), int(t[3])
            pixel_size = round(pt * ydpi / 72)
        elif key == "FONTBOUNDINGBOX":
            bbox_h, bbox_y = int(t[2]), int(t[4])
        elif key == "STARTPROPERTIES":
            i += 1
            while i < len(lines) and not lines[i].startswith("ENDPROPERTIES"):
                kv = lines[i].split(None, 1)
                if len(kv) == 2:
                    props[kv[0]] = kv[1].strip()
                i += 1
        elif key == "STARTCHAR":
            i, glyph = _parse_char(lines, i)
            if glyph is not None:
                glyphs[glyph.codepoint] = glyph
            continue
        i += 1

    if "PIXEL_SIZE" in props:
        pixel_size = int(props["PIXEL_SIZE"])
    ascent = int(props["FONT_ASCENT"]) if "FONT_ASCENT" in props else None
    descent = int(props["FONT_DESCENT"]) if "FONT_DESCENT" in props else None
    if ascent is None or descent is None:
        if bbox_h is None:
            raise ValueError("BDF has neither FONT_ASCENT/FONT_DESCENT nor FONTBOUNDINGBOX")
        descent = -bbox_y if descent is None else descent
        ascent = bbox_h + bbox_y if ascent is None else ascent
    if pixel_size is not None and pixel_size != ascent + descent:
        raise ValueError(
            f"BDF pixel size {pixel_size} != FONT_ASCENT {ascent} + FONT_DESCENT {descent}; "
            "FontForge requires them to be equal. Fix the header (or re-save with bdf.save).")
    for k in BdfFont.OWNED_PROPERTIES:
        props.pop(k, None)
    return BdfFont(ascent, descent, glyphs, font_name, props)


def _parse_char(lines: list[str], i: int) -> tuple[int, Glyph | None]:
    head = lines[i].split(None, 1)
    name = head[1].strip() if len(head) == 2 else ""
    codepoint = -1
    advance = 0
    width = height = xoff = yoff = 0
    rows: list[list[bool]] = []
    i += 1
    while i < len(lines):
        t = lines[i].split()
        if not t:
            i += 1
            continue
        key = t[0]
        if key == "ENCODING":
            codepoint = int(t[1])
            if codepoint == -1 and len(t) > 2:
                codepoint = int(t[2])
        elif key == "DWIDTH":
            advance = int(t[1])
        elif key == "BBX":
            width, height, xoff, yoff = (int(v) for v in t[1:5])
        elif key == "BITMAP":
            i += 1
            for _ in range(height):
                hexrow = lines[i].strip()
                bits = bin(int(hexrow, 16))[2:].zfill(len(hexrow) * 4)
                rows.append([b == "1" for b in bits[:width]])
                i += 1
            continue
        elif key == "ENDCHAR":
            i += 1
            break
        i += 1
    if codepoint < 0:
        return i, None  # unencoded glyph; FontForge exports these for e.g. .notdef
    return i, Glyph(codepoint, advance, width, height, xoff, yoff, rows, name)


# ---------------------------------------------------------------------------- dump

def dump(font: BdfFont) -> str:
    glyphs = font.sorted_glyphs()
    drawn = [g for g in glyphs if not g.is_empty]
    lh = font.line_height
    bbox_right = max((g.xoff + g.width for g in drawn), default=lh)
    bbox_x = min((g.xoff for g in drawn), default=0)
    xlfd = f"-misc-pixelfont-medium-r-normal--{lh}-{lh * 10}-72-72-p-0-iso10646-1"
    out = [
        "STARTFONT 2.1",
        f"FONT {xlfd}",
        f"SIZE {lh} 72 72",
        f"FONTBOUNDINGBOX {bbox_right - bbox_x} {lh} {bbox_x} {-font.descent}",
    ]
    props = {
        "PIXEL_SIZE": str(lh),
        "POINT_SIZE": str(lh * 10),
        "RESOLUTION_X": "72",
        "RESOLUTION_Y": "72",
        "FONT_ASCENT": str(font.ascent),
        "FONT_DESCENT": str(font.descent),
        # Without these FontForge assumes Latin-1 and exports every codepoint
        # above U+00FF as ENCODING -1, i.e. drops the Cyrillic.
        "CHARSET_REGISTRY": '"ISO10646"',
        "CHARSET_ENCODING": '"1"',
        **font.properties,
    }
    out.append(f"STARTPROPERTIES {len(props)}")
    out.extend(f"{k} {v}" for k, v in props.items())
    out.append("ENDPROPERTIES")
    out.append(f"CHARS {len(glyphs)}")
    for g in glyphs:
        out.append(f"STARTCHAR {g.name}")
        out.append(f"ENCODING {g.codepoint}")
        out.append(f"SWIDTH {g.advance * 1000 // lh} 0")
        out.append(f"DWIDTH {g.advance} 0")
        out.append(f"BBX {g.width} {g.height} {g.xoff} {g.yoff}")
        out.append("BITMAP")
        nbytes = (g.width + 7) // 8
        for row in g.rows:
            bits = "".join("1" if p else "0" for p in row).ljust(nbytes * 8, "0")
            out.append(f"{int(bits, 2):0{nbytes * 2}X}")
        out.append("ENDCHAR")
    out.append("ENDFONT")
    return "\n".join(out) + "\n"


def load(path: str | Path) -> BdfFont:
    return parse(Path(path).read_text(encoding="utf-8"))


def save(font: BdfFont, path: str | Path) -> None:
    Path(path).write_text(dump(font), encoding="utf-8", newline="\n")
