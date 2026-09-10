# STATUS — deb2nix Phase 1

Cloud VM, headless: **generate → `nix build` only**. No GUI smoke. No kernel modules.

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
| [jordangarrison/grok-bot-flake](https://github.com/jordangarrison/grok-bot-flake) + nixpkgs Chrome/Edge | Hand-written **deb-repack** patterns for Phase 2 emit. |
| Signal wiki / `signal-desktop-bin` | Electron emit shapes for Phase 2. |
| [nixpkgs#558990](https://github.com/NixOS/nixpkgs/pull/558990) | Draft grok-bot; we generate **private** flakes, no nixpkgs publish. |

Roadmap: **Phase 1** = cli-only working `default.nix` / `package.nix` + `nix build` smoke. **Phase 2** = `electron` (Grok Bot, VS Code) **and** `chromium-browser` (Chrome, Edge) as separate profiles. **Phase 3** = DisplayLink parked (Synaptics EULA + nixpkgs `requireFile` / unfree / `evdi` / `hardware.video.displaylink` — document only, no download, no kernel).

Full pack on some boxes: `/workspace/ops-graph/jobs/deb2nix-generator/prior-art.md` (unreachable here). Local copy of this decision: [`docs/PRIOR-ART.md`](docs/PRIOR-ART.md).

## What works (Phase 1)

- Flake app: `nix run .#deb2nix -- ./app.deb` and URL + `--out`.
- Unpack: `dpkg-deb` first, `ar`+`tar` fallback (app2nix-shaped pipeline, new code).
- `control` parse, file inventory, ELF `DT_NEEDED`, builtin `.so` → nixpkgs map, optional `nix-locate`.
- **cli profile emit is complete**: `stdenv.mkDerivation` + `autoPatchelfHook` + `dpkg-deb -x` + hash-pinned `src` (`fetchurl` or `./src.deb`).
- Classifier **does not default to Electron**. First-class profiles:
  - `electron`: `app.asar` / `app.asar.unpacked`, names like `code` / `grok-bot`
  - `chromium-browser`: Chrome/Edge/Brave — `chrome-sandbox` / paks **without** `app.asar`
  - `gtk` / `qt`: `DT_NEEDED`
  - `driver` / `system`: `.ko`, `dkms.conf`, DisplayLink/EVDI names (Phase 3 parked)
  - `cli`: leftover ELF/binaries
  - `fhs-fallback`: honest `throw`, not `buildFHSEnv`
- Synthetic fixtures in `fixtures/`:
  - CLI hello-world `.deb` generates a **buildable** expression (`scripts/smoke.sh` runs `nix build` and the binary).
  - Electron-marker `.deb` (`app.asar`) → `electron` → `throw`.
  - Chromium-browser-marker `.deb` (sandbox/paks, no asar) → `chromium-browser` → `throw`.
  - DisplayLink-marker `.deb` → `driver` → `throw` (no `insmod`, no DKMS).
- Unfree: `allowUnfreePredicate` for that pname only. Unknown license → unfree, not silent MIT.
- Docs: `README.md`, this file, `fixtures/MATRIX.md`, `docs/PRIOR-ART.md`.

## What is stubbed

| Profile | Phase | Stub behavior | Next implementation |
| --- | --- | --- | --- |
| `electron` | 2 | `throw` + `package.stub.nix` | Keep upstream Electron when `.node` is ABI-locked (grok-bot-flake). `autoPatchelfHook` + `wrapGAppsHook3`. **Not** app2nix `--no-sandbox`. Prefetch Grok Bot 0.47.0 hash then. |
| `chromium-browser` | 2 | `throw` + stub | nixpkgs `google-chrome` / `microsoft-edge` deb-repack, unfree, hash-pin. Distinct from Electron ABI. |
| `gtk` / `qt` | later | `throw` | Toolkit wraps. |
| `driver` / `system` | **3 parked** | `throw` | NixOS `hardware.video.displaylink` / `evdi` / `requireFile`. Never kernel load from this tool. |
| `fhs-fallback` | — | `throw` | Even `--profile fhs-fallback` still throws in Phase 1 so FHS cannot happen by accident. |

## What this run did **not** do

- Did not download Grok Bot, VS Code, Chrome, or Edge `.deb`s (unfree GUI). **Did not prefetch** the 0.47.0 Grok Bot hash (Phase 2).
- Did not download DisplayLink (EULA + kernel policy).
- Did not vendor app2nix sources (license unverified).
- Did not run Electron/browser GUI smoke. That needs NixOS + Hyprland.
- Did not open a nixpkgs PR.
- `nix-locate` is optional; smoke used `--skip-locate` (no nix-index database on this VM).

## Smoke (Phase 1)

```bash
bash scripts/make-fixtures.sh   # gcc + dpkg-deb
PYTHONPATH=src python3 -m unittest discover -s tests -v
bash scripts/smoke.sh           # generate cli expr + nix build + run hello
```

Expected (verified on the Phase 1 cloud VM, then taxonomy split):

- `nix build .#deb2nix` installs `deb2nix` and runs unit tests in `installCheckPhase`.
- `hello-deb2nix` profile `cli` → store path with `bin/hello-deb2nix` printing `hello from deb2nix fixture`.
- `fake-electron-app` profile `electron` → `package.nix` throws on `nix eval`.
- `fake-chromium-browser` profile `chromium-browser` → throw (not lumped into electron).
- `fake-displaylink` profile `driver` / subtype `displaylink` → throw (no kernel load).
- URL + `--out` emits `fetchurl { url = ...; hash = "sha256-…"; }`.

## Next steps

**Phase 2 — NixOS + Hyprland VM**

1. Prefetch Grok Bot 0.47.0 (`fixtures/MATRIX.md`); pin SRI. Known 0.44.0 pin is documented for cross-check only.
2. Implement `electron` emit from grok-bot-flake / signal-desktop-bin / vscode shapes — not app2nix's template.
3. Implement `chromium-browser` emit from nixpkgs Chrome/Edge.
4. GUI smoke: Grok Bot, VS Code, Chrome/Edge. Record GPU/sandbox/keyring failures honestly.
5. Optional: `nix-index-database` so `nix-locate` works in `nix run`.

**Phase 3 — DisplayLink parked**

Document Synaptics EULA and nixpkgs `requireFile` + `unfree` + `evdi` + `hardware.video.displaylink`. Never download or `insmod` from deb2nix.

## Known gaps

- Builtin lib map is incomplete; unmapped libs become `autoPatchelfIgnoreMissingDeps` on **cli** (listed in `report.json`). Visible, not silent.
- `License:` is often missing on Debian binaries; we then mark unfree unless the field maps cleanly (the CLI fixture sets `License: MIT`).
- Generated flakes pin `nixpkgs` to `nixos-unstable` **unpinned URL** (consumer `flake.lock` on first `nix build`). The `.deb` itself is SRI-pinned.
- Multi-arch `.deb`s other than amd64/arm64 are mapped coarsely.
- No Windows/macOS.
