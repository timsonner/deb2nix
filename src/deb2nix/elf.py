"""ELF DT_NEEDED scanner (readelf / patchelf / magic fallback)."""

from __future__ import annotations

import re
import shutil
import struct
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

ELF_MAGIC = b"\x7fELF"
NEEDED_RE = re.compile(r"Shared library:\s*\[([^\]]+)\]")


@dataclass
class ElfInfo:
    path: str
    needed: list[str] = field(default_factory=list)
    interpreter: str | None = None
    is_elf: bool = False


def is_elf_file(path: Path) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    try:
        with path.open("rb") as fh:
            return fh.read(4) == ELF_MAGIC
    except OSError:
        return False


def scan_tree(data_root: Path) -> list[ElfInfo]:
    results: list[ElfInfo] = []
    if not data_root.exists():
        return results
    for path in sorted(data_root.rglob("*")):
        if not is_elf_file(path):
            continue
        info = scan_file(path, data_root)
        if info.is_elf:
            results.append(info)
    return results


def scan_file(path: Path, root: Path | None = None) -> ElfInfo:
    rel = str(path.relative_to(root)).replace("\\", "/") if root else str(path)
    info = ElfInfo(path=rel, is_elf=True)
    needed = _needed_readelf(path) or _needed_patchelf(path) or _needed_struct(path)
    info.needed = sorted(set(needed))
    info.interpreter = _interp_readelf(path) or _interp_patchelf(path)
    return info


def unique_needed(infos: list[ElfInfo]) -> list[str]:
    libs: set[str] = set()
    for info in infos:
        libs.update(info.needed)
    return sorted(libs)


def _needed_readelf(path: Path) -> list[str] | None:
    exe = shutil.which("readelf")
    if not exe:
        return None
    r = subprocess.run(
        [exe, "-d", str(path)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return None
    return NEEDED_RE.findall(r.stdout)


def _needed_patchelf(path: Path) -> list[str] | None:
    exe = shutil.which("patchelf")
    if not exe:
        return None
    r = subprocess.run(
        [exe, "--print-needed", str(path)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return None
    return [line.strip() for line in r.stdout.splitlines() if line.strip()]


def _interp_readelf(path: Path) -> str | None:
    exe = shutil.which("readelf")
    if not exe:
        return None
    r = subprocess.run(
        [exe, "-l", str(path)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return None
    m = re.search(r"\[Requesting program interpreter:\s*([^\]]+)\]", r.stdout)
    return m.group(1).strip() if m else None


def _interp_patchelf(path: Path) -> str | None:
    exe = shutil.which("patchelf")
    if not exe:
        return None
    r = subprocess.run(
        [exe, "--print-interpreter", str(path)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return None
    val = r.stdout.strip()
    return val or None


def _needed_struct(path: Path) -> list[str]:
    """Minimal ELF DT_NEEDED parser when readelf/patchelf are missing."""
    try:
        data = path.read_bytes()
    except OSError:
        return []
    if data[:4] != ELF_MAGIC or len(data) < 64:
        return []
    ei_class = data[4]
    ei_data = data[5]
    endian = "<" if ei_data == 1 else ">"
    try:
        if ei_class == 2:  # ELF64
            e_shoff = struct.unpack_from(endian + "Q", data, 40)[0]
            e_shentsize = struct.unpack_from(endian + "H", data, 58)[0]
            e_shnum = struct.unpack_from(endian + "H", data, 60)[0]
            e_shstrndx = struct.unpack_from(endian + "H", data, 62)[0]
            return _dt_needed_from_sections(
                data, endian, e_shoff, e_shentsize, e_shnum, e_shstrndx, is64=True
            )
        if ei_class == 1:  # ELF32
            e_shoff = struct.unpack_from(endian + "I", data, 32)[0]
            e_shentsize = struct.unpack_from(endian + "H", data, 46)[0]
            e_shnum = struct.unpack_from(endian + "H", data, 48)[0]
            e_shstrndx = struct.unpack_from(endian + "H", data, 50)[0]
            return _dt_needed_from_sections(
                data, endian, e_shoff, e_shentsize, e_shnum, e_shstrndx, is64=False
            )
    except (struct.error, IndexError, ValueError):
        return []
    return []


def _dt_needed_from_sections(
    data: bytes,
    endian: str,
    e_shoff: int,
    e_shentsize: int,
    e_shnum: int,
    e_shstrndx: int,
    is64: bool,
) -> list[str]:
    if e_shentsize == 0 or e_shnum == 0:
        return []
    sections = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        if is64:
            sh_name, sh_type, _, _, sh_offset, sh_size, sh_link, *_ = struct.unpack_from(
                endian + "IIQQQQIIQQ", data, off
            )
        else:
            sh_name, sh_type, _, _, sh_offset, sh_size, sh_link, *_ = struct.unpack_from(
                endian + "IIIIIIIIII", data, off
            )
        sections.append((sh_name, sh_type, sh_offset, sh_size, sh_link))
    # SHT_DYNAMIC = 6, SHT_STRTAB = 3
    needed: list[str] = []
    for _sh_name, sh_type, sh_offset, sh_size, sh_link in sections:
        if sh_type != 6:
            continue
        dyn = data[sh_offset : sh_offset + sh_size]
        strtab_off = strtab_size = 0
        if 0 <= sh_link < len(sections):
            strtab_off = sections[sh_link][2]
            strtab_size = sections[sh_link][3]
        strtab = data[strtab_off : strtab_off + strtab_size]
        step = 16 if is64 else 8
        for i in range(0, len(dyn) - step + 1, step):
            if is64:
                d_tag, d_val = struct.unpack_from(endian + "qQ", dyn, i)
            else:
                d_tag, d_val = struct.unpack_from(endian + "iI", dyn, i)
            if d_tag == 1:  # DT_NEEDED
                needed.append(_cstr(strtab, d_val))
            if d_tag == 0:
                break
    return [n for n in needed if n]


def _cstr(buf: bytes, offset: int) -> str:
    if offset < 0 or offset >= len(buf):
        return ""
    end = buf.find(b"\x00", offset)
    if end < 0:
        end = len(buf)
    return buf[offset:end].decode("utf-8", errors="replace")
