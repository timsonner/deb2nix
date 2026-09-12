"""Emit flake.nix / package.nix / default.nix / report.json for a profile."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

from deb2nix import __version__
from deb2nix.classify import Classification
from deb2nix.control import Control
from deb2nix.locate import MappingResult
from deb2nix.nixlang import nix_ident, nix_indented_string, nix_string


NIXPKGS_LICENSE = {
    "mit": "lib.licenses.mit",
    "expat": "lib.licenses.mit",
    "bsd-2-clause": "lib.licenses.bsd2",
    "bsd-3-clause": "lib.licenses.bsd3",
    "apache-2.0": "lib.licenses.asl20",
    "asl2.0": "lib.licenses.asl20",
    "gpl-2": "lib.licenses.gpl2Only",
    "gpl-2.0": "lib.licenses.gpl2Only",
    "gpl-2+": "lib.licenses.gpl2Plus",
    "gpl-2.0+": "lib.licenses.gpl2Plus",
    "gpl-3": "lib.licenses.gpl3Only",
    "gpl-3.0": "lib.licenses.gpl3Only",
    "gpl-3+": "lib.licenses.gpl3Plus",
    "gpl-3.0+": "lib.licenses.gpl3Plus",
    "lgpl-2.1": "lib.licenses.lgpl21Only",
    "lgpl-2.1+": "lib.licenses.lgpl21Plus",
    "lgpl-3": "lib.licenses.lgpl3Only",
    "lgpl-3.0+": "lib.licenses.lgpl3Plus",
    "mpl-2.0": "lib.licenses.mpl20",
    "isc": "lib.licenses.isc",
    "zlib": "lib.licenses.zlib",
}


@dataclass
class EmitContext:
    control: Control
    classification: Classification
    mapping: MappingResult
    src_kind: str  # url | local
    src_url: str | None
    src_hash: str
    src_filename: str
    system: str
    pname: str
    license_expr: str
    main_program: str | None
    binaries: list[str]
    needed: list[str]


# Debian binaries often omit License: or put a placeholder (Grok Bot: "unknown").
# Same stand-in as a missing field: lib.licenses.free = unspecified, not MIT, not unfree.
UNSPECIFIED_LICENSE_KEYS = {
    "",
    "unknown",
    "n/a",
    "na",
    "none",
    "unspecified",
    "-",
    ".",
}


def license_expr_for(control: Control) -> str:
    """Follow nixpkgs meta.license so the parent OS allowUnfree policy applies.

    The generator never sets allowUnfree. NixOS / ~/.config/nixpkgs/config.nix /
    NIXPKGS_ALLOW_UNFREE decide whether an unfree derivation evaluates.
    Placeholder License: values (unknown, n/a) are treated as missing, not quoted
    as a Nix string — a quoted "unknown" is not a nixpkgs license and skips the
    unfree gate without meaning "free software".
    """
    raw = (control.license or "").strip()
    key = raw.lower().split(",")[0].strip()
    if control.is_unfree():
        return "lib.licenses.unfree"
    if key in NIXPKGS_LICENSE:
        return NIXPKGS_LICENSE[key]
    if key in UNSPECIFIED_LICENSE_KEYS:
        return "lib.licenses.free"
    return nix_string(raw)


def guess_main_program(control: Control, binaries: list[str]) -> str | None:
    names = []
    for rel in binaries:
        if rel.startswith("usr/bin/") or rel.startswith("bin/"):
            names.append(Path(rel).name)
    if not names:
        for rel in binaries:
            names.append(Path(rel).name)
    pkg = control.package
    if pkg in names:
        return pkg
    if names:
        return names[0]
    return nix_ident(pkg)


def emit_all(out_dir: Path, ctx: EmitContext) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    package = _emit_package(ctx)
    (out_dir / "package.nix").write_text(package, encoding="utf-8")
    written.append(out_dir / "package.nix")
    default = _emit_default(ctx)
    (out_dir / "default.nix").write_text(default, encoding="utf-8")
    written.append(out_dir / "default.nix")
    flake = _emit_flake(ctx)
    (out_dir / "flake.nix").write_text(flake, encoding="utf-8")
    written.append(out_dir / "flake.nix")
    report = _emit_report(ctx)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    written.append(out_dir / "report.json")
    profile = ctx.classification.profile
    if profile in {"electron", "chromium-browser"}:
        notes = _emit_gui_notes(ctx)
        (out_dir / "NOTES.md").write_text(notes, encoding="utf-8")
        written.append(out_dir / "NOTES.md")
    if profile in {"driver", "system"}:
        stub = _emit_phase2_stub(ctx)
        (out_dir / "package.stub.nix").write_text(stub, encoding="utf-8")
        written.append(out_dir / "package.stub.nix")
        module = _emit_nixos_module_stub(ctx)
        (out_dir / "nixos-module.stub.nix").write_text(module, encoding="utf-8")
        written.append(out_dir / "nixos-module.stub.nix")
        limits = _emit_driver_limitations(ctx)
        (out_dir / "LIMITATIONS.md").write_text(limits, encoding="utf-8")
        written.append(out_dir / "LIMITATIONS.md")
    elif profile == "fhs-fallback":
        stub = _emit_phase2_stub(ctx)
        (out_dir / "package.stub.nix").write_text(stub, encoding="utf-8")
        written.append(out_dir / "package.stub.nix")
    return written


def _header_comment(ctx: EmitContext) -> str:
    return "\n".join(
        [
            f"# Generated by deb2nix {__version__} (profile: {ctx.classification.profile}).",
            "# Review before use. Not intended for publishing into nixpkgs.",
            "# Hash-pinned src. Review before use.",
        ]
    )


def _src_attr(ctx: EmitContext) -> str:
    if ctx.src_kind == "url" and ctx.src_url:
        return (
            "  src = fetchurl {\n"
            f"    url = {nix_string(ctx.src_url)};\n"
            f"    hash = {nix_string(ctx.src_hash)};\n"
            "  };"
        )
    return "  src = ./src.deb;"


GUI_USERLAND_EXTRAS = [
    "alsa-lib",
    "at-spi2-core",
    "cairo",
    "cups",
    "dbus",
    "expat",
    "glib",
    "gtk3",
    "libdrm",
    "libGL",
    "libnotify",
    "libsecret",
    "libxkbcommon",
    "mesa",
    "nspr",
    "nss",
    "pango",
    "libx11",
    "libxcomposite",
    "libxdamage",
    "libxext",
    "libxfixes",
    "libxrandr",
    "libxcb",
]

GTK_USERLAND_EXTRAS = [
    "glib",
    "gtk3",
    "cairo",
    "pango",
    "gdk-pixbuf",
]


def _call_args(
    ctx: EmitContext,
    extra_native: list[str] | None = None,
    extra_inputs: list[str] | None = None,
) -> tuple[list[str], list[str], list[str]]:
    """Return (function arguments, nativeBuildInputs, buildInputs exprs)."""
    native = ["autoPatchelfHook", "dpkg", "makeWrapper"]
    for item in extra_native or []:
        if item not in native:
            native.append(item)
    args = ["lib", "stdenv", "dpkg", "autoPatchelfHook", "makeWrapper"]
    for item in extra_native or []:
        if item not in args:
            args.append(item)
    if ctx.src_kind == "url":
        args.append("fetchurl")
    inputs = ["stdenv.cc.cc.lib"]
    extra_args: list[str] = []
    for pkg in list(ctx.mapping.build_inputs) + list(extra_inputs or []):
        top = pkg.split(".", 1)[0]
        if top not in extra_args and top not in args:
            extra_args.append(top)
        inputs.append(pkg)
    seen: set[str] = set()
    args_out: list[str] = []
    for a in args + extra_args:
        if a not in seen:
            seen.add(a)
            args_out.append(a)
    in_seen: set[str] = set()
    inputs_out: list[str] = []
    for i in inputs:
        if i not in in_seen:
            in_seen.add(i)
            inputs_out.append(i)
    return args_out, native, inputs_out


def _fmt_list(items: list[str], indent: int = 4) -> str:
    pad = " " * indent
    if not items:
        return pad + "# (none)"
    return "\n".join(f"{pad}{item}" for item in items)


def _emit_package(ctx: EmitContext) -> str:
    profile = ctx.classification.profile
    if profile in {"cli", "electron", "chromium-browser", "gtk", "qt"}:
        return _emit_userland_package(ctx)
    return _emit_throwing_package(ctx)


def _ignore_block(ctx: EmitContext, extra: list[str] | None = None) -> str:
    names: list[str] = []
    for u in list(ctx.mapping.unmapped) + list(extra or []):
        if u not in names:
            names.append(u)
    if not names:
        return ""
    quoted = [nix_string(u) for u in names]
    return (
        "\n  autoPatchelfIgnoreMissingDeps = [\n"
        + "\n".join(f"    {u}" for u in quoted)
        + "\n  ];\n"
    )


def _qt_libs_for(ctx: EmitContext, prefixes: tuple[str, ...]) -> list[str]:
    return [
        m.lib
        for m in ctx.mapping.mapped
        if any((m.pkg or "").startswith(p) for p in prefixes)
    ]


def _drop_qt_inputs(
    args: list[str], inputs: list[str], ctx: EmitContext
) -> tuple[list[str], list[str], list[str]]:
    """Drop all Qt pkgs. Chromium/Electron/GTK still get toolkit via GApps; Qt sonames ignored."""
    qt_pkgs = [i for i in inputs if i.startswith("qt5.") or i.startswith("qt6.")]
    if not qt_pkgs:
        return args, inputs, []
    inputs = [i for i in inputs if i not in qt_pkgs]
    args = [a for a in args if a not in {"qt5", "qt6"}]
    return args, inputs, _qt_libs_for(ctx, ("qt5.", "qt6."))


def _prefer_one_qt(
    args: list[str], inputs: list[str], ctx: EmitContext
) -> tuple[list[str], list[str], list[str]]:
    """Keep Qt5 or Qt6, not both — mixed setup hooks fail the build."""
    qt5 = [i for i in inputs if i.startswith("qt5.")]
    qt6 = [i for i in inputs if i.startswith("qt6.")]
    if qt5 and qt6:
        if len(qt6) >= len(qt5):
            inputs = [i for i in inputs if i not in qt5]
            args = [a for a in args if a != "qt5"]
            return args, inputs, _qt_libs_for(ctx, ("qt5.",))
        inputs = [i for i in inputs if i not in qt6]
        args = [a for a in args if a != "qt6"]
        return args, inputs, _qt_libs_for(ctx, ("qt6.",))
    return args, inputs, []


def _platforms_expr(ctx: EmitContext) -> str:
    if ctx.control.architecture.lower() == "all":
        return "lib.platforms.linux"
    return f"[ {nix_string(ctx.system)} ]"


def _install_phase() -> str:
    """Copy Debian layout. Retarget /opt and /usr. No per-app paths or names."""
    return """
  installPhase = ''
    runHook preInstall
    mkdir -p "$out"
    if [ -d usr ]; then
      cp -a usr/. "$out/"
    fi
    if [ -d opt ]; then
      mkdir -p "$out/opt"
      cp -a opt/. "$out/opt/"
    fi
    if [ -d bin ] && [ ! -e "$out/bin" ]; then
      mkdir -p "$out/bin"
      cp -a bin/. "$out/bin/"
    fi
    if [ -d "$out/usr/bin" ] && [ ! -e "$out/bin" ]; then
      mv "$out/usr/bin" "$out/bin"
    fi
    # Debian .debs often ship absolute /opt and /usr symlinks; retarget into $out.
    find "$out" -type l -print0 2>/dev/null | while IFS= read -r -d $'\\0' link; do
      t="$(readlink "$link" || true)"
      case "$t" in
        /opt/*)
          ln -sfn "$out$t" "$link" || true
          ;;
        /usr/*)
          ln -sfn "$out''${t#/usr}" "$link" || true
          ;;
      esac
    done
    # Rewrite text wrappers only. substituteInPlace on an ELF corrupts it.
    if [ -d "$out/bin" ]; then
      for f in "$out/bin"/*; do
        [ -f "$f" ] && [ ! -L "$f" ] || continue
        magic="$(head -c 4 "$f" 2>/dev/null || true)"
        if [ "$magic" = $'\\x7fELF' ]; then
          continue
        fi
        if grep -qE '/opt/|/usr/' "$f" 2>/dev/null; then
          substituteInPlace "$f" --replace-quiet /opt/ "$out/opt/" --replace-quiet /usr/ "$out/" || true
        fi
      done
    fi
    find "$out" -name '*.desktop' -type f -print0 2>/dev/null | while IFS= read -r -d $'\\0' desk; do
      substituteInPlace "$desk" --replace-quiet /opt/ "$out/opt/" --replace-quiet /usr/ "$out/" || true
    done
    # Chromium helper binaries named *-sandbox must not be setuid in the Nix store.
    find "$out" -type f \\( -name chrome-sandbox -o -name '*-sandbox' \\) -exec chmod 0755 {} \\; || true
    mkdir -p "$out/bin"
    # If the .deb had no usr/bin, expose executables from opt/share by basename.
    if [ -z "$(find "$out/bin" -mindepth 1 -maxdepth 1 \\( -type f -o -xtype f \\) -print -quit 2>/dev/null)" ]; then
      find "$out/opt" "$out/share" -maxdepth 4 -type f -executable \\
        ! -name '*.so' ! -name '*.so.*' ! -name '*-sandbox' ! -name '*crashpad*' \\
        2>/dev/null | while IFS= read -r exe; do
        [ -n "$exe" ] || continue
        ln -sfn "$exe" "$out/bin/$(basename "$exe")" || true
      done
    fi
    runHook postInstall
  '';
"""


def _emit_userland_package(ctx: EmitContext) -> str:
    """Unpack + autoPatchelf. No --no-sandbox, no FHS, no setuid sandbox."""
    profile = ctx.classification.profile
    extra_native: list[str] = []
    extra_inputs: list[str] = []
    qt_ignore: list[str] = []
    electron_env = False
    wrap_gapps_manual = False
    dont_wrap_gapps = False
    dont_wrap_qt = False
    header_notes = ""

    if profile == "electron":
        extra_native = ["wrapGAppsHook3"]
        extra_inputs = GUI_USERLAND_EXTRAS
        electron_env = True
        wrap_gapps_manual = True
        dont_wrap_gapps = True
        dont_wrap_qt = True
        header_notes = (
            "# Userland electron expression: unpack + autoPatchelf + GApps wrap.\n"
            "# Does not disable the Chromium sandbox. *-sandbox files are mode 0755.\n"
            "# Qt5/Qt6 are not in buildInputs (hook conflict); sonames ignored if present.\n"
        )
    elif profile == "chromium-browser":
        extra_native = ["wrapGAppsHook3"]
        extra_inputs = GUI_USERLAND_EXTRAS
        wrap_gapps_manual = True
        dont_wrap_gapps = True
        dont_wrap_qt = True
        header_notes = (
            "# Userland chromium-browser expression: unpack + autoPatchelf + GApps wrap.\n"
            "# Does not disable the Chromium sandbox. *-sandbox files are mode 0755.\n"
            "# Qt5/Qt6 are not in buildInputs (hook conflict); sonames ignored if present.\n"
        )
    elif profile == "gtk":
        extra_native = ["wrapGAppsHook3"]
        extra_inputs = GTK_USERLAND_EXTRAS
        dont_wrap_qt = True
        header_notes = (
            "# GTK userland expression: unpack + autoPatchelf + wrapGAppsHook3.\n"
        )
    elif profile == "qt":
        extra_native = ["wrapQtAppsHook"]
        dont_wrap_gapps = True
        header_notes = (
            "# Qt userland expression: unpack + autoPatchelf + wrapQtAppsHook.\n"
            "# One Qt major only (5 or 6).\n"
        )

    args, native, inputs = _call_args(
        ctx, extra_native=extra_native, extra_inputs=extra_inputs
    )
    if profile in {"electron", "chromium-browser", "gtk"}:
        args, inputs, qt_ignore = _drop_qt_inputs(args, inputs, ctx)
    elif profile == "qt":
        args, inputs, qt_ignore = _prefer_one_qt(args, inputs, ctx)

    wrap_flags = ""
    if dont_wrap_gapps:
        wrap_flags += "  dontWrapGApps = true;\n"
    if dont_wrap_qt:
        wrap_flags += "  dontWrapQtApps = true;\n"

    pre_fixup = ""
    if electron_env:
        pre_fixup = """
  preFixup = ''
    gappsWrapperArgs+=(
      --set-default ELECTRON_FORCE_IS_PACKAGED 1
    )
  '';
"""
    post_fixup = ""
    if wrap_gapps_manual:
        post_fixup = """
  postFixup = ''
    if [ -n "''${gappsWrapperArgs-}" ]; then
      for bin in "$out/bin"/*; do
        if [ -e "$bin" ] && [ -x "$bin" ]; then
          wrapProgram "$bin" "''${gappsWrapperArgs[@]}" || true
        fi
      done
    fi
  '';
"""

    arg_block = ",\n  ".join(args)
    input_block = _fmt_list(inputs)
    native_block = _fmt_list(native)
    src = _src_attr(ctx)
    meta_license = ctx.license_expr
    homepage = ctx.control.homepage or ""
    description = ctx.control.synopsis or ctx.pname
    main = ctx.main_program or ctx.pname
    pname_nix = nix_string(ctx.pname)
    return f"""{_header_comment(ctx)}
{header_notes}{{
  {arg_block},
}}:

stdenv.mkDerivation (finalAttrs: {{
  pname = {pname_nix};
  version = {nix_string(ctx.control.version)};
{src}

  nativeBuildInputs = [
{native_block}
  ];

  buildInputs = [
{input_block}
  ];
{_ignore_block(ctx, extra=qt_ignore)}
  dontConfigure = true;
  dontBuild = true;
{wrap_flags}
  unpackPhase = ''
    runHook preUnpack
    dpkg-deb --fsys-tarfile "$src" | tar -x --no-same-owner --no-same-permissions
    runHook postUnpack
  '';
{_install_phase()}{pre_fixup}{post_fixup}
  meta = {{
    description = {nix_string(description)};
    homepage = {nix_string(homepage)};
    license = {meta_license};
    platforms = {_platforms_expr(ctx)};
    sourceProvenance = [ lib.sourceTypes.binaryNativeCode ];
    mainProgram = {nix_string(main)};
  }};
}})
"""


def _throw_message(ctx: EmitContext) -> str:
    profile = ctx.classification.profile
    reasons = "; ".join(ctx.classification.reasons) or "classifier heuristics"
    if profile in {"driver", "system"}:
        extra = (
            "deb2nix will not emit an expression that loads kernel modules or installs DKMS."
        )
    else:
        extra = (
            "fhs-fallback refuses to silently emit buildFHSEnv. "
            "Inspect report.json and re-run with --profile after review."
        )
    warnings = " ".join(ctx.classification.warnings)
    return (
        f"deb2nix classified {ctx.pname!r} as profile {profile!r}. {reasons}. {extra} {warnings}"
    ).strip()


def _emit_throwing_package(ctx: EmitContext) -> str:
    args = ["lib"]
    msg = _throw_message(ctx)
    # Nix indented string: escape '' 
    body = msg.replace("''", "'''")
    evidence = json.dumps(ctx.classification.as_dict(), indent=2)
    evidence_comment = "\n".join("# " + line if line else "#" for line in evidence.splitlines())
    return f"""{_header_comment(ctx)}
# Classifier evidence:
{evidence_comment}

{{
  {", ".join(args)},
}}:

throw {nix_indented_string(body, indent="  ")}
"""


def _emit_default(ctx: EmitContext) -> str:
    return f"""{_header_comment(ctx)}
# import <nixpkgs> picks up ~/.config/nixpkgs/config.nix (allowUnfree, etc.).
{{ pkgs ? import <nixpkgs> {{ }} }}:

pkgs.callPackage ./package.nix {{ }}
"""


def _emit_flake(ctx: EmitContext) -> str:
    return f"""{_header_comment(ctx)}
{{
  description = {nix_string(ctx.control.synopsis or ctx.pname + " (generated by deb2nix)")};

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {{ self, nixpkgs }}:
    let
      system = {nix_string(ctx.system)};
      # No config here: flakes do not inherit NixOS allowUnfree.
      # Consume package.nix from NixOS, or: NIXPKGS_ALLOW_UNFREE=1 nix build --impure
      pkgs = import nixpkgs {{ inherit system; }};
    in {{
      packages.${{system}} = rec {{
        default = pkgs.callPackage ./package.nix {{ }};
        {nix_string(ctx.pname)} = default;
      }};
    }};
}}
"""


def _emit_phase2_stub(ctx: EmitContext) -> str:
    """Non-evaluated notes for Phase 2 implementers — not a silent FHS wrap."""
    profile = ctx.classification.profile
    notes = {
        "driver": "This .deb ships kernel/DKMS payload. package.nix throws. See LIMITATIONS.md.",
        "system": "udev/firmware/systemd units need NixOS modules, not a user package install.",
        "fhs-fallback": "Only emit buildFHSEnv after an explicit --profile fhs-fallback and a review of unmapped libs.",
    }
    note = notes.get(profile, "")
    return f"""{_header_comment(ctx)}
# This file is documentation for a future profile implementation.
# package.nix throws until the profile is fully implemented.
#
# profile: {profile}
# subtype: {ctx.classification.subtype}
#
{chr(10).join('# ' + line if line else '#' for line in note.splitlines())}
#
# Suggested fetch:
#   src = fetchurl {{ url = "..."; hash = {nix_string(ctx.src_hash)}; }};
"""


def _emit_gui_notes(ctx: EmitContext) -> str:
    return dedent(
        f"""\
        # {ctx.pname} — userland notes

        Profile: `{ctx.classification.profile}`.

        `package.nix` is a userland unpack + `autoPatchelfHook` + GApps wrap.
        Hash-pinned.

        Out of scope for this generator:

        - GUI/display smoke (`nix build` is not a display test; Electron `--version` may open a window).
        - Disabling the Chromium sandbox.
        - Silent `buildFHSEnv`.
        - setuid on `*-sandbox` (mode 0755; user namespaces).
        - Qt5+Qt6 in the same `buildInputs` (setup-hook conflict).
        - Publishing to public nixpkgs.

        Hash: `{ctx.src_hash}`
        """
    )


def _emit_nixos_module_stub(ctx: EmitContext) -> str:
    return f"""{_header_comment(ctx)}
# NixOS module stub for a .deb that shipped kernel/DKMS payload.
# Not imported by package.nix. deb2nix will not insmod or run DKMS.

{{ config, lib, pkgs, ... }}:

{{
  # boot.extraModulePackages = [ ];
  assertions = [
    {{
      assertion = true;
      message = {nix_string("deb2nix kernel/DKMS stub: modules not enabled")};
    }}
  ];
}}
"""


def _emit_driver_limitations(ctx: EmitContext) -> str:
    reasons = "\n".join(f"- {r}" for r in ctx.classification.reasons) or "- (see report.json)"
    return f"""# LIMITATIONS — `{ctx.pname}` ({ctx.classification.profile})

This `.deb` ships kernel-module or DKMS payload. deb2nix will not `insmod`,
run DKMS, or emit a fake working driver.

## Classifier evidence

{reasons}

Hash: `{ctx.src_hash}`
Depends: `{ctx.control.depends or "(none)"}`

`package.nix` throws. `nixos-module.stub.nix` is documentation only.
"""


def _emit_report(ctx: EmitContext) -> dict:
    return {
        "deb2nix": __version__,
        "pname": ctx.pname,
        "version": ctx.control.version,
        "architecture": ctx.control.architecture,
        "nixSystem": ctx.system,
        "profile": ctx.classification.as_dict(),
        "licenseExpr": ctx.license_expr,
        "source": {
            "kind": ctx.src_kind,
            "url": ctx.src_url,
            "filename": ctx.src_filename,
            "hash": ctx.src_hash,
        },
        "control": {
            "package": ctx.control.package,
            "homepage": ctx.control.homepage,
            "maintainer": ctx.control.maintainer,
            "depends": ctx.control.depends,
            "section": ctx.control.section,
            "license": ctx.control.license,
            "description": ctx.control.synopsis,
        },
        "mapping": {
            "locateAvailable": ctx.mapping.locate_available,
            "buildInputs": ctx.mapping.build_inputs,
            "unmapped": ctx.mapping.unmapped,
            "bundled": ctx.mapping.bundled,
            "libs": [
                {
                    "lib": m.lib,
                    "pkg": m.pkg,
                    "source": m.source,
                    "note": m.note,
                }
                for m in ctx.mapping.mapped
            ],
        },
        "needed": ctx.needed,
        "binaries": ctx.binaries,
        "mainProgram": ctx.main_program,
        "constraints": {
            "noPublicNixpkgsPublish": True,
            "hashPinned": True,
            "honestFailureOverSilentFhs": True,
            "noKernelModuleLoad": True,
        },
    }
