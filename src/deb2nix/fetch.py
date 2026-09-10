"""Download a .deb from a URL or copy a local path."""

from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


def is_url(source: str) -> bool:
    parsed = urlparse(source)
    return parsed.scheme in {"http", "https"}


def fetch_deb(source: str, dest_dir: Path) -> tuple[Path, str | None]:
    """Return (local_deb_path, original_url_or_none)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    if is_url(source):
        name = Path(urlparse(source).path).name or "package.deb"
        if not name.endswith(".deb"):
            name += ".deb"
        dest = dest_dir / name
        _download(source, dest)
        return dest, source
    path = Path(source).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"not a file: {source}")
    if path.suffix != ".deb":
        raise ValueError(f"input must be a .deb file (got {path.name})")
    dest = dest_dir / path.name
    if path != dest:
        shutil.copy2(path, dest)
    return dest, None


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "deb2nix/0.1 (Debian-to-Nix generator)"},
    )
    with urllib.request.urlopen(req) as resp, dest.open("wb") as out:
        shutil.copyfileobj(resp, out)
