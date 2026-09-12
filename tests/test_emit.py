"""CLI profile emit contains autoPatchelfHook; other profiles throw."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from deb2nix.classify import Classification
from deb2nix.control import parse_control_text
from deb2nix.emit import EmitContext, emit_all, license_expr_for
from deb2nix.locate import MappingResult


def _ctx(profile: str, **kwargs) -> EmitContext:
    control = parse_control_text(
        "Package: hello-deb2nix\nVersion: 0.1.0\nArchitecture: amd64\n"
        "License: MIT\nHomepage: https://example.com\nDescription: hello\n"
    )
    classification = Classification(profile=profile, confidence="high", reasons=["test"])
    return EmitContext(
        control=control,
        classification=classification,
        mapping=kwargs.get("mapping", MappingResult()),
        src_kind="local",
        src_url=None,
        src_hash="sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        src_filename="hello.deb",
        system="x86_64-linux",
        pname="hello-deb2nix",
        license_expr="lib.licenses.mit",
        main_program="hello-deb2nix",
        binaries=["usr/bin/hello-deb2nix"],
        needed=["libc.so.6"],
    )


class EmitTests(unittest.TestCase):
    def test_cli_has_autopatchelf(self) -> None:
        with TemporaryDirectory() as td:
            paths = emit_all(Path(td), _ctx("cli"))
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("autoPatchelfHook", package)
            self.assertIn("stdenv.mkDerivation", package)
            self.assertIn("dpkg-deb --fsys-tarfile", package)
            self.assertNotIn("dpkg-deb -x", package)
            self.assertNotIn("--no-sandbox", package)
            self.assertIn("ln -sfn", package)
            self.assertIn("x7fELF", package)
            flake = (Path(td) / "flake.nix").read_text()
            self.assertIn('"hello-deb2nix" = default;', flake)
            self.assertNotIn(".hello-deb2nix =", flake)
            self.assertTrue(any(p.name == "flake.nix" for p in paths))

    def test_electron_userland_not_sandbox(self) -> None:
        with TemporaryDirectory() as td:
            emit_all(Path(td), _ctx("electron"))
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("autoPatchelfHook", package)
            self.assertIn("wrapGAppsHook3", package)
            self.assertNotRegex(package, r'--add-flags\s+"--no-sandbox"')
            self.assertNotRegex(package, r"wrapProgram[^\n]*--no-sandbox")
            self.assertIn("$'\\0'", package)
            self.assertNotIn("read -r -d ''", package)
            self.assertNotIn("throw", package.split("meta")[0])
            self.assertTrue((Path(td) / "NOTES.md").is_file())
            self.assertIn("dontWrapQtApps = true", package)
            self.assertIn('find "$out/opt"', package)
            self.assertIn("ln -sfn", package)
            self.assertIn("ELECTRON_FORCE_IS_PACKAGED", package)
            self.assertIn("x7fELF", package)
            self.assertNotIn('-name "hello-deb2nix"', package)
            self.assertIn("basename", package)

    def test_chromium_browser_userland(self) -> None:
        with TemporaryDirectory() as td:
            emit_all(Path(td), _ctx("chromium-browser"))
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("autoPatchelfHook", package)
            self.assertIn("chromium-browser", package)
            self.assertNotRegex(package, r'--add-flags\s+"--no-sandbox"')
            self.assertNotRegex(package, r"wrapProgram[^\n]*--no-sandbox")
            self.assertTrue((Path(td) / "NOTES.md").is_file())
            self.assertNotIn("ELECTRON_FORCE_IS_PACKAGED", package)
            self.assertIn("x7fELF", package)

    def test_driver_throws_no_kernel_load(self) -> None:
        with TemporaryDirectory() as td:
            emit_all(Path(td), _ctx("driver"))
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("throw", package)
            self.assertIn("DKMS", package)
            self.assertTrue((Path(td) / "LIMITATIONS.md").is_file())
            self.assertTrue((Path(td) / "nixos-module.stub.nix").is_file())
            module = (Path(td) / "nixos-module.stub.nix").read_text()
            self.assertIn("kernel/DKMS", module)
            self.assertIn("insmod", module.lower() + package.lower() + (Path(td) / "LIMITATIONS.md").read_text().lower())
            self.assertNotIn("displaylink", package.lower())
            self.assertNotIn("displaylink", module.lower())

    def test_fhs_not_silent(self) -> None:
        with TemporaryDirectory() as td:
            emit_all(Path(td), _ctx("fhs-fallback"))
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("throw", package)
            self.assertIn("buildFHSEnv", package)
            self.assertNotIn("buildFHSEnv {", package)

    def test_gtk_userland_not_throw(self) -> None:
        with TemporaryDirectory() as td:
            paths = emit_all(Path(td), _ctx("gtk"))
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("autoPatchelfHook", package)
            self.assertIn("wrapGAppsHook3", package)
            self.assertNotIn("throw", package.split("meta")[0])
            self.assertFalse(any(p.name == "package.stub.nix" for p in paths))

    def test_qt_userland_not_throw(self) -> None:
        with TemporaryDirectory() as td:
            emit_all(Path(td), _ctx("qt"))
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("autoPatchelfHook", package)
            self.assertIn("wrapQtAppsHook", package)
            self.assertNotIn("throw", package.split("meta")[0])

    def test_arch_all_uses_linux_platforms(self) -> None:
        ctx = _ctx("cli")
        ctx.control.architecture = "all"
        with TemporaryDirectory() as td:
            emit_all(Path(td), ctx)
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("lib.platforms.linux", package)

    def test_license_follows_debian_and_nixpkgs(self) -> None:
        mit = parse_control_text(
            "Package: x\nVersion: 1\nArchitecture: amd64\nLicense: MIT\nDescription: x\n"
        )
        self.assertEqual(license_expr_for(mit), "lib.licenses.mit")
        empty = parse_control_text(
            "Package: x\nVersion: 1\nArchitecture: amd64\nSection: utils\nDescription: x\n"
        )
        self.assertEqual(license_expr_for(empty), "lib.licenses.free")
        nonfree = parse_control_text(
            "Package: x\nVersion: 1\nArchitecture: amd64\nSection: non-free/web\nDescription: x\n"
        )
        self.assertEqual(license_expr_for(nonfree), "lib.licenses.unfree")

    def test_placeholder_license_is_unspecified_free(self) -> None:
        """Grok Bot 0.47.0 ships License: unknown; do not emit a quoted Nix string."""
        unknown = parse_control_text(
            "Package: grok-bot\nVersion: 0.47.0\nArchitecture: amd64\n"
            "Section: default\nLicense: unknown\nDescription: grok-bot\n"
        )
        self.assertEqual(license_expr_for(unknown), "lib.licenses.free")
        self.assertFalse(unknown.is_unfree())
        na = parse_control_text(
            "Package: x\nVersion: 1\nArchitecture: amd64\nLicense: n/a\nDescription: x\n"
        )
        self.assertEqual(license_expr_for(na), "lib.licenses.free")

    def test_electron_uses_flat_x11_attrs(self) -> None:
        """nixpkgs 26.05+ deprecates xorg.libX11; emit libx11 etc."""
        with TemporaryDirectory() as td:
            emit_all(Path(td), _ctx("electron"))
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("libx11", package)
            self.assertIn("libxcb", package)
            self.assertNotIn("xorg.libX11", package)
            self.assertNotIn("xorg.libxcb", package)

    def test_flake_has_no_unfree_gate(self) -> None:
        with TemporaryDirectory() as td:
            emit_all(Path(td), _ctx("cli"))
            flake = (Path(td) / "flake.nix").read_text()
            default = (Path(td) / "default.nix").read_text()
            self.assertNotIn("allowUnfreePredicate", flake)
            self.assertNotIn("allowUnfree =", flake)
            self.assertNotIn("allowUnfreePredicate", default)


if __name__ == "__main__":
    unittest.main()
