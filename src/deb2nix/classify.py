"""Profile classifier. Never defaults to Electron."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from deb2nix.control import Control
from deb2nix.elf import ElfInfo
from deb2nix.inventory import Inventory

PROFILES = (
    "cli",
    "electron",
    "gtk",
    "qt",
    "driver",
    "system",
    "fhs-fallback",
)

ELECTRON_FILENAMES = {
    "app.asar",
    "chrome-sandbox",
    "chrome_crashpad_handler",
    "chrome_crashpad_handler.exe",
    "v8_context_snapshot.bin",
    "snapshot_blob.bin",
    "natives_blob.bin",
    "icudtl.dat",
    "resources.pak",
    "chrome_100_percent.pak",
    "chrome_200_percent.pak",
    "vk_swiftshader_icd.json",
    "libvk_swiftshader.so",
    "licenses.chromium.html",
}

ELECTRON_PACKAGE_NAMES = {
    "code",
    "code-insiders",
    "code-exploration",
    "google-chrome-stable",
    "google-chrome-beta",
    "google-chrome-unstable",
    "chromium-browser",
    "microsoft-edge-stable",
    "microsoft-edge-beta",
    "microsoft-edge-dev",
    "brave-browser",
    "discord",
    "slack-desktop",
    "signal-desktop",
    "grok-bot",
    "sand",
    "cursor",
    "element-desktop",
    "obsidian",
    "1password",
}

# Phrases that may appear in Description. Do NOT include bare "electron":
# a CLI package that says "no Electron" must stay cli.
ELECTRON_DESC_PHRASES = (
    "visual studio code",
    "microsoft edge",
    "google chrome",
    "grok bot",
    "chromium browser",
)

ELECTRON_PKG_TOKENS = (
    "electron",
    "chrome",
    "chromium",
    "vscode",
    "grok-bot",
)

GTK_LIBS = ("libgtk-3.so", "libgtk-4.so", "libgdk-3.so", "libwebkit2gtk")
QT_LIBS = ("libqt5", "libqt6", "libqtcore.so")
DRIVER_NAMES = (
    "displaylink",
    "evdi",
    "nvidia",
    "dkms",
    "broadcom",
    "realtek",
    "wifi-firmware",
)


@dataclass
class Classification:
    profile: str
    confidence: str
    reasons: list[str] = field(default_factory=list)
    evidence: dict[str, list[str]] = field(default_factory=dict)
    subtype: str | None = None
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "profile": self.profile,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "evidence": self.evidence,
            "subtype": self.subtype,
            "warnings": self.warnings,
        }


def classify(
    control: Control,
    inventory: Inventory,
    elfs: list[ElfInfo],
    unmapped: list[str] | None = None,
    override: str | None = None,
) -> Classification:
    if override:
        if override not in PROFILES:
            raise ValueError(f"unknown profile {override!r}; choose from {', '.join(PROFILES)}")
        auto = _classify(control, inventory, elfs, unmapped or [])
        auto.warnings.append(f"profile overridden from {auto.profile} to {override}")
        auto.profile = override
        auto.confidence = "overridden"
        return auto
    return _classify(control, inventory, elfs, unmapped or [])


def _classify(
    control: Control,
    inventory: Inventory,
    elfs: list[ElfInfo],
    unmapped: list[str],
) -> Classification:
    needed = [lib.lower() for info in elfs for lib in info.needed]
    pkg = control.package.lower()
    desc = (control.description + " " + control.provides).lower()
    depends = control.depends.lower()

    driver_hits = _driver_hits(control, inventory, pkg, desc)
    if driver_hits:
        return Classification(
            profile="driver" if "dkms" in " ".join(driver_hits).lower() or inventory.kernel_modules else "system",
            confidence="high",
            reasons=driver_hits,
            evidence={"kernel_modules": inventory.kernel_modules[:20], "hints": driver_hits},
            subtype="displaylink" if any("displaylink" in h.lower() or "evdi" in h.lower() for h in driver_hits) else None,
            warnings=[
                "deb2nix will not emit an expression that loads kernel modules or installs DKMS (including DisplayLink/EVDI).",
            ],
        )

    electron_files = sorted(
        p for p in inventory.files if PathName(p) in ELECTRON_FILENAMES or p.endswith("app.asar")
    )
    electron_dirs = [d for d in inventory.dirs if d.endswith("app.asar.unpacked")]
    name_hit = _electron_name_hit(pkg, desc)
    depends_electron = bool(re.search(r"(^|[,\s])electron([0-9]|-|$)", depends))
    chromium_pack = (
        inventory.has_name("resources.pak") and inventory.has_name("icudtl.dat")
    ) or inventory.has_name("chrome-sandbox")

    electron_reasons: list[str] = []
    if electron_files:
        electron_reasons.append(
            "electron/chromium payload files: " + ", ".join(PathName(p) for p in electron_files[:8])
        )
    if electron_dirs:
        electron_reasons.append("found app.asar.unpacked")
    if name_hit:
        electron_reasons.append(f"package name/description matches electron/chromium family ({control.package})")
    if depends_electron:
        electron_reasons.append("Depends mentions electron")
    if chromium_pack and not electron_files:
        electron_reasons.append("chromium resources.pak / chrome-sandbox layout")

    if electron_reasons:
        subtype = "electron"
        if any(token in pkg for token in ("chrome", "edge", "chromium", "brave")):
            subtype = "chromium-browser"
        return Classification(
            profile="electron",
            confidence="high" if electron_files or chromium_pack else "medium",
            reasons=electron_reasons,
            evidence={"files": electron_files[:20], "package": [control.package]},
            subtype=subtype,
        )

    gtk_hits = sorted({lib for lib in needed if any(lib.startswith(g) for g in GTK_LIBS)})
    qt_hits = sorted({lib for lib in needed if any(q in lib for q in QT_LIBS)})
    if qt_hits and len(qt_hits) >= len(gtk_hits):
        return Classification(
            profile="qt",
            confidence="high",
            reasons=[f"NEEDED Qt libraries: {', '.join(qt_hits[:8])}"],
            evidence={"qt_libs": qt_hits},
        )
    if gtk_hits:
        return Classification(
            profile="gtk",
            confidence="high",
            reasons=[f"NEEDED GTK libraries: {', '.join(gtk_hits[:8])}"],
            evidence={"gtk_libs": gtk_hits},
        )

    has_bin = bool(inventory.binaries) or any(
        p.startswith("usr/bin/") or p.startswith("bin/") for p in inventory.files
    )
    if has_bin and len(unmapped) <= 8:
        return Classification(
            profile="cli",
            confidence="high" if elfs else "medium",
            reasons=[
                "no electron/chromium/GTK/Qt/driver markers",
                f"{len(elfs)} ELF object(s), {len(inventory.binaries)} executable path(s)",
            ],
            evidence={"binaries": inventory.binaries[:20]},
        )

    reasons = ["layout does not match cli/electron/gtk/qt/driver heuristics"]
    if unmapped:
        reasons.append(f"{len(unmapped)} unmapped libraries; refusing silent buildFHSEnv")
    return Classification(
        profile="fhs-fallback",
        confidence="low",
        reasons=reasons,
        evidence={"unmapped": unmapped[:20]},
        warnings=[
            "Honest failure: deb2nix will not silently wrap this in buildFHSEnv. Inspect report.json.",
        ],
    )


def _electron_name_hit(pkg: str, desc: str) -> bool:
    if pkg in ELECTRON_PACKAGE_NAMES:
        return True
    for tok in ELECTRON_PKG_TOKENS:
        if re.search(rf"(^|[-_+]){re.escape(tok)}([-_+]|$)", pkg):
            return True
    return any(phrase in desc for phrase in ELECTRON_DESC_PHRASES)


def _driver_hits(control: Control, inventory: Inventory, pkg: str, desc: str) -> list[str]:
    hits: list[str] = []
    if inventory.kernel_modules:
        hits.append(f"{len(inventory.kernel_modules)} kernel module(s) (.ko)")
    if inventory.has_name("dkms.conf") or inventory.has_path_part("dkms"):
        hits.append("DKMS metadata present")
    if inventory.has_path_part("lib/modules"):
        hits.append("ships files under lib/modules")
    for token in DRIVER_NAMES:
        if token in pkg or token in desc or token in control.package.lower():
            hits.append(f"name/description matches driver token {token!r}")
    if control.section.lower() in {"kernel", "kernel/dkms", "misc"} and (
        "module" in desc or "driver" in desc
    ):
        hits.append(f"section {control.section} looks like a kernel driver")
    return hits


def PathName(path: str) -> str:
    return path.rsplit("/", 1)[-1].lower()
