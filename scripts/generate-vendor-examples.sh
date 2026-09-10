#!/usr/bin/env bash
# Generate hash-pinned examples from prefetched fixtures/vendor/*.deb.
# Blobs stay gitignored; only Nix + reports are committed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export PATH="/nix/var/nix/profiles/default/bin:$PATH"

python3 -m deb2nix.cli --version >/dev/null

gen() {
  local deb="$1" url="$2" out="$3"
  echo "==== generating $(basename "$out") ===="
  rm -rf "$out"
  python3 -m deb2nix.cli "$deb" --src-url "$url" --out "$out" --skip-locate
}

VENDOR="$ROOT/fixtures/vendor"
EX="$ROOT/examples"

gen "$VENDOR/google-chrome-stable_current_amd64.deb" \
  "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb" \
  "$EX/google-chrome-stable"

gen "$VENDOR/microsoft-edge-stable_152.0.4191.66-1_amd64.deb" \
  "https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/microsoft-edge-stable_152.0.4191.66-1_amd64.deb" \
  "$EX/microsoft-edge-stable"

gen "$VENDOR/code_amd64.deb" \
  "https://vscode.download.prss.microsoft.com/dbazure/download/stable/645f29cc3176500b4b5762ba887cf2a7f0ffdf2c/code_1.137.0-1788902055_amd64.deb" \
  "$EX/vscode"

gen "$VENDOR/grok-bot_0.47.0_amd64.deb" \
  "https://downloads.cursor.com/grokbot/stable/c1e7d7a46549956d25f53e9c0b9f59666e03aa3a/linux/x64/grok-bot_0.47.0_amd64.deb" \
  "$EX/grok-bot"

gen "$VENDOR/displaylink-driver_6.3.0-0ubuntu1~ppa3~noble1_amd64.deb" \
  "https://ppa.launchpadcontent.net/synaptics-displaylink/displaylink-driver/ubuntu/pool/main/d/displaylink-driver/displaylink-driver_6.3.0-0ubuntu1~ppa3~noble1_amd64.deb" \
  "$EX/displaylink-driver"

gen "$VENDOR/synaptics-repository-keyring.deb" \
  "https://www.synaptics.com/sites/default/files/Ubuntu/pool/stable/main/all/synaptics-repository-keyring.deb" \
  "$EX/synaptics-repository-keyring"

echo "vendor examples written under $EX"
