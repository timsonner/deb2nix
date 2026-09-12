# grok-bot — userland notes

Profile: `electron`.

`package.nix` is a userland unpack + `autoPatchelfHook` + GApps wrap.
Hash-pinned.

Generate / `nix build` does **not** put `grok-bot` on `PATH`.
Ask how to install:

```bash
nix build .
./result/bin/grok-bot
nix profile add ./result          # user profile
# or NixOS: pkgs.callPackage ./package.nix {} in environment.systemPackages
```

Out of scope for this generator:

- GUI/display smoke (`nix build` is not a display test; Electron `--version` may open a window).
- Disabling the Chromium sandbox.
- Silent `buildFHSEnv`.
- setuid on `*-sandbox` (mode 0755; user namespaces).
- Qt5+Qt6 in the same `buildInputs` (setup-hook conflict).
- Publishing to public nixpkgs.

Hash: `sha256-EcoPUaU1uXr1GjUq35wPns0uGwQwpprpRRtoinoGWAg=`
