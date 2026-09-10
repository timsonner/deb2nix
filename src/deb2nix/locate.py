"""Map DT_NEEDED libraries to nixpkgs attributes."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

from deb2nix.libraries import builtin_pkg_for, is_system_lib, toolchain_map


@dataclass
class MappedLib:
    lib: str
    pkg: str | None
    source: str  # builtin | nix-locate | toolchain | bundled | system | unmapped
    note: str = ""


@dataclass
class MappingResult:
    mapped: list[MappedLib] = field(default_factory=list)
    build_inputs: list[str] = field(default_factory=list)
    unmapped: list[str] = field(default_factory=list)
    bundled: list[str] = field(default_factory=list)
    locate_available: bool = False

    def pkgs_for_inputs(self) -> list[str]:
        pkgs: list[str] = []
        seen: set[str] = set()
        for item in self.mapped:
            if not item.pkg or item.source in {"system", "bundled"}:
                continue
            if item.pkg == "stdenv.cc.cc.lib":
                continue
            if item.pkg not in seen:
                seen.add(item.pkg)
                pkgs.append(item.pkg)
        return pkgs


def map_libraries(
    needed: list[str],
    bundled_names: set[str],
    skip_locate: bool = False,
) -> MappingResult:
    result = MappingResult()
    locate_ok = (not skip_locate) and shutil.which("nix-locate") is not None
    result.locate_available = locate_ok
    for lib in needed:
        if is_system_lib(lib):
            result.mapped.append(MappedLib(lib, None, "system", "provided by glibc/interpreter"))
            continue
        if lib in bundled_names:
            result.bundled.append(lib)
            result.mapped.append(
                MappedLib(lib, None, "bundled", "shipped inside the .deb")
            )
            continue
        pkg = builtin_pkg_for(lib)
        source = "builtin"
        if pkg is None and locate_ok:
            pkg = _nix_locate(lib)
            source = "nix-locate" if pkg else "unmapped"
        if pkg is None:
            result.unmapped.append(lib)
            result.mapped.append(MappedLib(lib, None, "unmapped"))
            continue
        if lib in toolchain_map():
            source = "toolchain"
        result.mapped.append(MappedLib(lib, pkg, source))
    result.build_inputs = result.pkgs_for_inputs()
    return result


def _nix_locate(lib: str) -> str | None:
    candidates = [f"/lib/{lib}", f"/lib64/{lib}", f"/usr/lib/{lib}"]
    for path in candidates:
        pkg = _nix_locate_path(path)
        if pkg:
            return pkg
    return _nix_locate_loose(lib)


def _nix_locate_path(path: str) -> str | None:
    r = subprocess.run(
        [
            "nix-locate",
            "--top-level",
            "--minimal",
            "--at-root",
            "--whole-name",
            path,
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return None
    return _pick_locate_pkg(r.stdout)


def _nix_locate_loose(lib: str) -> str | None:
    r = subprocess.run(
        ["nix-locate", "--top-level", "--minimal", "--whole-name", lib],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return None
    return _pick_locate_pkg(r.stdout)


def _pick_locate_pkg(stdout: str) -> str | None:
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    if not lines:
        return None
    ranked: list[tuple[int, str]] = []
    for line in lines:
        attr = line.split()[0] if line.split() else line
        attr = attr.rstrip("()")
        attr = attr.removesuffix(".out").removesuffix(".lib")
        score = 0
        lower = attr.lower()
        if any(bad in lower for bad in (".debug", ".dev", "stdenv", "busybox", "pkgsMusl")):
            score -= 10
        if attr.count(".") == 0:
            score += 2
        ranked.append((score, attr))
    ranked.sort(reverse=True)
    return ranked[0][1] if ranked else None
