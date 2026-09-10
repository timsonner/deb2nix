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
    if c.profile != "cli":
        print("  note    : non-cli profile is stubbed (package.nix throws). See STATUS.md.")
    if c.warnings:
        for w in c.warnings:
            print(f"  warn    : {w}")


if __name__ == "__main__":
    raise SystemExit(main())
