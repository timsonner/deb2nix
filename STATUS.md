# STATUS — deb2nix

Cloud VM, headless: **generate → `nix build` of userland expressions only**. No GUI smoke. No kernel modules.

## Tim approval (2026-09-10)

**All unfree / EULAs accepted**, including DisplayLink and browser/Electron `.deb`s (Chrome, Edge, VS Code, Grok Bot).

Allowed now:

- `allowUnfreePredicate` (pname-scoped) in generated expressions. The generator flake itself stays MIT and does not set `allowUnfree = true`.
- Prefetch + hash-pin of vendor `.deb`s (blobs gitignored under `fixtures/vendor/`; SRI in `fixtures/vendor/LOCK.json` and `fixtures/MATRIX.md`).
- DisplayLink documented as `driver`/`system` with **module stub + limitations report**.

Still forbidden:

- Loading DKMS / kernel modules on any host (`insmod`, `modprobe`, enabling `hardware.video.displaylink`).
- Modifying Tim’s machines.
- Publishing generated expressions to public nixpkgs.

If DisplayLink cannot fully build without kernel hooks, an honest stub + report is **success** for Phase 1/3 prep.

## Approach (GREENFIELD hybrid)

Port **ideas** from [Er1ckR1ck0/app2nix](https://github.com/Er1ckR1ck0/app2nix) — unpack a `.deb`, scan ELF `DT_NEEDED`, map via `libraries.json` + optional `nix-locate` — into a **new** `deb2nix`. Do **not** fork or vendor app2nix, and do **not** copy its Electron-default emit (`--no-sandbox`, GTK/Electron single template).

**Why not fork app2nix**

- One Electron-flavored template conflicts with profiled emit (`cli` vs `electron` vs `chromium-browser` vs driver).
- ~25★, idle.
- **License is unverified:** GitHub `license: null`, no `LICENSE` file (HTTP 404), `Cargo.toml` has no `license` field, yet `flake.nix` sets `license = licenses.mit`. Do not copy substantial code until that is fixed upstream.

**What else is not a starting point**

| Ref | Role |
| --- | --- |
| [milahu/deb2nix](https://github.com/milahu/deb2nix) | Debian↔nixpkgs **name mapping** only (`nix-locate` / apt-file). Same name, different job. |
| [nix-init](https://github.com/nix-community/nix-init) | Source/URL generators (GitHub, crates, PyPI). Not a `.deb` unpacker. |
| [jordangarrison/grok-bot-flake](https://github.com/jordangarrison/grok-bot-flake) + nixpkgs Chrome/Edge | Hand-written **deb-repack** patterns for GUI emit. |
| Signal wiki / `signal-desktop-bin` | Electron emit shapes. |
| [nixpkgs#558990](https://github.com/NixOS/nixpkgs/pull/558990) | Draft grok-bot; we generate **private** flakes, no nixpkgs publish. |

Roadmap: **Phase 1** = cli emit + smoke. **Phase 2** = `electron` + `chromium-browser` **userland** `nix build` (GUI smoke still NixOS+Hyprland). **Phase 3** = DisplayLink parked at module stub (EULA accepted; still no kernel load).

Full pack on some boxes: `/workspace/ops-graph/jobs/deb2nix-generator/prior-art.md` (unreachable here). Local copy: [`docs/PRIOR-ART.md`](docs/PRIOR-ART.md). DisplayLink report: [`docs/DISPLAYLINK.md`](docs/DISPLAYLINK.md).

## What works

- Flake app: `nix run .#deb2nix -- ./app.deb` and URL + `--out`. Prefetched vendor blobs: `--src-url` stamps `fetchurl` without copying the `.deb` into the output.
- Unpack: `dpkg-deb` first, `ar`+`tar` fallback.
- `control` parse, file inventory, ELF `DT_NEEDED`, builtin `.so` → nixpkgs map, optional `nix-locate`.
- **cli profile emit is complete**: `stdenv.mkDerivation` + `autoPatchelfHook` + `dpkg-deb --fsys-tarfile` (no setuid unpack) + hash-pinned `src`.
- **electron / chromium-browser userland emit**: same unpack + `autoPatchelfHook` + `wrapGAppsHook3`. Does **not** add `--no-sandbox`. `chrome-sandbox` is mode 0755, never setuid. GUI smoke is still a later NixOS+Hyprland step.
- Classifier **does not default to Electron**. First-class profiles:
  - `electron`: `app.asar` / `app.asar.unpacked`, names like `code` / `grok-bot`
  - `chromium-browser`: Chrome/Edge/Brave — `chrome-sandbox` / paks **without** `app.asar`
  - `gtk` / `qt`: `DT_NEEDED` (still `throw`)
  - `driver` / `system`: `.ko`, `dkms.conf`, DisplayLink/EVDI names → **throw** + `LIMITATIONS.md` + `nixos-module.stub.nix`
  - `cli`: leftover ELF/binaries
  - `fhs-fallback`: honest `throw`, not `buildFHSEnv`
- Synthetic fixtures in `fixtures/` plus vendor pins in `fixtures/vendor/LOCK.json` (`.deb` blobs gitignored).
- Unfree: `allowUnfreePredicate` for that pname only. Unknown license → unfree, not silent MIT. Tim 2026-09-10 approval is recorded in generated headers; it does not blanket-enable nixpkgs unfree.

## What is stubbed

| Profile | Phase | Emit | Notes |
| --- | --- | --- | --- |
| `electron` | 2 userland | `stdenv.mkDerivation` + autoPatchelf + GApps | Examples: Grok Bot 0.47.0, VS Code 1.137.0. No `--no-sandbox`. GUI smoke later. |
| `chromium-browser` | 2 userland | same shape, distinct profile | Examples: Chrome `current`, Edge 152. Distinct from Electron ABI. |
| `gtk` / `qt` | later | `throw` | Toolkit wraps. |
| `driver` / `system` | **3 parked** | `throw` + module stub + `LIMITATIONS.md` | DisplayLink PPA 6.3.0 inspected. Userspace `DisplayLinkManager` exists; EVDI/DKMS is a **Depends**, not in this `.deb`. Never `insmod`. |
| `fhs-fallback` | — | `throw` | Even `--profile fhs-fallback` still throws so FHS cannot happen by accident. |

## Vendor pins (fetched 2026-09-10 after EULA approval)

See [`fixtures/vendor/LOCK.json`](fixtures/vendor/LOCK.json). Blobs are **not** in git.

| Package | Profile | SRI |
| --- | --- | --- |
| Grok Bot 0.47.0 | `electron` | `sha256-EcoPUaU1uXr1GjUq35wPns0uGwQwpprpRRtoinoGWAg=` |
| Google Chrome stable (`current` that day) | `chromium-browser` | `sha256-m7ROMwMcLyhXzza0NDBRoS+TBY5LeB48djE9+H9sjTI=` |
| VS Code 1.137.0-1788902055 | `electron` | `sha256-/U3/csRFmNOsuIW0SCVvXYLPU/WVONl/x9PI2NnVdNM=` |
| Microsoft Edge 152.0.4191.66-1 | `chromium-browser` | `sha256-GGwZ+dYHnRdO+7TvMxzMHhHRObb3qOo7DbdfmxfiXw0=` |
| DisplayLink driver 6.3.0 (Launchpad PPA noble) | `driver` | `sha256-zHVC+5aQb5cPwTVO2DwKhRVH96RoCa2zNlmKDjGxWKM=` |
| Synaptics APT keyring | keyring (not the driver) | `sha256-+DMAkohI8vdgX/hDhGcmcBnHzFGB7Iueq8fx4Fy/rL4=` |

Known **Grok Bot 0.44.0** pin (do not treat as 0.47.0): `sha256-3e0YstPUSxwy1rn2NEbSsnvKaLPeeiqgKM55VulpQWQ=`.

Rolling URLs (`google-chrome-stable_current_amd64.deb`, Code `latest`) **change**. Re-hash when refetching.

Generated trees (Nix + `report.json`, no blobs): [`examples/`](examples/).

## What this run did **not** do

- Did not `insmod` / DKMS / enable `hardware.video.displaylink` on any host.
- Did not modify Tim’s machines.
- Did not vendor app2nix sources (license unverified).
- Did not run Electron/browser GUI smoke. That needs NixOS + Hyprland.
- Did not open a nixpkgs PR.
- `nix-locate` is optional; vendor generate used `--skip-locate` (no nix-index database on this VM). Unmapped libs become `autoPatchelfIgnoreMissingDeps` and are listed in `report.json`.

## Smoke

```bash
bash scripts/make-fixtures.sh   # gcc + dpkg-deb
PYTHONPATH=src python3 -m unittest discover -s tests -v
bash scripts/smoke.sh           # generate cli expr + nix build + run hello
# after EULA approval, vendor examples:
bash scripts/generate-vendor-examples.sh
nix build ./examples/google-chrome-stable   # userland only
```

Expected:

- `nix build .#deb2nix` installs `deb2nix` and runs unit tests in `checkPhase`.
- `hello-deb2nix` profile `cli` → `bin/hello-deb2nix` prints `hello from deb2nix fixture`.
- `fake-electron-app` → `electron` **userland** `package.nix` (autoPatchelf, no sandbox-disable flags).
- `fake-chromium-browser` → `chromium-browser` userland (not lumped into electron).
- `fake-displaylink` → `driver` / subtype `displaylink` → `throw` (no kernel load).
- URL / `--src-url` + `--out` emits `fetchurl { url = ...; hash = "sha256-…"; }`.
- Real DisplayLink `.deb` → `throw` + `LIMITATIONS.md` + `nixos-module.stub.nix`. `nix eval` of that package is expected to fail with the throw; that is success.

## Next steps

**Phase 2 GUI smoke — NixOS + Hyprland VM** (not this cloud run)

1. Install the userland store paths from `examples/{grok-bot,vscode,google-chrome-stable,microsoft-edge-stable}`.
2. Record GPU/sandbox/keyring failures honestly. Still no `--no-sandbox` as a generator default.
3. Optional: `nix-index-database` so `nix-locate` works in `nix run`.

**Phase 3 — DisplayLink**

A working driver needs NixOS `hardware.video.displaylink` + `evdi` on a machine the operator intends to reboot. deb2nix will not do that. See [`docs/DISPLAYLINK.md`](docs/DISPLAYLINK.md).

## Known gaps

- Builtin lib map is incomplete; unmapped libs become `autoPatchelfIgnoreMissingDeps` (listed in `report.json`). Visible, not silent. Userland `nix build` can succeed while the GUI still fails at runtime.
- `License:` is often missing on Debian binaries; we then mark unfree unless the field maps cleanly (the CLI fixture sets `License: MIT`).
- Generated flakes pin `nixpkgs` to `nixos-unstable` **unpinned URL** (consumer `flake.lock` on first `nix build`). The `.deb` itself is SRI-pinned.
- Multi-arch `.deb`s other than amd64/arm64 are mapped coarsely.
- No Windows/macOS.
- DisplayLink PPA package ships **userspace** `DisplayLinkManager` and depends on `evdi-dkms | evdi`. Patchelf-only userland is not claimed as a working driver.
