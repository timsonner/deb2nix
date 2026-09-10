"""Builtin .so → nixpkgs mapping."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any


@lru_cache(maxsize=1)
def _tables() -> dict[str, Any]:
    text = files("deb2nix.data").joinpath("libraries.json").read_text(encoding="utf-8")
    return json.loads(text)


def system_libs() -> set[str]:
    return set(_tables()["system_libs"])


def toolchain_map() -> dict[str, str]:
    return dict(_tables()["toolchain_libs"])


def lib_to_pkg() -> dict[str, str]:
    return dict(_tables()["lib_to_pkg"])


def is_system_lib(name: str) -> bool:
    return name in system_libs()


def builtin_pkg_for(lib: str) -> str | None:
    if lib in toolchain_map():
        return toolchain_map()[lib]
    return lib_to_pkg().get(lib)
