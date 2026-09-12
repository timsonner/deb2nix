"""Install/remove how-to is cwd-safe (DIR/result, not ./result from cwd)."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from deb2nix.emit import emit_all
from deb2nix.howto import install_lines, remove_lines, result_link
from test_emit import _ctx


class HowtoTests(unittest.TestCase):
    def test_install_pins_result_under_out_dir(self) -> None:
        out = "/tmp/hello-deb2nix-nix"
        lines = install_lines(out, "hello-deb2nix")
        joined = "\n".join(lines)
        self.assertIn(f"nix build {out} -o {out}/result", joined)
        self.assertIn(f"{out}/result/bin/hello-deb2nix", joined)
        self.assertIn(f"nix profile add {out}/result", joined)
        self.assertIn("hash -r", joined)
        self.assertIn("nix profile list", joined)
        self.assertNotIn("nix profile add ./result\n", joined + "\n")

    def test_remove_uses_pname(self) -> None:
        lines = remove_lines("grok-bot")
        self.assertEqual(lines[0], "nix profile remove grok-bot")
        self.assertIn("nix-collect-garbage", lines)

    def test_result_link(self) -> None:
        self.assertEqual(result_link(Path("/x/y")), "/x/y/result")

    def test_notes_include_cwd_safe_steps(self) -> None:
        with TemporaryDirectory() as td:
            emit_all(Path(td), _ctx("electron"))
            notes = (Path(td) / "NOTES.md").read_text()
            self.assertIn("nix build . -o ./result", notes)
            self.assertIn("nix profile add ./result", notes)
            self.assertIn("hash -r", notes)
            self.assertIn("nix profile list", notes)
            self.assertIn("nixos-rebuild", notes)
            self.assertIn("nix profile remove hello-deb2nix", notes)


if __name__ == "__main__":
    unittest.main()
