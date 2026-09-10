# DisplayLink — Phase 3 limitations (2026-09-10)

Tim approval 2026-09-10 accepted the Synaptics/DisplayLink EULA. This file is the Phase 1/3 prep report. **Success criterion:** honest stub + this report. A runtime driver is **not** in scope.

deb2nix still must not `insmod`, run DKMS, load `evdi`, enable `hardware.video.displaylink`, or change Tim’s machines.

## What was fetched

Launchpad PPA `displaylink-driver` 6.3.0 for Ubuntu noble, **publicly fetchable** after the EULA/PPA listing:

- URL: `https://ppa.launchpadcontent.net/synaptics-displaylink/displaylink-driver/ubuntu/pool/main/d/displaylink-driver/displaylink-driver_6.3.0-0ubuntu1~ppa3~noble1_amd64.deb`
- Size: 7 301 458 bytes
- SRI: `sha256-zHVC+5aQb5cPwTVO2DwKhRVH96RoCa2zNlmKDjGxWKM=`

Also fetched (APT keyring only — **not** the driver):

- `https://www.synaptics.com/sites/default/files/Ubuntu/pool/stable/main/all/synaptics-repository-keyring.deb`
- SRI: `sha256-+DMAkohI8vdgX/hDhGcmcBnHzFGB7Iueq8fx4Fy/rL4=`

Blobs stay in `fixtures/vendor/` (gitignored). Pins: `fixtures/vendor/LOCK.json`. Generated stub: `examples/displaylink-driver/`.

## What is inside the `.deb` (analysis only)

Inspected with `dpkg-deb -c` / `-I` / `-e`. Maintainer scripts were **read**, not executed. No module was loaded.

| Path | Role |
| --- | --- |
| `usr/lib/displaylink-driver/DisplayLinkManager` | Userspace ELF (x86-64 PIE). `DT_NEEDED`: libuuid, libusb-1.0, libstdc++, libgcc, libc, pthread/dl/rt/m. |
| `usr/lib/displaylink-driver/*.spkg` | Dock/monitor firmware blobs (ella, firefly, navarro, ridge). |
| `usr/lib/systemd/system/displaylink-driver.service` | systemd unit for the userspace manager. |
| `usr/lib/udev/rules.d/99-displaylink.rules` | udev rules. |
| `usr/bin/displaylink-installer`, `DLSupportTool` | Helper scripts. |
| `usr/share/wayland-sessions/weston-displaylink.desktop` | Optional Weston session. |

**There is no `.ko` and no `dkms.conf` in this package.** Ubuntu’s copyright file states the bundled EVDI tarball is **removed** from the PPA repack: EVDI is packaged separately as `evdi-dkms` / `libevdi1`.

Debian `Depends`:

```
libc6, libgcc-s1, libstdc++6, libusb-1.0-0, libuuid1,
evdi-dkms (>= 1.12.0) | evdi (>= 1.12.0),
libevdi1 (>= 1.12.0) | evdi (>= 1.12.0)
```

`postinst` (not run here) would write `/etc/modules-load.d/evdi.conf` and `/etc/modprobe.d/evdi.conf` (`options evdi initial_device_count=…`, `softdep evdi pre: <drm helpers>`) unless a Synaptics `evdi` package is already installed. That is exactly the kernel hook this tool refuses to perform.

License in `usr/share/doc/displaylink-driver/copyright`: **DisplayLink-EULA** (binary-only `DisplayLinkManager`; redistribution of the unmodified binary with the EULA attached is clause 1.4). Unfree.

## Classifier / emit

- Profile: `driver` (name `displaylink-driver`, description mentions EVDI/DKMS).
- `package.nix` **throws**. It will not unpack into a fake “it works” FHS env and will not patchelf `DisplayLinkManager` as if that were a driver.
- `nixos-module.stub.nix` documents `hardware.video.displaylink` **commented out / enable = false**.
- `LIMITATIONS.md` is copied next to the generated tree.

Evaluating the generated package is expected to fail:

```bash
nix eval ./examples/displaylink-driver#packages.x86_64-linux.default
# throw: deb2nix classified 'displaylink-driver' as profile 'driver' ...
```

That throw is the Phase 1/3 deliverable.

## What nixpkgs already has (do not enable from this tool)

- NixOS module `hardware.video.displaylink`
- `evdi` kernel package
- Often `requireFile` + unfree for a vendor blob on versions that are not the PPA `.deb`

A human on a NixOS host they intend to reboot can wire those by hand after reading this file. Generated `nixos-module.stub.nix` is documentation, not an activation path.

## Why userland-only `nix build` is not “DisplayLink works”

`DisplayLinkManager` talks to hardware through the **EVDI kernel module**. Without `evdi` loaded, the userspace daemon cannot create DRM devices. autoPatchelf on `DisplayLinkManager` would produce a store path that still cannot drive a dock. Claiming otherwise would be the silent-success failure mode this project refuses.

## Policy recap

- EULA: accepted 2026-09-10 (Tim).
- Kernel: never from deb2nix.
- Publish: no public nixpkgs.
- Host: this cloud VM and Tim’s machines stay unmodified.
