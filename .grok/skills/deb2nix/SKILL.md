---
name: deb2nix
description: >
  Work on the deb2nix Debian .deb → Nix generator. Use when converting a .deb,
  classifying profiles, emitting flakes, running smoke, or the user mentions
  deb2nix, autoPatchelfHook, or /deb2nix.
---

# deb2nix

The program is `nix run .#deb2nix`. Humans do not need this skill. Usage, emit, classify, license, and install/remove commands live in `README.md` and the CLI summary — do not restate them.

## Agent-only

- Do not add generator tools to NixOS (`python3`, `dpkg`, `gcc`, `binutils`). Use `nix run` / `nix develop`.
- Do not `insmod`, DKMS, or enable `hardware.video.displaylink` / `evdi` on the host. The generator already throws for driver `.deb`s; do not work around it in nixos-config.
- Do not open a public nixpkgs PR from this tool.
- The CLI never installs or uninstalls. After generate/`nix build`, **ask every time** before `nix profile add`/`remove`, editing nixos-config, `nix-collect-garbage`, or deleting `$HOME` app config. Do not reuse the last choice.
