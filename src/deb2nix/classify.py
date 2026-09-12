"""Profile classifier from .deb contents only. No product-name allowlists."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from deb2nix.control import Control
from deb2nix.elf import ElfInfo
from deb2nix.inventory import Inventory

PROFILES = (
    "cli",
    "electron",
    "chromium-browser",
    "gtk",
    "qt",
    "driver",
    "system",
    "fhs-fallback",
)

# Filename conventions inside Chromium/Electron trees — not product names.
ELECTRON_FILENAMES = {
    "app.asar",
    "chrome_crashpad_handler",
    "chrome_crashpad_handler.exe",
    "v8_context_snapshot.bin",
    "snapshot_blob.bin",
    "natives_blob.bin",
    "vk_swiftshader_icd.json",
    "libvk_swiftshader.so",
    "licenses.chromium.html",
}

CHROMIUM_PAYLOAD_FILES = {
    "chrome-sandbox",
    "icudtl.dat",
    "resources.pak",
    "chrome_100_percent.pak",
    "chrome_200_percent.pak",
}

GTK_LIBS = ("libgtk-3.so", "libgtk-4.so", "libgdk-3.so", "libwebkit2gtk")
QT_LIBS = ("libqt5", "libqt6", "libqtcore.so")


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
    depends = control.depends.lower()

    driver_hits = _driver_hits(inventory)
    if driver_hits:
        return Classification(
            profile="driver" if "dkms" in " ".join(driver_hits).lower() or inventory.kernel_modules else "system",
            confidence="high",
            reasons=driver_hits,
            evidence={"kernel_modules": inventory.kernel_modules[:20], "hints": driver_hits},
            warnings=[
                "deb2nix will not emit an expression that loads kernel modules or installs DKMS.",
            ],
        )

    asar_files = sorted(
        p for p in inventory.files if PathName(p) == "app.asar" or p.endswith("app.asar")
    )
    electron_dirs = [d for d in inventory.dirs if d.endswith("app.asar.unpacked")]
    electron_payload = sorted(
        p for p in inventory.files if PathName(p) in ELECTRON_FILENAMES
    )
    chromium_payload = sorted(
        p for p in inventory.files if PathName(p) in CHROMIUM_PAYLOAD_FILES
    )
    sandbox_files = [p for p in inventory.files if PathName(p) == "chrome-sandbox"]
    depends_electron = bool(re.search(r"(^|[,\s])electron([0-9]|-|$)", depends))

    unpacked_electron = inventory.has_path_part("resources/app") and bool(
        electron_payload or sandbox_files
    )

    if asar_files or electron_dirs or depends_electron or unpacked_electron:
        reasons: list[str] = []
        if asar_files:
            reasons.append("electron payload: app.asar")
        if electron_dirs:
            reasons.append("found app.asar.unpacked")
        if unpacked_electron and not asar_files:
            reasons.append("unpacked electron tree: resources/app")
        if electron_payload:
            reasons.append(
                "electron/chromium helper files: "
                + ", ".join(PathName(p) for p in electron_payload[:8])
            )
        if depends_electron:
            reasons.append("Depends mentions electron")
        return Classification(
            profile="electron",
            confidence="high" if asar_files or electron_dirs or unpacked_electron else "medium",
            reasons=reasons or ["Depends mentions electron"],
            evidence={"files": (asar_files + electron_payload)[:20]},
            subtype="electron",
        )

    if sandbox_files:
        reasons = [
            "chromium payload files (no app.asar): "
            + ", ".join(PathName(p) for p in chromium_payload[:8])
        ]
        return Classification(
            profile="chromium-browser",
            confidence="high",
            reasons=reasons,
            evidence={"files": chromium_payload[:20]},
            subtype="chromium-browser",
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
        p.startswith("usr/bin/") or p.startswith("bin/") or p.startswith("opt/")
        for p in inventory.files
    )
    if has_bin:
        reasons = [
            "no electron/chromium/GTK/Qt/driver markers",
            f"{len(elfs)} ELF object(s), {len(inventory.binaries)} executable path(s)",
        ]
        if unmapped:
            reasons.append(
                f"{len(unmapped)} unmapped libraries listed in autoPatchelfIgnoreMissingDeps"
            )
        return Classification(
            profile="cli",
            confidence="high" if elfs else "medium",
            reasons=reasons,
            evidence={"binaries": inventory.binaries[:20], "unmapped": unmapped[:20]},
        )

    reasons = ["layout does not match cli/electron/chromium-browser/gtk/qt/driver heuristics"]
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


def _driver_hits(inventory: Inventory) -> list[str]:
    """Driver only if this .deb actually ships kernel/DKMS payload."""
    hits: list[str] = []
    if inventory.kernel_modules:
        hits.append(f"{len(inventory.kernel_modules)} kernel module(s) (.ko)")
    if inventory.has_name("dkms.conf") or inventory.has_path_part("dkms"):
        hits.append("DKMS metadata present")
    if inventory.has_path_part("lib/modules"):
        hits.append("ships files under lib/modules")
    return hits


def PathName(path: str) -> str:
    return path.rsplit("/", 1)[-1].lower()
