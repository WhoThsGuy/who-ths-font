"""Project paths and font.toml loading."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "font.toml"
SOURCE_BDF = ROOT / "source" / "font-8.bdf"
CHARSET_PATH = ROOT / "source" / "charset.txt"
BUILD_DIR = ROOT / "build"


@dataclass(frozen=True)
class Config:
    family: str
    style: str
    version: str
    copyright: str
    license: str
    license_url: str
    pixel_size: int
    upm: int
    antialias: bool
    cap_height: int = 0  # editor guides only; 0 hides the guide
    x_height: int = 0

    @property
    def scale(self) -> int:
        """Font units per pixel."""
        if self.upm % self.pixel_size:
            raise ValueError(f"upm {self.upm} is not a multiple of pixel_size {self.pixel_size}")
        return self.upm // self.pixel_size

    @property
    def ps_name(self) -> str:
        return f"{self.family.replace(' ', '')}-{self.style.replace(' ', '')}"

    @property
    def ttf_path(self) -> Path:
        return BUILD_DIR / f"{self.ps_name}.ttf"


def load_config(path: Path = CONFIG_PATH) -> Config:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return Config(
        family=data["family"],
        style=data.get("style", "Regular"),
        version=str(data.get("version", "0.1")),
        copyright=data.get("copyright", ""),
        license=data.get("license", ""),
        license_url=data.get("license_url", ""),
        pixel_size=int(data["pixel_size"]),
        upm=int(data.get("upm", 1024)),
        antialias=bool(data.get("antialias", False)),
        cap_height=int(data.get("guides", {}).get("cap_height", 0)),
        x_height=int(data.get("guides", {}).get("x_height", 0)),
    )


def load_charset(path: Path = CHARSET_PATH) -> list[int]:
    """Required codepoints, one ``U+XXXX`` per line; ``#`` starts a comment."""
    out: list[int] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        token = line.split()[0]
        if not token.upper().startswith("U+"):
            raise ValueError(f"charset.txt: expected U+XXXX, got {raw!r}")
        out.append(int(token[2:], 16))
    return out


def parse_char_arg(arg: str) -> int:
    """``Ї`` or ``U+0407`` or ``0x407`` -> codepoint."""
    if len(arg) == 1:
        return ord(arg)
    if arg.upper().startswith("U+"):
        return int(arg[2:], 16)
    return int(arg, 0)
