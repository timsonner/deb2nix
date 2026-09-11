#!/usr/bin/env bash
# Generate the CLI fixture, run deb2nix, nix build the output, run the binary.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/nix/var/nix/profiles/default/bin:$PATH"

if [[ ! -f "$ROOT/fixtures/hello-deb2nix_0.1.0_amd64.deb" ]]; then
  bash "$ROOT/scripts/make-fixtures.sh"
fi

OUT="${TMPDIR:-/tmp}/deb2nix-smoke-hello"
rm -rf "$OUT"
nix run "$ROOT"#deb2nix -- "$ROOT/fixtures/hello-deb2nix_0.1.0_amd64.deb" --out "$OUT" --skip-locate

echo "---- generated package.nix ----"
cat "$OUT/package.nix"

echo "---- nix build ----"
nix build "$OUT" --no-link --print-out-paths | tee "$OUT/store-path.txt"
STORE="$(cat "$OUT/store-path.txt")"
"$STORE/bin/hello-deb2nix"

echo "---- classifier electron vs chromium-browser vs cli vs tokens ----"
EOUT="${TMPDIR:-/tmp}/deb2nix-smoke-electron"
COUT="${TMPDIR:-/tmp}/deb2nix-smoke-chromium"
GOUT="${TMPDIR:-/tmp}/deb2nix-smoke-chrome-token"
OOUT="${TMPDIR:-/tmp}/deb2nix-smoke-opt-cli"
rm -rf "$EOUT" "$COUT" "$GOUT" "$OOUT"
nix run "$ROOT"#deb2nix -- "$ROOT/fixtures/fake-electron-app_0.0.1_amd64.deb" --out "$EOUT" --skip-locate
nix run "$ROOT"#deb2nix -- "$ROOT/fixtures/fake-chromium-browser_0.0.1_amd64.deb" --out "$COUT" --skip-locate
nix run "$ROOT"#deb2nix -- "$ROOT/fixtures/fake-chrome-gnome-shell_0.0.1_amd64.deb" --out "$GOUT" --skip-locate
nix run "$ROOT"#deb2nix -- "$ROOT/fixtures/fake-opt-cli_0.0.1_amd64.deb" --out "$OOUT" --skip-locate
python3 - <<PY
import json
import re
from pathlib import Path
hello = json.loads(Path("$OUT/report.json").read_text())
elec = json.loads(Path("$EOUT/report.json").read_text())
chrome = json.loads(Path("$COUT/report.json").read_text())
token = json.loads(Path("$GOUT/report.json").read_text())
optcli = json.loads(Path("$OOUT/report.json").read_text())
assert hello["profile"]["profile"] == "cli", hello["profile"]
assert elec["profile"]["profile"] == "electron", elec["profile"]
assert chrome["profile"]["profile"] == "chromium-browser", chrome["profile"]
assert token["profile"]["profile"] == "cli", token["profile"]
assert optcli["profile"]["profile"] == "cli", optcli["profile"]
print("classifier: hello ->", hello["profile"]["profile"])
print("classifier: fake-electron ->", elec["profile"]["profile"])
print("classifier: fake-chromium-browser ->", chrome["profile"]["profile"])
print("classifier: chrome-gnome-shell token ->", token["profile"]["profile"])
print("classifier: opt-cli ->", optcli["profile"]["profile"])
e_pkg = Path("$EOUT/package.nix").read_text()
c_pkg = Path("$COUT/package.nix").read_text()
o_pkg = Path("$OOUT/package.nix").read_text()
assert "autoPatchelfHook" in e_pkg
assert "autoPatchelfHook" in c_pkg
assert "x7fELF" in o_pkg
assert "ln -sfn" in o_pkg
for pkg in (e_pkg, c_pkg):
    assert not re.search(r'--add-flags\s+"--no-sandbox"', pkg)
    assert not re.search(r"wrapProgram[^\n]*--no-sandbox", pkg)
assert "ELECTRON_FORCE_IS_PACKAGED" in e_pkg
assert "ELECTRON_FORCE_IS_PACKAGED" not in c_pkg
print("electron and chromium-browser userland exprs (no sandbox-disable flags)")
PY

echo "---- nix build opt-cli and run wrapper ----"
nix build "$OOUT" --no-link --print-out-paths | tee "$OOUT/store-path.txt"
STORE_OPT="$(cat "$OOUT/store-path.txt")"
"$STORE_OPT/bin/fake-opt-cli"

echo "smoke ok"
