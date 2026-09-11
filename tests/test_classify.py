"""Classifier must not default to Electron."""

from __future__ import annotations

import unittest

from deb2nix.classify import classify
from deb2nix.control import parse_control_text
from deb2nix.elf import ElfInfo
from deb2nix.inventory import Inventory


def _control(**fields: str):
    lines = [
        f"Package: {fields.get('package', 'demo')}",
        f"Version: {fields.get('version', '1')}",
        f"Architecture: {fields.get('architecture', 'amd64')}",
        f"Section: {fields.get('section', 'utils')}",
        f"Description: {fields.get('description', 'demo')}",
    ]
    if "depends" in fields:
        lines.append(f"Depends: {fields['depends']}")
    if "license" in fields:
        lines.append(f"License: {fields['license']}")
    return parse_control_text("\n".join(lines) + "\n")


class ClassifyTests(unittest.TestCase):
    def test_cli_hello(self) -> None:
        inv = Inventory(files=["usr/bin/hello-deb2nix"], binaries=["usr/bin/hello-deb2nix"])
        elfs = [ElfInfo(path="usr/bin/hello-deb2nix", needed=["libc.so.6"], is_elf=True)]
        c = classify(_control(package="hello-deb2nix", license="MIT"), inv, elfs)
        self.assertEqual(c.profile, "cli")

    def test_cli_negation_in_description(self) -> None:
        inv = Inventory(files=["usr/bin/hello-deb2nix"], binaries=["usr/bin/hello-deb2nix"])
        c = classify(
            _control(
                package="hello-deb2nix",
                description="MIT-licensed, no GUI, no Electron, no kernel modules",
            ),
            inv,
            [],
        )
        self.assertEqual(c.profile, "cli")

    def test_electron_asar(self) -> None:
        inv = Inventory(
            files=[
                "opt/app/resources/app.asar",
                "opt/app/chrome-sandbox",
                "usr/bin/app",
            ],
            binaries=["usr/bin/app"],
        )
        c = classify(_control(package="some-app"), inv, [])
        self.assertEqual(c.profile, "electron")
        self.assertNotEqual(c.profile, "cli")
        self.assertNotEqual(c.profile, "chromium-browser")

    def test_package_name_alone_is_not_electron(self) -> None:
        inv = Inventory(files=["usr/share/code/code"], binaries=["usr/share/code/code"])
        c = classify(_control(package="code", description="Visual Studio Code"), inv, [])
        self.assertEqual(c.profile, "cli")

    def test_chrome_sandbox_is_chromium_browser_not_electron(self) -> None:
        inv = Inventory(
            files=["opt/vendor/app/chrome-sandbox", "opt/vendor/app/icudtl.dat", "opt/vendor/app/resources.pak"],
            binaries=["opt/vendor/app/app"],
        )
        c = classify(_control(package="any-browser"), inv, [])
        self.assertEqual(c.profile, "chromium-browser")
        self.assertNotEqual(c.profile, "electron")

    def test_asar_wins_over_chrome_sandbox(self) -> None:
        inv = Inventory(
            files=["opt/app/resources/app.asar", "opt/app/chrome-sandbox"],
            binaries=["opt/app/app"],
        )
        c = classify(_control(package="any-app"), inv, [])
        self.assertEqual(c.profile, "electron")

    def test_gtk(self) -> None:
        inv = Inventory(files=["usr/bin/gedit-like"], binaries=["usr/bin/gedit-like"])
        elfs = [
            ElfInfo(
                path="usr/bin/gedit-like",
                needed=["libgtk-3.so.0", "libglib-2.0.so.0", "libc.so.6"],
                is_elf=True,
            )
        ]
        c = classify(_control(package="gedit-like"), inv, elfs)
        self.assertEqual(c.profile, "gtk")

    def test_qt(self) -> None:
        inv = Inventory(files=["usr/bin/qtapp"], binaries=["usr/bin/qtapp"])
        elfs = [ElfInfo(path="usr/bin/qtapp", needed=["libQt6Core.so.6"], is_elf=True)]
        c = classify(_control(package="qtapp"), inv, elfs)
        self.assertEqual(c.profile, "qt")

    def test_displaylink_driver(self) -> None:
        inv = Inventory(
            files=["usr/src/evdi-1/dkms.conf", "lib/modules/x/evdi.ko"],
            kernel_modules=["lib/modules/x/evdi.ko"],
        )
        c = classify(
            _control(package="some-kmod", description="a kernel helper"),
            inv,
            [],
        )
        self.assertIn(c.profile, {"driver", "system"})
        self.assertTrue(any("kernel" in w.lower() or "dkms" in w.lower() for w in c.warnings))

    def test_override(self) -> None:
        inv = Inventory(files=["usr/bin/x"], binaries=["usr/bin/x"])
        c = classify(_control(package="x"), inv, [], override="gtk")
        self.assertEqual(c.profile, "gtk")
        self.assertEqual(c.confidence, "overridden")

    def test_unknown_override(self) -> None:
        with self.assertRaises(ValueError):
            classify(_control(package="x"), Inventory(), [], override="electron-default")

    def test_chrome_token_alone_is_not_chromium_browser(self) -> None:
        inv = Inventory(
            files=["usr/bin/chrome-gnome-shell"],
            binaries=["usr/bin/chrome-gnome-shell"],
        )
        c = classify(
            _control(
                package="chrome-gnome-shell",
                description="GNOME Shell integration for Google Chrome",
            ),
            inv,
            [],
        )
        self.assertEqual(c.profile, "cli")

    def test_nvidia_in_description_is_not_a_driver(self) -> None:
        inv = Inventory(
            files=["usr/bin/nvidia-settings"],
            binaries=["usr/bin/nvidia-settings"],
        )
        c = classify(
            _control(
                package="nvidia-settings",
                description="Tool for configuring the NVIDIA X driver",
                section="x11",
            ),
            inv,
            [],
        )
        self.assertEqual(c.profile, "cli")

    def test_product_name_without_kernel_payload_is_not_driver(self) -> None:
        inv = Inventory(files=["opt/vendor/Manager"], binaries=[])
        c = classify(
            _control(
                package="displaylink-driver",
                description="DisplayLink USB 3.x display driver",
                depends="libc6, evdi-dkms (>= 1.12.0) | evdi (>= 1.12.0)",
            ),
            inv,
            [],
        )
        self.assertEqual(c.profile, "cli")

    def test_many_unmapped_libs_still_cli(self) -> None:
        inv = Inventory(files=["usr/bin/fat-cli"], binaries=["usr/bin/fat-cli"])
        elfs = [
            ElfInfo(
                path="usr/bin/fat-cli",
                needed=[f"libmissing{i}.so.1" for i in range(12)] + ["libc.so.6"],
                is_elf=True,
            )
        ]
        c = classify(_control(package="fat-cli"), inv, elfs, unmapped=[f"libmissing{i}.so.1" for i in range(12)])
        self.assertEqual(c.profile, "cli")

    def test_paks_without_sandbox_or_known_name_are_not_browser(self) -> None:
        inv = Inventory(
            files=["usr/share/app/icudtl.dat", "usr/share/app/resources.pak", "usr/bin/app"],
            binaries=["usr/bin/app"],
        )
        c = classify(_control(package="random-cef-app"), inv, [])
        self.assertNotEqual(c.profile, "chromium-browser")
        self.assertNotEqual(c.profile, "electron")
        self.assertEqual(c.profile, "cli")


if __name__ == "__main__":
    unittest.main()
