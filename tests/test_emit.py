"""CLI profile emit contains autoPatchelfHook; other profiles throw."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from deb2nix.classify import Classification
from deb2nix.control import parse_control_text
from deb2nix.emit import EmitContext, emit_all
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
        unfree=False,
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
            self.assertIn("dpkg-deb -x", package)
            self.assertNotIn("--no-sandbox", package)
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
            self.assertNotIn("throw", package.split("meta")[0])
            self.assertTrue((Path(td) / "NOTES.md").is_file())

    def test_chromium_browser_userland(self) -> None:
        with TemporaryDirectory() as td:
            emit_all(Path(td), _ctx("chromium-browser"))
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("autoPatchelfHook", package)
            self.assertIn("chromium-browser", package)
            self.assertNotRegex(package, r'--add-flags\s+"--no-sandbox"')
            self.assertNotRegex(package, r"wrapProgram[^\n]*--no-sandbox")
            self.assertTrue((Path(td) / "NOTES.md").is_file())

    def test_driver_throws_no_kernel_load(self) -> None:
        with TemporaryDirectory() as td:
            emit_all(Path(td), _ctx("driver"))
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("throw", package)
            self.assertIn("DKMS", package)
            self.assertIn("DisplayLink", package)
            self.assertTrue((Path(td) / "LIMITATIONS.md").is_file())
            self.assertTrue((Path(td) / "nixos-module.stub.nix").is_file())
            module = (Path(td) / "nixos-module.stub.nix").read_text()
            self.assertIn("hardware.video.displaylink", module)
            self.assertIn("insmod", module.lower() + package.lower() + (Path(td) / "LIMITATIONS.md").read_text().lower())

    def test_fhs_not_silent(self) -> None:
        with TemporaryDirectory() as td:
            emit_all(Path(td), _ctx("fhs-fallback"))
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("throw", package)
            self.assertIn("buildFHSEnv", package)
            self.assertNotIn("buildFHSEnv {", package)

    def test_unfree_predicate(self) -> None:
        ctx = _ctx("cli")
        ctx.unfree = True
        ctx.license_expr = "lib.licenses.unfree"
        with TemporaryDirectory() as td:
            emit_all(Path(td), ctx)
            flake = (Path(td) / "flake.nix").read_text()
            self.assertIn("allowUnfreePredicate", flake)
            self.assertNotIn("allowUnfree = true;", flake)


if __name__ == "__main__":
    unittest.main()
