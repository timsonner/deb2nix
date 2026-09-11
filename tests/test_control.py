"""Control file parser tests."""

from __future__ import annotations

import unittest

from deb2nix.control import debian_arch_to_nix_system, parse_control_text


SAMPLE = """\
Package: hello-deb2nix
Version: 0.1.0
Architecture: amd64
Maintainer: deb2nix <deb2nix@example.com>
Depends: libc6 (>= 2.34)
Section: utils
Homepage: https://example.com/hello-deb2nix
License: MIT
Description: Tiny CLI negative control
 A dynamically linked hello-world.
 .
 Second paragraph.
"""


class ControlTests(unittest.TestCase):
    def test_fields(self) -> None:
        c = parse_control_text(SAMPLE)
        self.assertEqual(c.package, "hello-deb2nix")
        self.assertEqual(c.version, "0.1.0")
        self.assertEqual(c.architecture, "amd64")
        self.assertEqual(c.license, "MIT")
        self.assertEqual(c.synopsis, "Tiny CLI negative control")
        self.assertIn("dynamically linked", c.long_description)
        self.assertFalse(c.is_unfree())

    def test_unfree_section(self) -> None:
        c = parse_control_text(
            "Package: chrome\nVersion: 1\nArchitecture: amd64\nSection: non-free/web\nDescription: browser\n"
        )
        self.assertTrue(c.is_unfree())

    def test_arch(self) -> None:
        self.assertEqual(debian_arch_to_nix_system("amd64"), "x86_64-linux")
        self.assertEqual(debian_arch_to_nix_system("arm64"), "aarch64-linux")
        self.assertEqual(debian_arch_to_nix_system("all"), "x86_64-linux")

    def test_copyright_word_alone_is_not_unfree(self) -> None:
        c = parse_control_text(
            "Package: demo\nVersion: 1\nArchitecture: amd64\n"
            "License: MIT\nDescription: has a copyright file\n"
        )
        self.assertFalse(c.is_unfree())

    def test_missing_package(self) -> None:
        with self.assertRaises(ValueError):
            parse_control_text("Version: 1\n")


if __name__ == "__main__":
    unittest.main()
