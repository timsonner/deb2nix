# Fixture matrix

Tim approval **2026-09-10**: all unfree / EULAs accepted (Chrome, Edge, VS Code, Grok Bot, DisplayLink). Vendor `.deb`s were prefetched and SRI-pinned. Blobs live in `fixtures/vendor/` and are **gitignored**. Pins: [`vendor/LOCK.json`](vendor/LOCK.json). Generated Nix: [`examples/`](../examples/).

Still **do not** load DKMS/kernel modules, modify Tim’s machines, or publish to public nixpkgs.

## In-tree synthetic (always committed)

| Fixture | Path | License | Profile expected | Notes |
| --- | --- | --- | --- | --- |
| Tiny CLI negative control | `fixtures/hello-deb2nix_0.1.0_amd64.deb` | MIT | `cli` | Real ELF, `libc` only. Used for `nix build` smoke. Rebuild: `scripts/make-fixtures.sh`. |
| Electron markers | `fixtures/fake-electron-app_0.0.1_amd64.deb` | MIT (synthetic) | `electron` | Empty `app.asar` (+ sandbox/paks). **Not** Electron software. Userland emit (autoPatchelf). |
| Chromium-browser markers | `fixtures/fake-chromium-browser_0.0.1_amd64.deb` | MIT (synthetic) | `chromium-browser` | `chrome-sandbox` + paks, **no** `app.asar`. Distinguishes Chrome/Edge from VS Code/Grok Bot. |
| DisplayLink markers | `fixtures/fake-displaylink_0.0.1_amd64.deb` | MIT (synthetic) | `driver` | Dummy `dkms.conf` + `evdi.ko` **filename**. Not a real module. **Do not insmod.** Emit is `throw`. |
| `/opt` CLI | `fixtures/fake-opt-cli_0.0.1_amd64.deb` | MIT (synthetic) | `cli` | `usr/bin` wrapper hardcodes `/opt/...`. Tests symlink/script retarget, not ELF rewrite. |
| Chrome name token | `fixtures/fake-chrome-gnome-shell_0.0.1_amd64.deb` | MIT (synthetic) | `cli` | Package name contains `chrome`; must **not** become `chromium-browser`. |

SRI hashes from this tree (rebuild with `scripts/make-fixtures.sh`; hello may drift if `gcc` changes):

| File | Size | SRI |
| --- | --- | --- |
| `hello-deb2nix_0.1.0_amd64.deb` | 2190 | `sha256-BGlqYE0iZumG4kjdGE99SPm+ymbZGPPc6vMDVxAK8/g=` |
| `fake-electron-app_0.0.1_amd64.deb` | 862 | `sha256-iqjctiCPdqN+NeBE9WTQN3C9OkjklvLbU0GkTGdgwww=` |
| `fake-chromium-browser_0.0.1_amd64.deb` | 816 | `sha256-F9HEVr1KAFIepvRAB91tsDKBG0OZ3ZGQ4oWwAdECZUU=` |
| `fake-displaylink_0.0.1_amd64.deb` | 812 | `sha256-z+FJg6Ud/G+4iRXfccrVkmFSNOHnE4TTef5D6/ySZaw=` |

## Vendor GUI / browser (prefetched 2026-09-10)

Regenerate Nix with `bash scripts/generate-vendor-examples.sh` (requires the gitignored blobs).

### Grok Bot (Electron desktop agent)

- Landing: <https://cursor.com/download/bot>
- **0.47.0** pin:
  `https://downloads.cursor.com/grokbot/stable/c1e7d7a46549956d25f53e9c0b9f59666e03aa3a/linux/x64/grok-bot_0.47.0_amd64.deb`
  - bytes: 103367560
  - SRI: `sha256-EcoPUaU1uXr1GjUq35wPns0uGwQwpprpRRtoinoGWAg=`
- Known **0.44.0** pin (do not treat as 0.47.0): `sha256-3e0YstPUSxwy1rn2NEbSsnvKaLPeeiqgKM55VulpQWQ=`
- License: proprietary (SpaceXAI / Cursor). **unfree**.
- Expected profile: **`electron`** (`app.asar`, bundled chrome, `chrome-sandbox`). Not `chromium-browser`.
- Prior art: [jordangarrison/grok-bot-flake](https://github.com/jordangarrison/grok-bot-flake), [nixpkgs#558990](https://github.com/NixOS/nixpkgs/pull/558990).
- Emit: userland flake in `examples/grok-bot/`. GUI smoke later (NixOS+Hyprland). Do not publish to nixpkgs from this tool.

### Visual Studio Code (Electron IDE)

- Rolling: <https://update.code.visualstudio.com/latest/linux-deb-x64/stable>
- Fetched (redirect target 2026-09-10):
  `https://vscode.download.prss.microsoft.com/dbazure/download/stable/645f29cc3176500b4b5762ba887cf2a7f0ffdf2c/code_1.137.0-1788902055_amd64.deb`
  - bytes: 237130638
  - SRI: `sha256-/U3/csRFmNOsuIW0SCVvXYLPU/WVONl/x9PI2NnVdNM=`
- Apt repo: `https://packages.microsoft.com/repos/code`
- License: proprietary (Microsoft). **unfree**.
- Expected profile: **`electron`**. Not `chromium-browser`.
- Contrast: nixpkgs `vscode` vs `vscode-fhs`. deb2nix will not silently pick FHS.
- Emit: `examples/vscode/`.

### Google Chrome (Chromium-family)

- <https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb>
  - bytes: 141931876
  - SRI: `sha256-m7ROMwMcLyhXzza0NDBRoS+TBY5LeB48djE9+H9sjTI=`
- License: proprietary (Google). **unfree**.
- Expected profile: **`chromium-browser`**. Distinct from `electron`.
- **Rolling URL** — re-hash when refetching.
- Emit: `examples/google-chrome-stable/`.

### Microsoft Edge (Chromium-family)

- `https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/microsoft-edge-stable_152.0.4191.66-1_amd64.deb`
  - bytes: 195767486
  - SRI: `sha256-GGwZ+dYHnRdO+7TvMxzMHhHRObb3qOo7DbdfmxfiXw0=`
- License: proprietary (Microsoft). **unfree**.
- Expected profile: **`chromium-browser`**.
- Emit: `examples/microsoft-edge-stable/`.

## DisplayLink — Phase 3 parked (stub + report; **no kernel load**)

EULA accepted 2026-09-10. Full report: [`docs/DISPLAYLINK.md`](../docs/DISPLAYLINK.md).

deb2nix **must not** load kernel modules, run DKMS, or install DisplayLink/EVDI. The PPA `.deb` is userspace `DisplayLinkManager` plus firmware; EVDI is a **Depends** (`evdi-dkms | evdi`), not shipped in this package.

| Artifact | URL | SRI |
| --- | --- | --- |
| Ubuntu driver page | <https://www.synaptics.com/products/displaylink-graphics/downloads/ubuntu> | — |
| Synaptics APT keyring `.deb` | <https://www.synaptics.com/sites/default/files/Ubuntu/pool/stable/main/all/synaptics-repository-keyring.deb> | `sha256-+DMAkohI8vdgX/hDhGcmcBnHzFGB7Iueq8fx4Fy/rL4=` |
| PPA noble amd64 | `https://ppa.launchpadcontent.net/synaptics-displaylink/displaylink-driver/ubuntu/pool/main/d/displaylink-driver/displaylink-driver_6.3.0-0ubuntu1~ppa3~noble1_amd64.deb` | `sha256-zHVC+5aQb5cPwTVO2DwKhRVH96RoCa2zNlmKDjGxWKM=` |
| Launchpad PPA | <https://launchpad.net/~synaptics-displaylink/+archive/ubuntu/displaylink-driver> | — |

Expected classifier result: `driver` / `system`. Emit is a `throw` + `nixos-module.stub.nix` + `LIMITATIONS.md`. That throw is success for Phase 1/3 prep.

nixpkgs pattern for a **human** on NixOS: `requireFile` / unfree + `evdi` + `hardware.video.displaylink`. Not activated by this generator.

## Hash policy

```bash
nix run .#deb2nix -- "$URL" --out ./generated
# or, after prefetch:
nix run .#deb2nix -- ./fixtures/vendor/foo.deb --src-url "$URL" --out ./examples/foo --skip-locate
# report.json contains source.hash (SRI). That is the pin.
```

`google-chrome-stable_current_amd64.deb` and Code's `latest` redirect **change**. Always re-hash.
