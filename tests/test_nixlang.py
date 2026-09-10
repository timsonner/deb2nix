"""Nix identifier sanitization."""

from __future__ import annotations

import unittest

from deb2nix.nixlang import nix_ident, nix_string


class NixlangTests(unittest.TestCase):
    def test_ident(self) -> None:
        self.assertEqual(nix_ident("hello-deb2nix"), "hello-deb2nix")
        self.assertEqual(nix_ident("1password"), "pkg-1password")
        self.assertEqual(nix_ident("Google Chrome"), "google-chrome")

    def test_string_escapes(self) -> None:
        self.assertEqual(nix_string('say "hi"'), '"say \\"hi\\""')
        self.assertIn("\\${", nix_string("${foo}"))


if __name__ == "__main__":
    unittest.main()
