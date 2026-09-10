# Fixture matrix

Phase 1 cloud VM: **document public URLs**. Download **only** in-tree synthetic fixtures (no GUI license, no kernel). Hashes for vendor `.deb`s are **not** invented — pin them with `deb2nix` / `nix hash file` when you actually fetch on a machine that is allowed to.

Sizes below are `Content-Length` from HTTP HEAD on 2026-09-10, not SRI hashes.

## In-tree (downloaded / built here)

| Fixture | Path | License | Profile expected | Notes |
| --- | --- | --- | --- | --- |
| Tiny CLI negative control | `fixtures/hello-deb2nix_0.1.0_amd64.deb` | MIT | `cli` | Real ELF, `libc` only. Used for `nix build` smoke. Rebuild: `scripts/make-fixtures.sh`. |
| Electron markers | `fixtures/fake-electron-app_0.0.1_amd64.deb` | MIT (synthetic) | `electron` | Empty `app.asar`, `chrome-sandbox`, `icudtl.dat`, `resources.pak`. **Not** Electron software. |
| DisplayLink markers | `fixtures/fake-displaylink_0.0.1_amd64.deb` | MIT (synthetic) | `driver` | Dummy `dkms.conf` + `evdi.ko` **filename**. Not a real module. **Do not insmod.** |

SRI hashes from this tree (rebuild with `scripts/make-fixtures.sh`; hello may drift if `gcc` changes):

| File | Size | SRI |
| --- | --- | --- |
| `hello-deb2nix_0.1.0_amd64.deb` | 2194 | `sha256-9XxoQzCfVFw/t9J09PZdPh9wfEg1xcrTj+T0GqlvQ9M=` |
| `fake-electron-app_0.0.1_amd64.deb` | 860 | `sha256-fyKUg0oUMRfsF72aC7QNrCmAVs8ilm9w/o3BnEMiEHg=` |
| `fake-displaylink_0.0.1_amd64.deb` | 812 | `sha256-AJ6L+7IBfPaTXTNWphUtDHX1mSv+t4At2pAgL3W2nro=` |

## Vendor GUI / browser (document only — not fetched this run)

### Grok Bot (Electron desktop agent)

- Landing: <https://cursor.com/download/bot>
- Conventional Linux URL (build id + version from upstream feed; Linux feed itself may 204):
  `https://downloads.cursor.com/grokbot/stable/<buildId>/linux/x64/Grok_Bot_<version>.deb`
- License: proprietary (SpaceXAI / Cursor). Treat as **unfree**.
- Expected profile: `electron` (payload: `app.asar`, bundled chrome, `chrome-sandbox`).
- Prior art: [jordangarrison/grok-bot-flake](https://github.com/jordangarrison/grok-bot-flake), [nixpkgs#558990](https://github.com/NixOS/nixpkgs/pull/558990).
- Phase 2: generate private flake, `nix build`, GUI smoke on NixOS+Hyprland. Do not publish to nixpkgs from this tool.

### Visual Studio Code (Electron IDE)

- Rolling: <https://update.code.visualstudio.com/latest/linux-deb-x64/stable>
- HEAD 2026-09-10 redirected to:
  `https://vscode.download.prss.microsoft.com/dbazure/download/stable/645f29cc3176500b4b5762ba887cf2a7f0ffdf2c/code_1.137.0-1788902055_amd64.deb`
  (`Content-Length: 237130638`)
- Apt repo: `https://packages.microsoft.com/repos/code`
- License: proprietary (Microsoft). **unfree**.
- Expected profile: `electron` (`code` package name + `app.asar`).
- Contrast: nixpkgs `vscode` vs `vscode-fhs`. deb2nix will not silently pick FHS.

### Google Chrome (Chromium-family)

- <https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb>
  (`Content-Length: 141931876`, `application/x-debian-package`)
- License: proprietary (Google). **unfree**.
- Expected profile: `electron` / subtype `chromium-browser` (`chrome-sandbox`, pak/icudtl, name `google-chrome-stable`).

### Microsoft Edge (Chromium-family)

- Pool: <https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/>
- Example current amd64 (listing 2026-09-10):
  `https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/microsoft-edge-stable_152.0.4191.66-1_amd64.deb`
- License: proprietary (Microsoft). **unfree**.
- Expected profile: `electron` / subtype `chromium-browser`.

## DisplayLink — document only, **no install**

deb2nix **must not** load kernel modules, run DKMS, or install DisplayLink/EVDI.

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
