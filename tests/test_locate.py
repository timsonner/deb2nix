"""Library mapping uses the builtin table without nix-locate."""

from __future__ import annotations

import unittest

from deb2nix.locate import map_libraries


class LocateTests(unittest.TestCase):
    def test_zlib_and_system(self) -> None:
        result = map_libraries(
            ["libc.so.6", "libz.so.1", "libstdc++.so.6", "libmystery.so.1"],
            bundled_names=set(),
            skip_locate=True,
        )
        by_lib = {m.lib: m for m in result.mapped}
        self.assertEqual(by_lib["libc.so.6"].source, "system")
        self.assertEqual(by_lib["libz.so.1"].pkg, "zlib")
        self.assertEqual(by_lib["libstdc++.so.6"].pkg, "stdenv.cc.cc.lib")
        self.assertIn("libmystery.so.1", result.unmapped)
        self.assertIn("zlib", result.build_inputs)
        self.assertNotIn("stdenv.cc.cc.lib", result.build_inputs)

    def test_gmp_nl_webkit(self) -> None:
        result = map_libraries(
            ["libgmp.so.10", "libnl-3.so.200", "libwebkit2gtk-4.0.so.37"],
            bundled_names=set(),
            skip_locate=True,
        )
        by_lib = {m.lib: m for m in result.mapped}
        self.assertEqual(by_lib["libgmp.so.10"].pkg, "gmp")
        self.assertEqual(by_lib["libnl-3.so.200"].pkg, "libnl")
        self.assertEqual(by_lib["libwebkit2gtk-4.0.so.37"].pkg, "webkitgtk_4_0")

    def test_bundled_skipped(self) -> None:
        result = map_libraries(
            ["libfoo.so.1"],
            bundled_names={"libfoo.so.1"},
            skip_locate=True,
        )
        self.assertEqual(result.mapped[0].source, "bundled")
        self.assertEqual(result.build_inputs, [])

    def test_x11_maps_to_flat_attrs(self) -> None:
        result = map_libraries(
            ["libX11.so.6", "libxcb.so.1", "libXdamage.so.1"],
            bundled_names=set(),
            skip_locate=True,
        )
        by_lib = {m.lib: m for m in result.mapped}
        self.assertEqual(by_lib["libX11.so.6"].pkg, "libx11")
        self.assertEqual(by_lib["libxcb.so.1"].pkg, "libxcb")
        self.assertEqual(by_lib["libXdamage.so.1"].pkg, "libxdamage")
        self.assertNotIn("xorg.libX11", result.build_inputs)


if __name__ == "__main__":
    unittest.main()
