# deb2nix

Package-agnostic Debian `.deb` → Nix generator. Point it at any `.deb` (path or URL) and it writes a **profiled** `flake.nix` / `package.nix`. It does **not** assume Electron.

```bash
nix run .#deb2nix -- ./app.deb
nix run .#deb2nix -- https://example.com/app.deb --out ./generated
```

Phase 1 (this tree) fully implements the **`cli`** profile (`autoPatchelfHook`). Other profiles are classified with real heuristics and then **stubbed with an honest `throw`** — never a silent `buildFHSEnv`, never app2nix's Electron-default `--no-sandbox`, never a DisplayLink/DKMS kernel load.

GREENFIELD hybrid: reimplement unpack + ELF mapping ideas; do not fork app2nix (license metadata empty). See [`STATUS.md`](STATUS.md) and [`docs/PRIOR-ART.md`](docs/PRIOR-ART.md).

## Profiles

| Profile | When | Phase 1 emit |
| --- | --- | --- |
| `cli` | ELF binaries, no GUI/driver markers | Working derivation: unpack with `dpkg-deb`, `autoPatchelfHook`, hash-pinned `src` |
| `electron` | `app.asar` / Grok Bot / VS Code | `throw` + stub notes (Phase 2) |
| `chromium-browser` | Chrome / Edge: `chrome-sandbox` without `app.asar` | `throw` + stub notes (Phase 2, distinct emit) |
| `gtk` / `qt` | `DT_NEEDED` on GTK/Qt | stub `throw` |
| `driver` / `system` | `.ko`, `dkms.conf`, DisplayLink/EVDI | stub `throw` (Phase 3 parked; will not insmod) |
| `fhs-fallback` | no other match, or too much unknown | stub `throw` (refuses silent FHS) |

`--profile` overrides the classifier; `auto` **never** defaults to Electron.

## Usage

```bash
# local .deb → ./hello-deb2nix-nix/{flake.nix,package.nix,default.nix,report.json,src.deb}
nix run .#deb2nix -- ./hello.deb

# URL, explicit output dir (fetchurl + SRI hash in package.nix)
nix run .#deb2nix -- https://example.com/app.deb --out ./generated

# inspect classification only via the report
nix run .#deb2nix -- ./app.deb --out /tmp/out --json --skip-locate
```

Flags:

- `--out DIR` — write here (default: `./<pname>-nix`)
- `--profile auto|cli|electron|chromium-browser|gtk|qt|driver|system|fhs-fallback`
- `--skip-locate` — builtin `.so` → nixpkgs map only (no `nix-locate`)
- `--keep-unpack` — also copy the unpacked tree
- `--json` — print `report.json` to stdout

Then, for a **cli** result:

```bash
nix build ./hello-deb2nix-nix
./result/bin/hello-deb2nix
```

Non-cli results evaluate to `throw` until that profile is implemented. That is deliberate.

## What it actually does

1. Fetch a URL or copy a local `.deb`.
2. SRI-hash it (`sha256-…`) in Python — hash-pinned output, no floating `fetchurl`.
3. Unpack with `dpkg-deb` (fallback: `ar` + `tar`).
4. Parse `control`, inventory files, scan ELF `DT_NEEDED` (`readelf` / `patchelf` / struct fallback).
5. Map libraries via a builtin table, then `nix-locate` when it is on `PATH`.
6. Classify a profile (see table). `app.asar` selects `electron`; Chromium sandbox/paks without asar select `chromium-browser`. GTK libs that Chromium also needs do not steal those profiles.
7. Emit `flake.nix`, `package.nix`, `default.nix`, `report.json`. Local inputs are copied to `src.deb`.

Unfree packages set `config.allowUnfreePredicate` for **that pname only**. Unknown licenses are treated as unfree rather than silently marked MIT. Nothing here is for publishing into nixpkgs.

## Constraints (honored)

- Unfree is explicit.
- Hashes are pinned.
- Honest failure > silent FHS.
- No DisplayLink / DKMS / `insmod` (see `fixtures/MATRIX.md`).
- GUI smoke for Electron/browsers is **not** this VM. Phase 2 is a NixOS + Hyprland machine. Phase 3 DisplayLink stays parked.

## Fixture matrix

Public GUI/driver `.deb`s are **documented, not downloaded** in this run (unfree GUI / kernel policy). The in-tree fixtures are synthetic:

- `fixtures/hello-deb2nix_0.1.0_amd64.deb` — tiny CLI, MIT, used for `nix build` smoke.
- `fixtures/fake-electron-app_0.0.1_amd64.deb` — `app.asar` markers (VS Code / Grok Bot family).
- `fixtures/fake-chromium-browser_0.0.1_amd64.deb` — sandbox/paks, no asar (Chrome / Edge family).
- `fixtures/fake-displaylink_0.0.1_amd64.deb` — dummy `dkms.conf` + `.ko` name; **not** a kernel module.

Rebuild them with `bash scripts/make-fixtures.sh`. Public URL table: [`fixtures/MATRIX.md`](fixtures/MATRIX.md). Status: [`STATUS.md`](STATUS.md).

## Develop / test

```bash
nix develop
PYTHONPATH=src python3 -m unittest discover -s tests -v
bash scripts/smoke.sh
```

Without Nix, you still need `python3 >= 3.11`, `dpkg-deb`, `gcc` (to rebuild fixtures), and `readelf` from binutils.

## Prior art (and how this differs)

GREENFIELD hybrid — see [`docs/PRIOR-ART.md`](docs/PRIOR-ART.md). Short version:

| Project | Relation |
| --- | --- |
| [Er1ckR1ck0/app2nix](https://github.com/Er1ckR1ck0/app2nix) | Ideas only (unpack, ELF `NEEDED`, `nix-locate`). **Not forked:** Electron-default emit + `--no-sandbox`; LICENSE file missing while flake claims MIT. |
| [milahu/deb2nix](https://github.com/milahu/deb2nix) | Name mapping only, not a derivation emitter. |
| [jordangarrison/grok-bot-flake](https://github.com/jordangarrison/grok-bot-flake) | Hand-written Electron `.deb` flake. Phase 2 `electron` pattern. |
| nixpkgs Chrome / Edge | Hand-written Chromium `.deb` repacks. Phase 2 `chromium-browser` pattern. |
| [nixpkgs#558990](https://github.com/NixOS/nixpkgs/pull/558990) | Draft `grok-bot` in nixpkgs. Private flakes only. |
| nixpkgs `signal-desktop` / `signal-desktop-bin` | Source-built vs prebuilt Electron emit shapes. |
| [nix-init](https://github.com/nix-community/nix-init) | Source/URL generators. Complementary: not a `.deb` unpacker. |

## License

MIT. Generated expressions inherit the **upstream** `.deb` license; unfree stays unfree.
