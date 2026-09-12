# grok-bot — userland notes

Profile: `electron`.

`package.nix` is a userland unpack + `autoPatchelfHook` + GApps wrap.
Hash-pinned.

Generate / `nix build` does **not** put `grok-bot` on `PATH`.
`nix build .` writes `./result` in the **current directory**, so pin the
symlink with `-o` (or `cd` here first):

```bash
nix build . -o ./result
./result/bin/grok-bot
nix profile add ./result
pgrep -x hyprlauncher >/dev/null && { pkill -x hyprlauncher; i=0; while pgrep -x hyprlauncher >/dev/null && [ "$i" -lt 30 ]; do sleep 0.1; i=$((i+1)); done; pkill -KILL -x hyprlauncher 2>/dev/null || true; rm -f "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/.hyprlauncher.sock"; hyprlauncher -d; } || true
hash -r
nix profile list
```

`grok-bot` is a GUI for electron/chromium-browser: it opens a window.
`--help` / `--version` do too. After `nix profile add`, open a **new
terminal** (or `hash -r`) so `PATH` updates. The hyprlauncher line
restarts the daemon if it is running so the new `.desktop` is indexed.

NixOS (then `sudo nixos-rebuild switch`):

```nix
environment.systemPackages = [
  (pkgs.callPackage ./package.nix { })
];
```

Uninstall is the same channel. There is no dpkg database.
`report.json` is a conversion log, not an install manifest.

```bash
nix profile remove grok-bot
nix-collect-garbage
```

NixOS: drop the `callPackage` and rebuild. `$HOME` app config is not
in the Nix profile.

Out of scope for this generator:

- GUI/display smoke (`nix build` is not a display test; Electron `--version` may open a window).
- Disabling the Chromium sandbox.
- Silent `buildFHSEnv`.
- setuid on `*-sandbox` (mode 0755; user namespaces).
- Qt5+Qt6 in the same `buildInputs` (setup-hook conflict).
- Publishing to public nixpkgs.

Hash: `sha256-EcoPUaU1uXr1GjUq35wPns0uGwQwpprpRRtoinoGWAg=`
