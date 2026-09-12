"""Local input must be a .deb, not a vendor .run/.zip installer."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from deb2nix.fetch import fetch_deb


class FetchTests(unittest.TestCase):
    def test_rejects_run_installer(self) -> None:
        with TemporaryDirectory() as td:
            fake = Path(td) / "displaylink-driver-6.3.0-48.run"
            fake.write_bytes(b"#!/bin/sh\n# Makeself stub\n")
            with self.assertRaises(ValueError) as ctx:
                fetch_deb(str(fake), Path(td) / "dest")
            msg = str(ctx.exception)
            self.assertIn(".deb", msg)
            self.assertIn(".run", msg)
            self.assertIn("Makeself", msg)

    def test_rejects_zip(self) -> None:
        with TemporaryDirectory() as td:
            fake = Path(td) / "DisplayLink USB Graphics Software for Ubuntu6.3-EXE.zip"
            fake.write_bytes(b"PK\x03\x04")
            with self.assertRaises(ValueError) as ctx:
                fetch_deb(str(fake), Path(td) / "dest")
            self.assertIn("zip", str(ctx.exception).lower())

    def test_accepts_deb_suffix(self) -> None:
        with TemporaryDirectory() as td:
            src = Path(td) / "hello.deb"
            src.write_bytes(b"!<arch>\n")
            dest_dir = Path(td) / "dest"
            path, url = fetch_deb(str(src), dest_dir)
            self.assertIsNone(url)
            self.assertEqual(path.name, "hello.deb")
            self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
