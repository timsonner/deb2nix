# STATUS — deb2nix Phase 0–1

Cloud VM, headless: **generate → `nix build` only**. No GUI smoke. No kernel modules.

## What works

- Flake app: `nix run .#deb2nix -- ./app.deb` and URL + `--out`.
- Unpack: `dpkg-deb` first, `ar`+`tar` fallback.
- `control` parse, file inventory, ELF `DT_NEEDED`, builtin `.so` → nixpkgs map, optional `nix-locate`.
- **cli profile emit is complete**: `stdenv.mkDerivation` + `autoPatchelfHook` + `dpkg-deb -x` + hash-pinned `src` (`fetchurl` or `./src.deb`).
- Classifier **does not default to Electron**. Heuristics:
  - electron: `app.asar`, `chrome-sandbox`, Chromium pak/icudtl, names like `code` / `google-chrome-stable` / `microsoft-edge-stable` / `grok-bot`
  - gtk / qt: `DT_NEEDED`
  - driver/system: `.ko`, `dkms.conf`, DisplayLink/EVDI names
  - cli: leftover ELF/binaries
  - fhs-fallback: honest `throw`, not `buildFHSEnv`
- Synthetic fixtures in `fixtures/`:
  - CLI hello-world `.deb` generates a **buildable** expression (`scripts/smoke.sh` runs `nix build` and the binary).
  - Electron-marker `.deb` classifies as `electron` and the emitted `package.nix` **throws**.
  - DisplayLink-marker `.deb` classifies as `driver`/`system` and throws (no `insmod`, no DKMS).
- Unfree: `allowUnfreePredicate` for that pname only. Unknown license → unfree, not silent MIT.
- Docs: `README.md`, this file, `fixtures/MATRIX.md` (public URLs, **no GUI/driver downloads** this run).

## What is stubbed (Phase 2)

| Profile | Stub behavior | Next implementation |
| --- | --- | --- |
| `electron` | `throw` + `package.stub.nix` | Keep upstream Electron when `.node` is ABI-locked (grok-bot-flake). `autoPatchelfHook` + `wrapGAppsHook3`. Do **not** copy app2nix `--no-sandbox`. Sandbox follows user namespaces. |
| Chromium browsers (Chrome / Edge) | classified `electron` / subtype `chromium-browser` | Same family, unfree, hash-pin `fetchurl`. GUI smoke later. |
| `gtk` / `qt` | `throw` | `wrapGAppsHook3` / `wrapQtAppsHook` + mapped toolkit libs. |
| `driver` / `system` | `throw` | NixOS module territory. **Never** DisplayLink kernel load from this tool. |
| `fhs-fallback` | `throw` | Only after explicit `--profile fhs-fallback` **and** a human-reviewed unmapped-lib list. Phase 1 still throws even with the override so FHS cannot happen by accident. |

## What this run did **not** do

- Did not download Grok Bot, VS Code, Chrome, or Edge `.deb`s (unfree GUI).
- Did not download DisplayLink (document only; no DKMS/kernel).
- Did not run Electron/browser GUI smoke. That needs NixOS + Hyprland.
- Did not open a nixpkgs PR (`nixpkgs#558990` is prior art, not a destination).
- `nix-locate` is optional; the smoke used `--skip-locate` because this VM has no nix-index database.

## Smoke (Phase 1)

```bash
bash scripts/make-fixtures.sh   # gcc + dpkg-deb
PYTHONPATH=src python3 -m unittest discover -s tests -v
bash scripts/smoke.sh           # generate cli expr + nix build + run hello
```

Expected:

- `hello-deb2nix` profile `cli` → store path with `bin/hello-deb2nix` printing `hello from deb2nix fixture`.
- `fake-electron-app` profile `electron` → `package.nix` contains `throw`.

## Next steps (Phase 2 — NixOS + Hyprland VM)

1. Download the MATRIX Electron/browser `.deb`s **on that machine**, run `deb2nix`, pin hashes into private flakes.
2. Implement electron emit (not FHS-first): unpack, patchelf bundled chrome, wrap GApps, desktop file `Exec` rewrite, `chrome-sandbox` policy documented.
3. GUI smoke: Grok Bot, VS Code, Chrome/Edge on Hyprland. Record failures honestly (GPU, sandbox, keyring).
4. Optional: `nix-index-database` input so `nix-locate` works in `nix run` without a local db.
5. gtk/qt emit once there is a non-Electron GUI fixture.
6. Still never: DisplayLink `insmod` / DKMS from deb2nix.

## Known gaps

- Builtin lib map is incomplete; unmapped libs become `autoPatchelfIgnoreMissingDeps` on **cli** (listed in `report.json`). That is visible, not silent.
- `License:` is often missing on Debian binaries; we then mark unfree unless the field maps cleanly (the CLI fixture sets `License: MIT`).
- Generated flakes pin `nixpkgs` to `nixos-unstable` **unpinned URL** (the generated flake.lock is the consumer's job on first `nix build`). The `.deb` itself is SRI-pinned.
- Multi-arch `.deb`s other than amd64/arm64 are mapped coarsely.
- No Windows/macOS.
