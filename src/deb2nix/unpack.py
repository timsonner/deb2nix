"""Unpack a .deb with dpkg-deb, falling back to ar + tar."""

from __future__ import annotations

import shutil
import subprocess
import tarfile
from pathlib import Path


class UnpackError(RuntimeError):
    pass


def unpack_deb(deb_path: Path, dest: Path) -> Path:
    """Unpack data + control into dest. Returns dest."""
    dest.mkdir(parents=True, exist_ok=True)
    if shutil.which("dpkg-deb"):
        _unpack_dpkg(deb_path, dest)
        return dest
    _unpack_ar(deb_path, dest)
    return dest


def _unpack_dpkg(deb_path: Path, dest: Path) -> None:
    data = dest / "data"
    control = dest / "control"
    data.mkdir(parents=True, exist_ok=True)
    control.mkdir(parents=True, exist_ok=True)
    r1 = subprocess.run(
        ["dpkg-deb", "-x", str(deb_path), str(data)],
        capture_output=True,
        text=True,
    )
    r2 = subprocess.run(
        ["dpkg-deb", "-e", str(deb_path), str(control)],
        capture_output=True,
        text=True,
    )
    if r1.returncode != 0:
        raise UnpackError(r1.stderr.strip() or "dpkg-deb -x failed")
    if r2.returncode != 0:
        raise UnpackError(r2.stderr.strip() or "dpkg-deb -e failed")


def _unpack_ar(deb_path: Path, dest: Path) -> None:
    ar = shutil.which("ar")
    if not ar:
        raise UnpackError("neither dpkg-deb nor ar is available")
    stage = dest / "_ar"
    stage.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [ar, "x", str(deb_path.resolve())],
        cwd=stage,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise UnpackError(r.stderr.strip() or "ar x failed")
    data_tar = _find_member(stage, "data.tar")
    control_tar = _find_member(stage, "control.tar")
    if data_tar is None:
        raise UnpackError("deb archive has no data.tar.* member")
    data = dest / "data"
    control = dest / "control"
    data.mkdir(parents=True, exist_ok=True)
    control.mkdir(parents=True, exist_ok=True)
    _extract_tar(data_tar, data)
    if control_tar is not None:
        _extract_tar(control_tar, control)


def _find_member(stage: Path, prefix: str) -> Path | None:
    matches = sorted(stage.glob(prefix + "*"))
    return matches[0] if matches else None


def _extract_tar(archive: Path, dest: Path) -> None:
    # tarfile opens .gz/.xz/.bz2 via mode r:*
    with tarfile.open(archive, mode="r:*") as tf:
        try:
            tf.extractall(dest, filter="data")
        except TypeError:
            tf.extractall(dest)
