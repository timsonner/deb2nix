#!/usr/bin/env bash
# Generate the CLI fixture, run deb2nix, nix build the output, run the binary.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export PATH="/nix/var/nix/profiles/default/bin:$PATH"

if [[ ! -f "$ROOT/fixtures/hello-deb2nix_0.1.0_amd64.deb" ]]; then
  bash "$ROOT/scripts/make-fixtures.sh"
fi

OUT="${TMPDIR:-/tmp}/deb2nix-smoke-hello"
rm -rf "$OUT"
python3 -m deb2nix "$ROOT/fixtures/hello-deb2nix_0.1.0_amd64.deb" --out "$OUT" --skip-locate

echo "---- generated package.nix ----"
cat "$OUT/package.nix"

echo "---- nix build ----"
nix build "$OUT" --no-link --print-out-paths | tee "$OUT/store-path.txt"
STORE="$(cat "$OUT/store-path.txt")"
"$STORE/bin/hello-deb2nix"

echo "---- classifier electron vs cli ----"
EOUT="${TMPDIR:-/tmp}/deb2nix-smoke-electron"
rm -rf "$EOUT"
python3 -m deb2nix "$ROOT/fixtures/fake-electron-app_0.0.1_amd64.deb" --out "$EOUT" --skip-locate
python3 - <<PY
import json
from pathlib import Path
hello = json.loads(Path("$OUT/report.json").read_text())
elec = json.loads(Path("$EOUT/report.json").read_text())
assert hello["profile"]["profile"] == "cli", hello["profile"]
assert elec["profile"]["profile"] == "electron", elec["profile"]
print("classifier: hello ->", hello["profile"]["profile"])
print("classifier: fake-electron ->", elec["profile"]["profile"])
drv = Path("$EOUT/package.nix").read_text()
assert "throw" in drv
print("electron stub throws, as expected")
PY

echo "smoke ok"
