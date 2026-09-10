# code — userland notes

Profile: `electron`. Unfree EULA accepted 2026-09-10 (Tim).

`package.nix` is a **userland** unpack + `autoPatchelfHook` + GApps wrap. It is
hash-pinned and uses `allowUnfreePredicate` for this pname only.

Still out of scope for this generator:

- GUI smoke (needs NixOS + Hyprland). `nix build` here is not a display test.
- `--no-sandbox` (app2nix default; we will not).
- `vscode-fhs` / silent `buildFHSEnv`.
- `chrome-sandbox` setuid. Mode 0755; relies on user namespaces.
- Publishing to public nixpkgs.

Hash: `sha256-/U3/csRFmNOsuIW0SCVvXYLPU/WVONl/x9PI2NnVdNM=`
