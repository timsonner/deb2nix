"""SRI / SHA-256 helpers."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path


def sha256_bytes(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def sri_sha256(data: bytes) -> str:
    digest = sha256_bytes(data)
    return "sha256-" + base64.b64encode(digest).decode("ascii")


def sri_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256-" + base64.b64encode(h.digest()).decode("ascii")


def hex_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
