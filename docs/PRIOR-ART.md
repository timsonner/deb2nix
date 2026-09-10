# Prior art — why GREENFIELD hybrid

The ops-graph note `/workspace/ops-graph/jobs/deb2nix-generator/prior-art.md` is not in this checkout. This file is the in-repo record of the same decision.

## Approach

**GREENFIELD hybrid:** reimplement unpack + ELF → nix-locate / `libraries.json` ideas in new `deb2nix`. Do **not** vendor [Er1ckR1ck0/app2nix](https://github.com/Er1ckR1ck0/app2nix) emit. Phase 1 is **cli** `default.nix` + `nix build` smoke. Phase 2 is `electron` (Grok Bot / VS Code) **and** `chromium-browser` (Chrome / Edge) userland emit. Phase 3 is DisplayLink parked at a module stub (EULA accepted 2026-09-10; still no kernel load).

## Why not fork app2nix

Checked 2026-09-10 against `https://github.com/Er1ckR1ck0/app2nix`:

| Signal | Result |
| --- | --- |
| GitHub `license` API | `null` |
| `/LICENSE` | HTTP 404 |
| `Cargo.toml` `license` | missing |
| `flake.nix` `meta.license` | `licenses.mit` (claim only) |
| Emit template `templates/deb.in` | GTK/Electron-shaped: `autoPatchelfIgnoreMissingDeps` for Qt, `wrapProgram` `--no-sandbox`, “largest binary” heuristic |
| Stars / activity | ~25★, idle |

That Electron-default single template fights profiled emit. Copying substantial Rust/Nix from a repo with **empty license metadata** is not acceptable. Ideas (unpack, `patchelf --print-needed`, builtin so→pkg map, `nix-locate`) are reimplemented here under MIT.

## Other refs

- **milahu/deb2nix** — translate Debian package *names* with `nix-locate` / apt-file. Not a derivation generator.
- **nix-init** — source/URL (GitHub, crates.io, PyPI). Complementary, not a `.deb` unpacker.
- **jordangarrison/grok-bot-flake** — hand-written Electron `.deb` flake: keep upstream Electron, `autoPatchelfHook`, `wrapGAppsHook3`. Phase 2 `electron` target.
- **nixpkgs google-chrome / microsoft-edge** — hand-written Chromium `.deb` repacks. Phase 2 `chromium-browser` target (not the Electron profile).
- **Signal wiki / signal-desktop-bin** — emit shapes for prebuilt Electron.
- **nixpkgs#558990** — draft grok-bot; private flakes only, no public nixpkgs publish from this tool.

## Taxonomy

Browsers (Chrome / Edge / Brave) are profile **`chromium-browser`**. Generic Electron apps (VS Code, Grok Bot, Discord) are **`electron`**. `app.asar` decides Electron; `chrome-sandbox` without asar decides browser. They share Chromium files; they do not share ABI / updater / Widevine policy.

## Grok Bot (Electron — hash-pinned 2026-09-10)

- `https://downloads.cursor.com/grokbot/stable/c1e7d7a46549956d25f53e9c0b9f59666e03aa3a/linux/x64/grok-bot_0.47.0_amd64.deb`
- **0.47.0** SRI: `sha256-EcoPUaU1uXr1GjUq35wPns0uGwQwpprpRRtoinoGWAg=`
- Known **0.44.0** pin (do not treat as 0.47.0): `sha256-3e0YstPUSxwy1rn2NEbSsnvKaLPeeiqgKM55VulpQWQ=`

## DisplayLink (Phase 3 parked — EULA accepted, no kernel load)

Tim 2026-09-10 accepted the Synaptics EULA. The Launchpad PPA `.deb` is hash-pinned; emit is still a `throw` + NixOS module stub because EVDI/DKMS is required. Full report: [`DISPLAYLINK.md`](DISPLAYLINK.md). Never `insmod` from deb2nix.
