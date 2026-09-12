# STATUS — deb2nix

Cloud VM, headless: **generate → `nix build` of userland expressions only**. No GUI smoke. No kernel modules.

## Tim approval (2026-09-10)

**All unfree / EULAs accepted**, including DisplayLink and browser/Electron `.deb`s (Chrome, Edge, VS Code, Grok Bot).

Allowed now:

- Prefetch + hash-pin of vendor `.deb`s (blobs gitignored under `fixtures/vendor/`; SRI in `fixtures/vendor/LOCK.json` and `fixtures/MATRIX.md`).
- Kernel-module `.deb`s documented as `driver`/`system` with **module stub + limitations report**.

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
  - `electron`: `app.asar` / `app.asar.unpacked` / `Depends: electron*` (not package names)
  - `chromium-browser`: `chrome-sandbox` without `app.asar` (not Chrome/Edge product names)
  - `gtk` / `qt`: `DT_NEEDED` → userland autoPatchelf + toolkit wrap
  - `driver` / `system`: `.ko`, `dkms.conf`, DisplayLink/EVDI names → **throw** + `LIMITATIONS.md` + `nixos-module.stub.nix`
  - `cli`: leftover ELF/binaries
  - `fhs-fallback`: honest `throw`, not `buildFHSEnv`
- Synthetic fixtures in `fixtures/` plus vendor pins in `fixtures/vendor/LOCK.json` (`.deb` blobs gitignored).
- License: Debian + nixpkgs convention. Known `License:` → `lib.licenses.*`; `non-free` → `unfree`; missing field **or placeholder** (`unknown`, `n/a`) on a free section → `lib.licenses.free`. No `allowUnfree` in generated flakes — the parent OS/user nixpkgs config decides. Grok Bot 0.47.0 is `License: unknown` / `Section: default`, so it does **not** trip the unfree gate despite being proprietary. That is field policy, not a product-name guess.

## What is stubbed

| Profile | Phase | Emit | Notes |
| --- | --- | --- | --- |
| `electron` | 2 userland | `stdenv.mkDerivation` + autoPatchelf + GApps | Examples: Grok Bot 0.47.0, VS Code 1.137.0. No `--no-sandbox`. GUI smoke later. |
| `chromium-browser` | 2 userland | same shape, distinct profile | Examples: Chrome `current`, Edge 152. Distinct from Electron ABI. |
| `gtk` / `qt` | 2 userland | autoPatchelf + GApps or Qt wrap | No FHS. GUI smoke later. |
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

Verified on this cloud VM (2026-09-10), generate → `nix build` only:

| Tree | Result |
| --- | --- |
| `nix build .#deb2nix` | unit tests in checkPhase |
| `hello-deb2nix` | prints `hello from deb2nix fixture` |
| `examples/grok-bot` | `/bin/grok-bot` (wraps `opt/Grok Bot/grok-bot`) |
| `examples/google-chrome-stable` | `/bin/google-chrome-stable`; Qt shim libs ignored (hook conflict) |
| `examples/microsoft-edge-stable` | `/bin/microsoft-edge-stable`; same Qt ignore |
| `examples/vscode` | `/bin/code` (wraps `share/code/bin/code`) |
| `examples/displaylink-driver` | `nix eval` **throws** (EVDI/DKMS not loaded) |

`chrome-sandbox` / `msedge-sandbox` in those store paths are mode `555`, not setuid. GUI smoke is still NixOS+Hyprland.

## 2026-09-12 — NixOS 26.05 + Hyprland laptop (Tim)

Re-ran generate + userland `nix build` against a local `grok-bot_0.47.0_amd64.deb` (same SRI as the 2026-09-10 pin). HEAD classifier/emit, not the stale committed `examples/grok-bot` tree.

| Check | Result |
| --- | --- |
| Classifier | `electron` (high) from `app.asar` / `app.asar.unpacked`. Not `chromium-browser`. No product-name reason. |
| Hash | `sha256-EcoPUaU1uXr1GjUq35wPns0uGwQwpprpRRtoinoGWAg=` |
| `nix build -f` | `/nix/store/…-grok-bot-0.47.0`; `$out/bin/grok-bot` wraps `opt/Grok Bot/grok-bot` |
| Sandbox | `chrome-sandbox` mode 555, not setuid. Wrapper has **no** `--no-sandbox`. |
| Runtime (accidental) | `grok-bot --version` started Electron on Wayland (`NIXOS_OZONE_WL`); renderer had `--enable-sandbox`. Killed; not a GUI sign-off. |
| DisplayLink zip in `~/Downloads` | Makeself `.run`, **not** a `.deb`. Did not install. Did not `insmod`. |

Lessons folded into the generator:

- `License: unknown` / `n/a` → `lib.licenses.free` (was a quoted Nix string `"unknown"`).
- Builtin + GUI extras emit `libx11` / `libxcb` / … not `xorg.libX11` (26.05 deprecation warnings).
- Local `.run` / `.zip` is an explicit error, not a cryptic suffix check.

## Next steps

**Phase 2 GUI smoke — this Hyprland box**

1. Launch the userland store path (`$out/bin/grok-bot`) under Hyprland. `--version` is not a display test (it may open a window).
2. Record GPU/sandbox/keyring failures honestly. Still no `--no-sandbox` as a generator default.
3. Optional: `nix-index-database` so `nix-locate` works in `nix run`.

**Phase 3 — DisplayLink**

A working driver needs NixOS `hardware.video.displaylink` + `evdi` on a machine the operator intends to reboot. deb2nix will not do that. See [`docs/DISPLAYLINK.md`](docs/DISPLAYLINK.md).

## Known gaps

- Builtin lib map is incomplete; unmapped libs become `autoPatchelfIgnoreMissingDeps` (listed in `report.json`). Visible, not silent. Userland `nix build` can succeed while the GUI still fails at runtime.
- `License:` is often missing on Debian binaries, or is a placeholder (`unknown`). That becomes `lib.licenses.free` (unspecified free), not a silent MIT and not a forced unfree. Debian `non-free` still maps to `lib.licenses.unfree` so NixOS `allowUnfree` applies. Proprietary apps that ship `License: unknown` (Grok Bot) therefore evaluate without `allowUnfree`.
- Generated flakes pin `nixpkgs` to `nixos-unstable` **unpinned URL** (consumer `flake.lock` on first `nix build`). The `.deb` itself is SRI-pinned.
- Multi-arch `.deb`s other than amd64/arm64 are mapped coarsely.
- No Windows/macOS.
- DisplayLink PPA package ships **userspace** `DisplayLinkManager` and depends on `evdi-dkms | evdi`. The official Ubuntu download is a Makeself `.run` zip, not a `.deb`. Patchelf-only userland is not claimed as a working driver.
- Committed `examples/` trees were generated before the content-based + license/xorg emit; regenerate with `scripts/generate-vendor-examples.sh` (needs `fixtures/vendor/*.deb`).
