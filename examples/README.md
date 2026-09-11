# Generated examples (hash-pinned, no vendor blobs)

These trees were produced by `scripts/generate-vendor-examples.sh` from `fixtures/vendor/*.deb` after the 2026-09-10 EULA approval. The `.deb` files are gitignored; `fetchurl` URLs + SRI hashes are in each `package.nix` / `report.json`.

| Directory | Profile | `nix build` (this VM, 2026-09-10) |
| --- | --- | --- |
| `google-chrome-stable` | `chromium-browser` | `/bin/google-chrome-stable` (Qt shims ignored) |
| `microsoft-edge-stable` | `chromium-browser` | `/bin/microsoft-edge-stable` |
| `vscode` | `electron` | `/bin/code` |
| `grok-bot` | `electron` | `/bin/grok-bot` |
| `displaylink-driver` | `driver` | **throws** (see `LIMITATIONS.md`) |
| `synaptics-repository-keyring` | `fhs-fallback` (no ELF/binaries) | **throws** — APT keyring only, not the driver |

Generated flakes do not set `allowUnfree`.

```bash
nix build ./examples/google-chrome-stable
# DisplayLink is supposed to fail:
nix eval ./examples/displaylink-driver#packages.x86_64-linux.default
```

GUI smoke (Hyprland) is out of scope for these expressions. Regenerating:

```bash
bash scripts/generate-vendor-examples.sh
```
