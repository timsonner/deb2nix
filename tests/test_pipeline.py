"""End-to-end generation against committed fixtures (no GUI downloads)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from deb2nix.hashutil import sri_file
from deb2nix.pipeline import run

ROOT = Path(__file__).resolve().parents[1]
HELLO = ROOT / "fixtures" / "hello-deb2nix_0.1.0_amd64.deb"
ELECTRON = ROOT / "fixtures" / "fake-electron-app_0.0.1_amd64.deb"
CHROMIUM = ROOT / "fixtures" / "fake-chromium-browser_0.0.1_amd64.deb"
DRIVER = ROOT / "fixtures" / "fake-displaylink_0.0.1_amd64.deb"


@unittest.skipUnless(HELLO.is_file(), "hello fixture .deb missing; run scripts/make-fixtures.sh")
class FixturePipelineTests(unittest.TestCase):
    def test_hello_cli(self) -> None:
        with TemporaryDirectory() as td:
            result = run(str(HELLO), Path(td), skip_locate=True)
            self.assertEqual(result.classification.profile, "cli")
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("autoPatchelfHook", package)
            self.assertIn("lib.licenses.mit", package)
            report = json.loads((Path(td) / "report.json").read_text())
            self.assertEqual(report["source"]["hash"], sri_file(HELLO))
            self.assertTrue((Path(td) / "src.deb").is_file())
            self.assertTrue(any("libc.so.6" == n for n in result.needed) or result.needed)

    def test_electron_markers(self) -> None:
        with TemporaryDirectory() as td:
            result = run(str(ELECTRON), Path(td), skip_locate=True)
            self.assertEqual(result.classification.profile, "electron")
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("autoPatchelfHook", package)
            self.assertNotRegex(package, r'--add-flags\s+"--no-sandbox"')
            self.assertNotRegex(package, r"wrapProgram[^\n]*--no-sandbox")
            self.assertIn("lib.licenses.mit", package)

    def test_chromium_browser_markers(self) -> None:
        if not CHROMIUM.is_file():
            self.skipTest("chromium fixture .deb missing; run scripts/make-fixtures.sh")
        with TemporaryDirectory() as td:
            result = run(str(CHROMIUM), Path(td), skip_locate=True)
            self.assertEqual(result.classification.profile, "chromium-browser")
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("autoPatchelfHook", package)
            self.assertNotRegex(package, r'--add-flags\s+"--no-sandbox"')
            self.assertNotRegex(package, r"wrapProgram[^\n]*--no-sandbox")
            self.assertIn("lib.licenses.mit", package)

    def test_driver_markers(self) -> None:
        with TemporaryDirectory() as td:
            result = run(str(DRIVER), Path(td), skip_locate=True)
            self.assertIn(result.classification.profile, {"driver", "system"})
            text = (Path(td) / "package.nix").read_text()
            self.assertIn("throw", text)
            self.assertIn("DKMS", text)
            self.assertTrue((Path(td) / "LIMITATIONS.md").is_file())

    def test_chrome_gnome_shell_token_is_cli(self) -> None:
        path = ROOT / "fixtures" / "fake-chrome-gnome-shell_0.0.1_amd64.deb"
        if not path.is_file():
            self.skipTest("chrome-gnome-shell fixture missing; run scripts/make-fixtures.sh")
        with TemporaryDirectory() as td:
            result = run(str(path), Path(td), skip_locate=True)
            self.assertEqual(result.classification.profile, "cli")
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("autoPatchelfHook", package)
            self.assertNotIn("throw", package.split("meta")[0])

    def test_opt_cli_rewrites_wrapper(self) -> None:
        path = ROOT / "fixtures" / "fake-opt-cli_0.0.1_amd64.deb"
        if not path.is_file():
            self.skipTest("opt-cli fixture missing; run scripts/make-fixtures.sh")
        with TemporaryDirectory() as td:
            result = run(str(path), Path(td), skip_locate=True)
            self.assertEqual(result.classification.profile, "cli")
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("ln -sfn", package)
            self.assertIn("x7fELF", package)

    def test_src_url_stamps_fetchurl_without_copying_deb(self) -> None:
        with TemporaryDirectory() as td:
            run(
                str(HELLO),
                Path(td),
                skip_locate=True,
                src_url="https://example.com/hello-deb2nix.deb",
            )
            package = (Path(td) / "package.nix").read_text()
            self.assertIn("fetchurl", package)
            self.assertIn("https://example.com/hello-deb2nix.deb", package)
            self.assertFalse((Path(td) / "src.deb").exists())


if __name__ == "__main__":
    unittest.main()
