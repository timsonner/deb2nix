#!/usr/bin/env bash
# Build the tiny CLI .deb (real ELF) and classifier-only marker .debs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIXTURES="$ROOT/fixtures"
mkdir -p "$FIXTURES"

build_hello() {
  local work pkg
  work="$(mktemp -d)"
  pkg="$work/hello-deb2nix"
  mkdir -p "$pkg/usr/bin" "$pkg/DEBIAN"
  gcc -O2 -s -o "$pkg/usr/bin/hello-deb2nix" "$FIXTURES/hello-cli/hello.c"
  chmod 0755 "$pkg/usr/bin/hello-deb2nix"
  cat >"$pkg/DEBIAN/control" <<'EOF'
Package: hello-deb2nix
Version: 0.1.0
Architecture: amd64
Maintainer: deb2nix <deb2nix@example.com>
Depends: libc6
Section: utils
Priority: optional
Homepage: https://example.com/hello-deb2nix
License: MIT
Description: Tiny CLI negative control for deb2nix
 A dynamically linked hello-world used as the Phase 1 fixture.
 MIT-licensed, no GUI, no Electron, no kernel modules.
EOF
  dpkg-deb --root-owner-group --build "$pkg" "$FIXTURES/hello-deb2nix_0.1.0_amd64.deb"
  echo "wrote $FIXTURES/hello-deb2nix_0.1.0_amd64.deb"
  rm -rf "$work"
}

build_electron_markers() {
  local work pkg
  work="$(mktemp -d)"
  pkg="$work/fake-electron-app"
  mkdir -p \
    "$pkg/opt/fake-electron-app/resources" \
    "$pkg/usr/bin" \
    "$pkg/DEBIAN"
  : >"$pkg/opt/fake-electron-app/resources/app.asar"
  : >"$pkg/opt/fake-electron-app/chrome-sandbox"
  : >"$pkg/opt/fake-electron-app/icudtl.dat"
  : >"$pkg/opt/fake-electron-app/resources.pak"
  : >"$pkg/opt/fake-electron-app/v8_context_snapshot.bin"
  cat >"$pkg/usr/bin/fake-electron-app" <<'EOF'
#!/bin/sh
echo "marker only — not a real Electron binary"
EOF
  chmod 0755 "$pkg/usr/bin/fake-electron-app"
  cat >"$pkg/DEBIAN/control" <<'EOF'
Package: fake-electron-app
Version: 0.0.1
Architecture: amd64
Maintainer: deb2nix <deb2nix@example.com>
Section: utils
Priority: optional
License: MIT
Description: Synthetic Electron-marker tree for classifier tests
 Contains app.asar, chrome-sandbox, icudtl.dat, resources.pak.
 Not a real Electron application and not licensed GUI software.
EOF
  dpkg-deb --root-owner-group --build "$pkg" "$FIXTURES/fake-electron-app_0.0.1_amd64.deb"
  echo "wrote $FIXTURES/fake-electron-app_0.0.1_amd64.deb"
  rm -rf "$work"
}

build_chromium_markers() {
  local work pkg
  work="$(mktemp -d)"
  pkg="$work/fake-chromium-browser"
  mkdir -p "$pkg/opt/fake-chromium-browser" "$pkg/usr/bin" "$pkg/DEBIAN"
  : >"$pkg/opt/fake-chromium-browser/chrome-sandbox"
  : >"$pkg/opt/fake-chromium-browser/icudtl.dat"
  : >"$pkg/opt/fake-chromium-browser/resources.pak"
  cat >"$pkg/usr/bin/fake-chromium-browser" <<'EOF'
#!/bin/sh
echo "marker only — not Chrome/Edge"
EOF
  chmod 0755 "$pkg/usr/bin/fake-chromium-browser"
  cat >"$pkg/DEBIAN/control" <<'EOF'
Package: fake-chromium-browser
Version: 0.0.1
Architecture: amd64
Maintainer: deb2nix <deb2nix@example.com>
Section: web
Priority: optional
License: MIT
Description: Synthetic Chromium-browser marker for classifier tests
 chrome-sandbox + icudtl.dat + resources.pak, no app.asar.
 Distinguishes browser .debs from Electron-shell apps.
 Not licensed GUI software.
EOF
  dpkg-deb --root-owner-group --build "$pkg" "$FIXTURES/fake-chromium-browser_0.0.1_amd64.deb"
  echo "wrote $FIXTURES/fake-chromium-browser_0.0.1_amd64.deb"
  rm -rf "$work"
}

build_driver_markers() {
  local work pkg
  work="$(mktemp -d)"
  pkg="$work/fake-displaylink"
  mkdir -p "$pkg/usr/src/evdi-0.0/dkms" "$pkg/lib/modules/placeholder" "$pkg/DEBIAN"
  echo "# synthetic dkms.conf — not a real DisplayLink driver" >"$pkg/usr/src/evdi-0.0/dkms.conf"
  echo "fake" >"$pkg/lib/modules/placeholder/evdi.ko"
  cat >"$pkg/DEBIAN/control" <<'EOF'
Package: displaylink-driver
Version: 0.0.1
Architecture: amd64
Maintainer: deb2nix <deb2nix@example.com>
Section: kernel
Priority: optional
License: MIT
Description: Synthetic DisplayLink/EVDI marker for classifier tests
 Contains dkms.conf and a dummy .ko. Not the Synaptics driver.
 Do not load this; it is not a kernel module.
EOF
  dpkg-deb --root-owner-group --build "$pkg" "$FIXTURES/fake-displaylink_0.0.1_amd64.deb"
  echo "wrote $FIXTURES/fake-displaylink_0.0.1_amd64.deb"
  rm -rf "$work"
}

build_hello
build_electron_markers
build_chromium_markers
build_driver_markers
