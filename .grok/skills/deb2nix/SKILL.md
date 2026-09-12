---
name: deb2nix
description: >
  Work on the deb2nix Debian .deb → Nix generator. Use when converting a .deb,
  classifying profiles, emitting flakes, running smoke, or the user mentions
  deb2nix, autoPatchelfHook, or /deb2nix.
---

# deb2nix

Read `README.md` and `STATUS.md` before changing emit, classify, or license mapping. Do not restate those docs here.

## Run

```bash
nix run .#deb2nix -- ./app.deb
nix run .#deb2nix -- ./app.deb --src-url https://example.com/app.deb --out ./out --skip-locate
nix develop -c python3 -m unittest discover -s tests -v
bash scripts/smoke.sh
```

Do not add generator tools (`python3`, `dpkg`, `gcc`, `binutils`) to NixOS `environment.systemPackages` unless the user asks. Use `nix run` / `nix develop`.

## Hard rules

- Input must be a Debian `.deb`. Reject Makeself `.run` and vendor `.zip` (DisplayLink Ubuntu EXE is a `.run` zip, not a deb). See `docs/DISPLAYLINK.md`.
- Never `insmod`, DKMS, `modprobe`, or enable `hardware.video.displaylink` / `evdi`.
- Never emit `--no-sandbox` or setuid `*-sandbox`. Mode 0755; Nix store will show 555.
- Never silent `buildFHSEnv`. `fhs-fallback` and `driver` / `system` throw.
- Classify from payload only (`app.asar`, `chrome-sandbox`, `DT_NEEDED`, `.ko` / `dkms.conf`). Not product names.
- Generator does not set `allowUnfree`. Flake builds: `NIXPKGS_ALLOW_UNFREE=1 nix build --impure`.
- Do not open a public nixpkgs PR from this tool.

## Emit notes

- Userland profiles (`cli`, `electron`, `chromium-browser`, `gtk`, `qt`): `autoPatchelfHook`, unpack via `dpkg-deb --fsys-tarfile`.
- X11 attrs are flat (`libx11`, not `xorg.libX11`).
- Placeholder `License:` (`unknown`, `n/a`) → `lib.licenses.free`. Debian `non-free` → `lib.licenses.unfree`.
- `nix build` is not GUI smoke and **not an install**. The binary is not on `PATH`. Electron `--version` may open a window.
- After generate + build, **ask every time** how to install. Do not reuse the last choice as a default.
  - run `./result/bin/<pname>` (or the store path) — no PATH change
  - `nix profile add ./result` — user profile, `~/.nix-profile/bin`
  - NixOS `environment.systemPackages` via `pkgs.callPackage ./package.nix {}` — needs rebuild
- Do not `nix profile add` or edit nixos-config until the user picks.
- Uninstall the same channel. No dpkg db; `report.json` is not an install manifest.
  - `nix profile remove <pname>` if it was `nix profile add`
  - drop `callPackage` + `nixos-rebuild` if it was NixOS
  - `nix-collect-garbage` for unreferenced store paths
  - `$HOME` app config is not in the profile; **ask** before deleting
- Do not `nix profile remove` or GC until the user picks.
- Vendor blobs stay gitignored under `fixtures/vendor/`. Pins live in `fixtures/vendor/LOCK.json`. Regenerating examples needs those blobs: `bash scripts/generate-vendor-examples.sh`.
