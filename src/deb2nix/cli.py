"""deb2nix command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from deb2nix import __version__
from deb2nix.classify import PROFILES
from deb2nix.pipeline import run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="deb2nix",
        description="Generate a Nix flake/package from any Debian .deb (path or URL).",
    )
    p.add_argument("source", help="Path or http(s) URL to a .deb")
    p.add_argument(
        "--out",
        "-o",
        default=None,
        help="Output directory (default: ./<pname>-nix)",
    )
    p.add_argument(
        "--profile",
        choices=("auto",) + PROFILES,
        default="auto",
        help="Force a profile. Default: auto (never defaults to electron).",
    )
    p.add_argument(
        "--skip-locate",
        action="store_true",
        help="Do not call nix-locate; builtin library map only.",
    )
    p.add_argument(
        "--keep-unpack",
        action="store_true",
        help="Copy the unpacked tree into the output directory.",
    )
    p.add_argument(
        "--src-url",
        default=None,
        help="Record this URL in fetchurl (use with a local .deb after prefetch).",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Print report.json to stdout after generation.",
    )
    p.add_argument("--version", action="version", version=f"deb2nix {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = Path(args.out) if args.out else None
    # First pass may need a temp out if pname unknown; use a placeholder then rename.
    staging = out or Path("deb2nix-out")
    try:
        result = run(
            source=args.source,
            out_dir=staging,
            profile=args.profile,
            skip_locate=args.skip_locate,
            keep_unpack=args.keep_unpack,
            src_url=args.src_url,
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"deb2nix: error: {exc}", file=sys.stderr)
        return 1
    if out is None:
        dest = Path(f"{result.pname}-nix")
        if dest.resolve() != result.out_dir.resolve():
            if dest.exists():
                print(f"deb2nix: error: {dest} already exists (pass --out)", file=sys.stderr)
                return 1
            result.out_dir.rename(dest)
            result.out_dir = dest
            result.report_path = dest / "report.json"
    _print_summary(result)
    if args.json:
        print(result.report_path.read_text(encoding="utf-8"))
    return 0


def _print_summary(result) -> None:
    c = result.classification
    print(f"deb2nix {__version__}")
    print(f"  package : {result.control.package} {result.control.version} ({result.control.architecture})")
    print(f"  hash    : {result.src_hash}")
    print(f"  profile : {c.profile} ({c.confidence})" + (f" [{c.subtype}]" if c.subtype else ""))
    for reason in c.reasons:
        print(f"            - {reason}")
    print(f"  needed  : {len(result.needed)} unique DT_NEEDED libraries")
    print(f"  mapped  : {', '.join(result.mapping.build_inputs) or '(toolchain/glibc only)'}")
    if result.mapping.unmapped:
        print(f"  unmapped: {', '.join(result.mapping.unmapped)}")
    else:
        print("  unmapped: none")
    if result.mapping.bundled:
        print(f"  bundled : {', '.join(result.mapping.bundled)}")
    print("  wrote   :")
    for path in result.written:
        print(f"            {path}")
    if c.profile in {"electron", "chromium-browser"}:
        print("  note    : userland expr emitted (autoPatchelf). No --no-sandbox. GUI smoke is Hyprland.")
        _print_install_hint(result)
    elif c.profile in {"gtk", "qt"}:
        print("  note    : userland expr emitted (autoPatchelf). GUI smoke is Hyprland.")
        _print_install_hint(result)
    elif c.profile == "cli":
        _print_install_hint(result)
    elif c.profile in {"driver", "system"}:
        print("  note    : driver/system stub (no DKMS/insmod). See LIMITATIONS.md.")
    else:
        print("  note    : profile is stubbed (package.nix throws). See STATUS.md.")
    if c.warnings:
        for w in c.warnings:
            print(f"  warn    : {w}")


def _print_install_hint(result) -> None:
    """nix build is not dpkg -i. The binary is not on PATH until the user installs it."""
    main = result.pname
    out = result.out_dir
    print("  install : not on PATH. `nix build` is not an install. Ask how to install:")
    print(f"            nix build {out}")
    print(f"            ./result/bin/{main}                 # run from the build, GUI apps open a window")
    print("            nix profile add ./result            # user profile → ~/.nix-profile/bin")
    print("            NixOS: pkgs.callPackage ./package.nix {} in environment.systemPackages")
    print("  remove  : dpkg does not know this package. Nix is the install db. Ask before removing:")
    print(f"            nix profile remove {main}           # if installed with nix profile add")
    print("            NixOS: drop the callPackage + nixos-rebuild switch")
    print("            nix-collect-garbage                 # drop unreferenced store paths")
    print("            $HOME config dirs are not in the profile; ask before deleting")


if __name__ == "__main__":
    raise SystemExit(main())
