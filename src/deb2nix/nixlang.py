"""Nix string / identifier helpers."""

from __future__ import annotations

import re

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_'-]*$")


def nix_ident(name: str) -> str:
    """Turn a Debian package name into a Nix attribute-safe identifier."""
    cleaned = name.strip().lower()
    cleaned = cleaned.replace("_", "-")
    cleaned = re.sub(r"[^a-z0-9+-]+", "-", cleaned)
    cleaned = cleaned.strip("-")
    if not cleaned:
        cleaned = "deb-package"
    if cleaned[0].isdigit():
        cleaned = "pkg-" + cleaned
    return cleaned


def nix_string(value: str) -> str:
    """Quote a value as a Nix string literal."""
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("${", "\\${")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def nix_indented_string(value: str, indent: str = "    ") -> str:
    """Quote a possibly multi-line value as a Nix indented string."""
    if "\n" not in value and "''" not in value:
        return nix_string(value)
    body = value.replace("''", "'''")
    lines = body.split("\n")
    inner = "\n".join(indent + "  " + line if line else indent for line in lines)
    return f"''\n{inner}\n{indent}''"


def is_nix_ident(name: str) -> bool:
    return bool(_IDENT_RE.match(name))
