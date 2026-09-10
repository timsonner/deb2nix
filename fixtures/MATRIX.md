# Fixture matrix

Phase 1 cloud VM: **document public URLs**. Download **only** in-tree synthetic fixtures (no GUI license, no kernel). Hashes for vendor `.deb`s are **not** invented — pin them with `deb2nix` / `nix hash file` when you actually fetch on a machine that is allowed to.

Sizes below are `Content-Length` from HTTP HEAD on 2026-09-10, not SRI hashes.

## In-tree (downloaded / built here)

| Fixture | Path | License | Profile expected | Notes |
| --- | --- | --- | --- | --- |
| Tiny CLI negative control | `fixtures/hello-deb2nix_0.1.0_amd64.deb` | MIT | `cli` | Real ELF, `libc` only. Used for `nix build` smoke. Rebuild: `scripts/make-fixtures.sh`. |
| Electron markers | `fixtures/fake-electron-app_0.0.1_amd64.deb` | MIT (synthetic) | `electron` | Empty `app.asar` (+ sandbox/paks). **Not** Electron software. |
| Chromium-browser markers | `fixtures/fake-chromium-browser_0.0.1_amd64.deb` | MIT (synthetic) | `chromium-browser` | `chrome-sandbox` + paks, **no** `app.asar`. Distinguishes Chrome/Edge from VS Code/Grok Bot. |
| DisplayLink markers | `fixtures/fake-displaylink_0.0.1_amd64.deb` | MIT (synthetic) | `driver` | Dummy `dkms.conf` + `evdi.ko` **filename**. Not a real module. **Do not insmod.** |

SRI hashes from this tree (rebuild with `scripts/make-fixtures.sh`; hello may drift if `gcc` changes):

| File | Size | SRI |
| --- | --- | --- |
| `hello-deb2nix_0.1.0_amd64.deb` | 2190 | `sha256-BGlqYE0iZumG4kjdGE99SPm+ymbZGPPc6vMDVxAK8/g=` |
| `fake-electron-app_0.0.1_amd64.deb` | 862 | `sha256-iqjctiCPdqN+NeBE9WTQN3C9OkjklvLbU0GkTGdgwww=` |
| `fake-chromium-browser_0.0.1_amd64.deb` | 816 | `sha256-F9HEVr1KAFIepvRAB91tsDKBG0OZ3ZGQ4oWwAdECZUU=` |
| `fake-displaylink_0.0.1_amd64.deb` | 812 | `sha256-z+FJg6Ud/G+4iRXfccrVkmFSNOHnE4TTef5D6/ySZaw=` |

## Vendor GUI / browser (document only — not fetched this run)

### Grok Bot (Electron desktop agent) — Phase 2, document now

- Landing: <https://cursor.com/download/bot>
- **0.47.0** (prefetch hash in Phase 2 — **UNKNOWN** here, do not fetch on this VM):
  `https://downloads.cursor.com/grokbot/stable/c1e7d7a46549956d25f53e9c0b9f59666e03aa3a/linux/x64/grok-bot_0.47.0_amd64.deb`
- Known **0.44.0** pin (do not treat as 0.47.0): `sha256-3e0YstPUSxwy1rn2NEbSsnvKaLPeeiqgKM55VulpQWQ=`
- Older URL convention also seen: `https://downloads.cursor.com/grokbot/stable/<buildId>/linux/x64/Grok_Bot_<version>.deb`
- License: proprietary (SpaceXAI / Cursor). **unfree**.
- Expected profile: **`electron`** (`app.asar`, bundled chrome, `chrome-sandbox`). Not `chromium-browser`.
- Prior art: [jordangarrison/grok-bot-flake](https://github.com/jordangarrison/grok-bot-flake), [nixpkgs#558990](https://github.com/NixOS/nixpkgs/pull/558990).
- Phase 2: generate private flake, `nix build`, GUI smoke on NixOS+Hyprland. Do not publish to nixpkgs from this tool.

### Visual Studio Code (Electron IDE)

- Rolling: <https://update.code.visualstudio.com/latest/linux-deb-x64/stable>
- HEAD 2026-09-10 redirected to:
  `https://vscode.download.prss.microsoft.com/dbazure/download/stable/645f29cc3176500b4b5762ba887cf2a7f0ffdf2c/code_1.137.0-1788902055_amd64.deb`
  (`Content-Length: 237130638`)
- Apt repo: `https://packages.microsoft.com/repos/code`
- License: proprietary (Microsoft). **unfree**.
- Expected profile: **`electron`** (`code` package name + `app.asar`). Not `chromium-browser`.
- Contrast: nixpkgs `vscode` vs `vscode-fhs`. deb2nix will not silently pick FHS.

### Google Chrome (Chromium-family)

- <https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb>
  (`Content-Length: 141931876`, `application/x-debian-package`)
- License: proprietary (Google). **unfree**.
- Expected profile: **`chromium-browser`** (`chrome-sandbox`, pak/icudtl, name `google-chrome-stable`). Distinct from `electron`.

### Microsoft Edge (Chromium-family)

- Pool: <https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/>
- Example current amd64 (listing 2026-09-10):
  `https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/microsoft-edge-stable_152.0.4191.66-1_amd64.deb`
- License: proprietary (Microsoft). **unfree**.
- Expected profile: **`chromium-browser`**.

## DisplayLink — Phase 3 parked (document only, **no install**)

deb2nix **must not** load kernel modules, run DKMS, or install DisplayLink/EVDI.

nixpkgs pattern to follow later (not emit in Phase 1): `requireFile` + `unfree` + `evdi` + NixOS `hardware.video.displaylink`. Synaptics EULA applies; do not download the vendor `.deb` on this VM.

| Artifact | URL | Notes |
| --- | --- | --- |
| Ubuntu driver page | <https://www.synaptics.com/products/displaylink-graphics/downloads/ubuntu> | APT repo + standalone installer. |
| Synaptics APT keyring `.deb` | <https://www.synaptics.com/sites/default/files/Ubuntu/pool/stable/main/all/synaptics-repository-keyring.deb> | HEAD `Content-Length: 2842`. Keyring only; still not fetched here. |
| PPA (example noble) | `https://ppa.launchpadcontent.net/synaptics-displaylink/displaylink-driver/ubuntu/pool/main/d/displaylink-driver/displaylink-driver_6.3.0-0ubuntu1~ppa3~noble1_amd64.deb` | HEAD `Content-Length: 7301458`. DKMS/EVDI. **Do not install on this VM.** |
| Launchpad PPA | <https://launchpad.net/~synaptics-displaylink/+archive/ubuntu/displaylink-driver> | `displaylink-driver` 6.3.0. |

Expected classifier result on a real DisplayLink `.deb`: `driver` / `system`. Emit is a `throw` explaining the kernel policy.

## Hash policy

```bash
# when you are allowed to fetch:
nix run .#deb2nix -- "$URL" --out ./generated
# report.json contains source.hash (SRI). That is the pin. Do not trust floating "current" URLs.
```

`google-chrome-stable_current_amd64.deb` and Code's `latest` redirect **change**. Always re-hash.
