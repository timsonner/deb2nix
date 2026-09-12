"""Human-facing install/remove sequences. CLI, NOTES, and tests share this."""

from __future__ import annotations

from pathlib import Path


def result_link(out_dir: Path | str) -> str:
    return f"{out_dir}/result"


def install_lines(out_dir: Path | str, pname: str) -> list[str]:
    """Cwd-safe: `nix build DIR -o DIR/result` then add that path, not `./result`."""
    out = str(out_dir)
    res = result_link(out)
    return [
        f"nix build {out} -o {res}",
        f"{res}/bin/{pname}",
        f"nix profile add {res}",
        "hash -r",
        "nix profile list",
    ]


def remove_lines(pname: str) -> list[str]:
    return [
        f"nix profile remove {pname}",
        "nix-collect-garbage",
    ]
