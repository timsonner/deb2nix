"""Human-facing install/remove sequences. CLI, NOTES, and tests share this."""

from __future__ import annotations

from pathlib import Path

# Hyprlauncher is a singleton: a second `hyprlauncher -d` just pokes the
# existing daemon over the socket and does not recache. Wait until the old
# process (and socket) are gone, then start a new daemon. No-op if none.
LAUNCHER_REFRESH = (
    'pgrep -x hyprlauncher >/dev/null && { pkill -x hyprlauncher; '
    'i=0; while pgrep -x hyprlauncher >/dev/null && [ "$i" -lt 30 ]; '
    'do sleep 0.1; i=$((i+1)); done; '
    'pkill -KILL -x hyprlauncher 2>/dev/null || true; '
    'rm -f "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/.hyprlauncher.sock"; '
    'hyprlauncher -d; } || true'
)


def result_link(out_dir: Path | str) -> str:
    return f"{out_dir}/result"


def refresh_launcher_lines() -> list[str]:
    return [LAUNCHER_REFRESH]


def install_lines(out_dir: Path | str, pname: str) -> list[str]:
    """Cwd-safe: `nix build DIR -o DIR/result` then add that path, not `./result`."""
    out = str(out_dir)
    res = result_link(out)
    return [
        f"nix build {out} -o {res}",
        f"{res}/bin/{pname}",
        f"nix profile add {res}",
        *refresh_launcher_lines(),
        "hash -r",
        "nix profile list",
    ]


def remove_lines(pname: str) -> list[str]:
    return [
        f"nix profile remove {pname}",
        *refresh_launcher_lines(),
        "nix-collect-garbage",
    ]
