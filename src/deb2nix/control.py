"""Debian control file parser (RFC822-style)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Control:
    package: str
    version: str
    architecture: str
    maintainer: str = ""
    depends: str = ""
    recommends: str = ""
    suggests: str = ""
    conflicts: str = ""
    provides: str = ""
    section: str = ""
    priority: str = ""
    homepage: str = ""
    description: str = ""
    license: str = ""
    source: str = ""
    raw: dict[str, str] = field(default_factory=dict)

    @property
    def synopsis(self) -> str:
        first = self.description.split("\n", 1)[0].strip()
        return first or self.package

    @property
    def long_description(self) -> str:
        parts = self.description.split("\n", 1)
        if len(parts) == 1:
            return parts[0].strip()
        return parts[1].strip()

    def is_unfree(self) -> bool:
        section = self.section.lower()
        if section.startswith("non-free") or "/non-free" in section:
            return True
        license_l = self.license.lower()
        proprietary_tokens = (
            "proprietary",
            "unfree",
            "commercial",
            "all rights reserved",
            "copyright",
        )
        if license_l and any(tok in license_l for tok in proprietary_tokens):
            return True
        if not self.license and section in {"non-free", "non-free-firmware", "contrib"}:
            return True
        return False


def parse_control_text(text: str) -> Control:
    fields: dict[str, str] = {}
    key: str | None = None
    for raw_line in text.splitlines():
        if not raw_line.strip() and key is None:
            continue
        if raw_line.startswith((" ", "\t")) and key:
            cont = raw_line.strip()
            if cont == ".":
                fields[key] += "\n"
            else:
                fields[key] += "\n" + cont
            continue
        if ":" not in raw_line:
            continue
        k, v = raw_line.split(":", 1)
        key = k.strip()
        fields[key] = v.strip()

    def g(*names: str) -> str:
        for name in names:
            if name in fields:
                return fields[name]
        return ""

    package = g("Package")
    if not package:
        raise ValueError("control file is missing Package")
    return Control(
        package=package,
        version=g("Version") or "0",
        architecture=g("Architecture") or "amd64",
        maintainer=g("Maintainer"),
        depends=g("Depends"),
        recommends=g("Recommends"),
        suggests=g("Suggests"),
        conflicts=g("Conflicts"),
        provides=g("Provides"),
        section=g("Section"),
        priority=g("Priority"),
        homepage=g("Homepage"),
        description=g("Description"),
        license=g("License"),
        source=g("Source"),
        raw=fields,
    )


def parse_control_file(path: Path) -> Control:
    return parse_control_text(path.read_text(encoding="utf-8", errors="replace"))


def debian_arch_to_nix_system(arch: str) -> str:
    mapping = {
        "amd64": "x86_64-linux",
        "x86_64": "x86_64-linux",
        "arm64": "aarch64-linux",
        "aarch64": "aarch64-linux",
        "armhf": "armv7l-linux",
        "i386": "i686-linux",
        "all": "x86_64-linux",
    }
    return mapping.get(arch.lower(), "x86_64-linux")
