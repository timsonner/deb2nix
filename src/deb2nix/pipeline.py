"""End-to-end: fetch → unpack → classify → emit."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from deb2nix.classify import Classification, classify
from deb2nix.control import Control, debian_arch_to_nix_system, parse_control_file
from deb2nix.elf import scan_tree, unique_needed
from deb2nix.emit import EmitContext, emit_all, guess_main_program, license_expr_for
from deb2nix.fetch import fetch_deb
from deb2nix.hashutil import sri_file
from deb2nix.inventory import Inventory, inventory_tree
from deb2nix.locate import MappingResult, map_libraries
from deb2nix.nixlang import nix_ident
from deb2nix.unpack import unpack_deb


@dataclass
class RunResult:
    out_dir: Path
    written: list[Path]
    control: Control
    classification: Classification
    mapping: MappingResult
    inventory: Inventory
    needed: list[str]
    src_hash: str
    pname: str
    report_path: Path


def run(
    source: str,
    out_dir: Path,
    profile: str = "auto",
    skip_locate: bool = False,
    keep_unpack: bool = False,
    work_dir: Path | None = None,
) -> RunResult:
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_owned = work_dir is None
    work = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="deb2nix-"))
    try:
        deb_path, url = fetch_deb(source, work / "download")
        src_hash = sri_file(deb_path)
        unpack_root = work / "unpack"
        unpack_deb(deb_path, unpack_root)
        data_root = unpack_root / "data"
        control_file = unpack_root / "control" / "control"
        if not control_file.is_file():
            raise FileNotFoundError("unpacked .deb has no DEBIAN/control")
        control = parse_control_file(control_file)
        inv = inventory_tree(data_root)
        elfs = scan_tree(data_root)
        needed = unique_needed(elfs)
        mapping = map_libraries(needed, inv.bundled_lib_names, skip_locate=skip_locate)
        override = None if profile == "auto" else profile
        classification = classify(
            control,
            inv,
            elfs,
            unmapped=mapping.unmapped,
            override=override,
        )
        pname = nix_ident(control.package)
        license_expr, unfree = license_expr_for(control)
        # Debian packages without a License field are often DFSG-free (cli fixture)
        # but unknown. For Section: utils/misc without non-free, treat as unknown-unfree
        # only when classifier is electron/chromium or section is non-free.
        if not control.license and not control.is_unfree():
            if classification.profile == "electron" or _looks_proprietary(control):
                unfree = True
                license_expr = "lib.licenses.unfree"
            elif _looks_mit(control):
                unfree = False
                license_expr = "lib.licenses.mit"
        system = debian_arch_to_nix_system(control.architecture)
        main = guess_main_program(control, inv.binaries)
        ctx = EmitContext(
            control=control,
            classification=classification,
            mapping=mapping,
            src_kind="url" if url else "local",
            src_url=url,
            src_hash=src_hash,
            src_filename=deb_path.name,
            system=system,
            pname=pname,
            unfree=unfree,
            license_expr=license_expr,
            main_program=main,
            binaries=inv.binaries,
            needed=needed,
        )
        written = emit_all(out_dir, ctx)
        dest_deb = out_dir / "src.deb"
        if dest_deb.resolve() != deb_path.resolve():
            shutil.copy2(deb_path, dest_deb)
        written.append(dest_deb)
        if keep_unpack:
            kept = out_dir / "unpacked"
            if kept.exists():
                shutil.rmtree(kept)
            shutil.copytree(unpack_root, kept)
            written.append(kept)
        return RunResult(
            out_dir=out_dir,
            written=written,
            control=control,
            classification=classification,
            mapping=mapping,
            inventory=inv,
            needed=needed,
            src_hash=src_hash,
            pname=pname,
            report_path=out_dir / "report.json",
        )
    finally:
        if tmp_owned and not keep_unpack:
            shutil.rmtree(work, ignore_errors=True)


def _looks_proprietary(control: Control) -> bool:
    blob = " ".join(
        [
            control.package,
            control.maintainer,
            control.description,
            control.section,
        ]
    ).lower()
    tokens = ("google", "microsoft", "chrome", "edge", "vscode", "cursor", "spacexai", "unfree")
    return any(t in blob for t in tokens)


def _looks_mit(control: Control) -> bool:
    blob = (control.description + " " + control.license).lower()
    return "mit" in blob or "expat" in blob
