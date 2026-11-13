# deb2nix

deb2nix reads a Debian `.deb` (local path or `http`/`https` URL) and writes a Nix flake for that archive. It classifies the payload from its files and ELF `DT_NEEDED` entries, then emits `flake.nix`, `package.nix`, `default.nix`, and `report.json`. Userland profiles (`cli`, `gtk`, `qt`, `electron`, `chromium-browser`) get an `autoPatchelfHook` derivation. `driver`, `system`, and `fhs-fallback` evaluate to `throw`. The program only generates files; installing the result is a separate Nix or NixOS step.

## Prerequisites

- Linux. The flake builds for `x86_64-linux` and `aarch64-linux`.
- [Nix](https://nixos.org/download/) with the `nix-command` and `flakes` experimental features. A stock install leaves them off. Enable them once:

```bash
mkdir -p ~/.config/nix
touch ~/.config/nix/nix.conf
grep -qxF 'experimental-features = nix-command flakes' ~/.config/nix/nix.conf || printf 'experimental-features = nix-command flakes\n' >> ~/.config/nix/nix.conf
```

Without Nix, the unit tests still run with Python 3.11+, `dpkg-deb`, and `readelf` from binutils. `scripts/make-fixtures.sh` also needs `gcc` when it rebuilds the synthetic CLI `.deb`.

## Install, build, run, test

From this checkout:

```bash
nix build .#deb2nix
nix run .#deb2nix -- --help
nix flake check
bash scripts/smoke.sh
```

`nix develop` drops you into a shell with the generator, Python 3, `dpkg`, binutils, `gcc`, and `nix-index`. The same unit tests, outside that Nix build:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Usage

Generate from the committed CLI fixture, build it, and run the binary. `nix build` links the output under the directory you pass to `-o`; it does not put the program on `PATH`.

```bash
nix run .#deb2nix -- ./fixtures/hello-deb2nix_0.1.0_amd64.deb --out /tmp/hello-deb2nix-nix --skip-locate
nix build /tmp/hello-deb2nix-nix -o /tmp/hello-deb2nix-nix/result
/tmp/hello-deb2nix-nix/result/bin/hello-deb2nix
```

That prints `hello from deb2nix fixture`.

Omit `--out` to write `./<pname>-nix` (this fixture lands in `./hello-deb2nix-nix`). Pass an `https` URL as `source` to download the archive and pin it with `fetchurl`. `--src-url URL` records a public URL while reading a local file. Other flags: `--profile`, `--keep-unpack`, `--json`, `--version`. `--profile` accepts `auto` (the default), `cli`, `electron`, `chromium-browser`, `gtk`, `qt`, `driver`, `system`, or `fhs-fallback`. `auto` classifies from file contents.

| Profile | Chosen when the archive contains | Emit |
| --- | --- | --- |
| `cli` | Executables and no GUI or driver markers | `autoPatchelfHook` derivation |
| `electron` | `app.asar`, `app.asar.unpacked`, `resources/app`, or an `electron` dependency | Userland `autoPatchelfHook` + `wrapGAppsHook3` |
| `chromium-browser` | `chrome-sandbox` and no Electron markers | Same userland shape |
| `gtk` / `qt` | GTK or Qt libraries in `DT_NEEDED` | Userland `autoPatchelfHook` plus a GApps or Qt wrap |
| `driver` / `system` | `.ko`, `dkms.conf`, or `lib/modules` | Stub `throw` and `LIMITATIONS.md` |
| `fhs-fallback` | No other match | Stub `throw` |

After a userland generate, the CLI prints install and remove lines: `nix profile add <out>/result`, `nix profile list`, `hash -r`, `nix profile remove <pname>`, and `nix-collect-garbage`. Those lines also restart Hyprland's `hyprlauncher` when that process is already running. On NixOS, add `(pkgs.callPackage ./<out>/package.nix { })` to `environment.systemPackages` and run `sudo nixos-rebuild switch`. Generated flakes leave `allowUnfree` to the parent NixOS or user nixpkgs config (`~/.config/nixpkgs/config.nix` applies to `default.nix`). For an unfree flake build: `NIXPKGS_ALLOW_UNFREE=1 nix build --impure`.

`--skip-locate` uses the builtin `.so` map only. With `nix-locate` on `PATH` (it is in the dev shell via `nix-index`), the generator also queries that database.

## Layout

- `src/deb2nix/` — generator
- `tests/` — unit tests
- `fixtures/` — synthetic `.deb`s; vendor blobs stay gitignored (`fixtures/MATRIX.md`)
- `scripts/smoke.sh` — generate, build, and run the CLI fixture
- `scripts/make-fixtures.sh` — rebuild the synthetic `.deb`s
- `scripts/generate-vendor-examples.sh` — regenerate `examples/` (needs `fixtures/vendor/*.deb`)
- `examples/` — hash-pinned generated trees
- `docs/PRIOR-ART.md`, `docs/DISPLAYLINK.md`, `STATUS.md`

## License

[MIT](LICENSE). A known Debian `License:` field is copied into `meta.license` as `lib.licenses.*`. Debian `non-free` maps to `lib.licenses.unfree`. A missing or placeholder license (`unknown`, `n/a`) on a free section maps to `lib.licenses.free`.
