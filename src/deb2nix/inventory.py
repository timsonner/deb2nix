"""Walk an unpacked .deb data tree."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


SKIP_DIR_NAMES = {".git", "__pycache__"}


@dataclass
class Inventory:
    files: list[str] = field(default_factory=list)
    dirs: list[str] = field(default_factory=list)
    binaries: list[str] = field(default_factory=list)
    desktop_files: list[str] = field(default_factory=list)
    shared_objects: list[str] = field(default_factory=list)
    kernel_modules: list[str] = field(default_factory=list)
    bundled_lib_names: set[str] = field(default_factory=set)

    def has_name(self, name: str) -> bool:
        target = name.lower()
        return any(Path(p).name.lower() == target for p in self.files)

    def has_suffix(self, suffix: str) -> bool:
        return any(p.endswith(suffix) for p in self.files)

    def has_path_part(self, part: str) -> bool:
        needle = part.lower()
        return any(needle in p.lower() for p in self.files + self.dirs)


def rel(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def inventory_tree(data_root: Path) -> Inventory:
    inv = Inventory()
    if not data_root.exists():
        return inv
    for path in sorted(data_root.rglob("*")):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.is_dir():
            inv.dirs.append(rel(data_root, path))
            continue
        if not path.is_file() and not path.is_symlink():
            continue
        rel_path = rel(data_root, path)
        inv.files.append(rel_path)
        name = path.name
        if name.endswith(".desktop"):
            inv.desktop_files.append(rel_path)
        if ".so" in name:
            inv.shared_objects.append(rel_path)
            inv.bundled_lib_names.add(name)
        if name.endswith(".ko"):
            inv.kernel_modules.append(rel_path)
        if path.is_symlink():
            continue
        if path.stat().st_mode & 0o111 and not name.endswith((".so", ".o")):
            inv.binaries.append(rel_path)
    return inv
